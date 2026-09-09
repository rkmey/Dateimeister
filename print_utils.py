"""
    from print_utils import print_photos
    print_photos(["/path/to/img1.jpg", "/path/to/img2.png"])
    print_photos(["/path/to/img1.jpg"], printer="Office Laser")
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import List, Optional
import tkinter as tk
from tkinter import ttk

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

"""
Usage from another script:

    printer = print_utils.choose_printer(self.root)   # self.root = your Tk root/parent window
    print_photos(files, printer=printer)              # printer may be None -> default printer is used
"""


def list_printers() -> List[str]:
    """Return the names of all printers installed on this machine."""
    if os.name == "nt":
        import win32print
        printers = win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        )
        return [p[2] for p in printers]
    else:
        try:
            result = subprocess.run(
                ["lpstat", "-p"], capture_output=True, text=True, check=True
            )
        except Exception:
            return []
        names = []
        for line in result.stdout.splitlines():
            # Typical line: "printer <name> is idle.  enabled since ..."
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "printer":
                names.append(parts[1])
        return names


def get_default_printer() -> Optional[str]:
    """Return the name of the current system default printer, if any."""
    if os.name == "nt":
        import win32print
        try:
            return win32print.GetDefaultPrinter()
        except Exception:
            return None
    else:
        try:
            result = subprocess.run(
                ["lpstat", "-d"], capture_output=True, text=True, check=True
            )
            line = result.stdout.strip()
            if ":" in line:
                name = line.split(":", 1)[1].strip()
                return name or None
        except Exception:
            pass
        return None


def choose_printer(parent: Optional[tk.Misc] = None) -> Optional[str]:
    """
    Show a small modal dialog letting the user pick one of the installed
    printers by name, so the caller does not need to know printer names
    in advance.

    Parameters
    ----------
    parent : tkinter widget, optional
        The parent window the dialog should be attached to. If omitted,
        a hidden temporary root window is created and destroyed again.

    Returns
    -------
    str or None
        The selected printer name, or None if the user cancelled or no
        printers are installed. Callers should treat None as "use the
        system default printer".
    """
    printers = list_printers()
    default = get_default_printer()

    owns_root = parent is None
    if owns_root:
        parent = tk.Tk()
        parent.withdraw()

    dialog = tk.Toplevel(parent)
    dialog.title("Select printer")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()  # modal

    tk.Label(dialog, text="Please select a printer:").pack(
        padx=12, pady=(12, 4), anchor="w"
    )

    if printers:
        initial = default if default in printers else printers[0]
    else:
        initial = ""
    selected = tk.StringVar(value=initial)

    combo = ttk.Combobox(
        dialog, textvariable=selected, values=printers, state="readonly", width=40
    )
    combo.pack(padx=12, pady=4)

    if not printers:
        tk.Label(
            dialog, text="No printers found.", fg="red"
        ).pack(padx=12, pady=(0, 4))

    result = {"printer": None}

    def on_ok():
        result["printer"] = selected.get() or None
        dialog.destroy()

    def on_cancel():
        result["printer"] = None
        dialog.destroy()

    button_frame = tk.Frame(dialog)
    button_frame.pack(padx=12, pady=(8, 12), fill="x")
    tk.Button(button_frame, text="OK", width=10, command=on_ok).pack(
        side="right", padx=(4, 0)
    )
    tk.Button(button_frame, text="Cancel", width=10, command=on_cancel).pack(
        side="right"
    )

    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    dialog.wait_window()

    if owns_root:
        parent.destroy()

    return result["printer"]

def print_photos(
    files: List[str],
    printer: Optional[str] = None,
    delay: float = 2.0,
    orientation: str = "auto",
    dry_run: bool = False,
    preview_dir: Optional[str] = None,
) -> int:
    """
    Print one or more image files, in the given order.

    On Windows, images are rendered and sent directly to the printer via
    GDI (requires pywin32 and Pillow) - this avoids relying on the Photos
    app's shell print handling, which is unreliable when targeting a
    specific (non-default) printer.
    On macOS/Linux, files are sent via CUPS ('lp'), which must be
    installed and have a printer configured.

    Parameters
    ----------
    files : list of str
        Full paths (including filename) of the images to print.
    printer : str, optional
        Name of the target printer. If omitted, the system default
        printer is used. Ignored when dry_run is True.
    delay : float, optional
        Seconds to wait between print jobs, giving the spooler time to
        pick up each job before the next one is sent. Default: 2.0.
    orientation : str, optional
        "auto" (default) picks landscape or portrait per image based on
        its aspect ratio. Can be forced to "landscape" or "portrait" for
        all images instead.
    dry_run : bool, optional
        If True, nothing is actually sent to a printer. Instead, a PNG
        preview of the page (paper size, orientation, scaling and
        centering) is saved next to the source image (or in preview_dir)
        and opened for viewing. Useful for testing without wasting ink
        or paper.
    preview_dir : str, optional
        Folder to save dry-run previews into. Defaults to the same
        folder as each source image.

    Returns
    -------
    int
        Number of files that were successfully processed.
    """
    success_count = 0

    for file in files:
        path = Path(file)

        if not path.is_file():
            print(f"[WARNING] File not found, skipped: {path}")
            continue

        if path.suffix.lower() not in VALID_EXTENSIONS:
            print(f"[WARNING] Unsupported image format, skipped: {path}")
            continue

        print(
            f"{'[DRY RUN] Previewing' if dry_run else 'Printing'}: {path}"
            + (f" -> {printer}" if printer and not dry_run else "")
        )

        try:
            if dry_run:
                _preview_photo(path, orientation, preview_dir)
            elif os.name == "nt":
                _print_windows(path, printer, orientation)
            else:
                _print_unix(path, printer, orientation)
        except Exception as e:
            print(f"[ERROR] Failed to process {path}: {e}")
            continue

        time.sleep(delay)
        success_count += 1

    print(f"Done: {success_count} of {len(files)} file(s) processed.")
    return success_count


def _preview_photo(
    path: Path,
    orientation: str,
    preview_dir: Optional[str] = None,
    dpi: int = 150,
    page_size_mm: tuple = (210, 297),  # A4
) -> None:
    """Render a PNG preview of the printed page, without using a printer."""
    from PIL import Image, ImageOps

    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")

    landscape = _resolve_landscape(img, orientation)
    page_w_mm, page_h_mm = page_size_mm
    if landscape:
        page_w_mm, page_h_mm = page_h_mm, page_w_mm

    page_w_px = int(page_w_mm / 25.4 * dpi)
    page_h_px = int(page_h_mm / 25.4 * dpi)

    scale = min(page_w_px / img.width, page_h_px / img.height)
    out_w = int(img.width * scale)
    out_h = int(img.height * scale)
    x_offset = (page_w_px - out_w) // 2
    y_offset = (page_h_px - out_h) // 2

    page = Image.new("RGB", (page_w_px, page_h_px), "white")
    resized = img.resize((out_w, out_h), Image.LANCZOS)
    page.paste(resized, (x_offset, y_offset))

    out_dir = Path(preview_dir) if preview_dir else path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    preview_path = out_dir / f"preview_{path.stem}.png"
    page.save(preview_path)

    print(
        f"[DRY RUN] Preview saved: {preview_path} "
        f"({'landscape' if landscape else 'portrait'}, {page_w_mm}x{page_h_mm}mm)"
    )

    try:
        if os.name == "nt":
            os.startfile(str(preview_path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(preview_path)])
        else:
            subprocess.run(["xdg-open", str(preview_path)])
    except Exception:
        pass  # opening the preview is a convenience, not essential


def _resolve_landscape(img, orientation: str) -> bool:
    if orientation == "landscape":
        return True
    if orientation == "portrait":
        return False
    return img.width >= img.height  # "auto"


def _print_windows(path: Path, printer: Optional[str], orientation: str) -> None:
    # We deliberately do NOT use the shell "print"/"printto" verbs here.
    # On modern Windows, image files are associated with the Photos app,
    # which frequently does not implement "printto" correctly and fails
    # with WinError 31 ("A device attached to the system is not
    # functioning") when a specific printer is requested. Rendering the
    # image directly via GDI avoids shell file associations entirely and
    # works the same way regardless of which printer is targeted.
    # Requires pywin32 (pip install pywin32) and Pillow (pip install pillow).
    try:
        import win32print
        import win32ui
        import win32con
        import win32gui
    except ImportError as e:
        raise RuntimeError(
            "Printing on Windows requires pywin32 (pip install pywin32)."
        ) from e
    from PIL import Image, ImageOps, ImageWin

    printer_name = printer or win32print.GetDefaultPrinter()

    img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # respect camera orientation
    if img.mode != "RGB":
        img = img.convert("RGB")

    landscape = _resolve_landscape(img, orientation)

    # set the page orientation on the printer's DEVMODE before creating the DC
    hprinter = win32print.OpenPrinter(printer_name)
    try:
        devmode = win32print.GetPrinter(hprinter, 2)["pDevMode"]
        devmode.Orientation = (
            win32con.DMORIENT_LANDSCAPE if landscape else win32con.DMORIENT_PORTRAIT
        )
        win32print.DocumentProperties(
            0,
            hprinter,
            printer_name,
            devmode,
            devmode,
            win32con.DM_IN_BUFFER | win32con.DM_OUT_BUFFER,
        )
    finally:
        win32print.ClosePrinter(hprinter)

    hdc_handle = win32gui.CreateDC("WINSPOOL", printer_name, devmode)
    hdc = win32ui.CreateDCFromHandle(hdc_handle)

    # printable area of the page, in device pixels (already reflects the
    # orientation set above)
    printable_w = hdc.GetDeviceCaps(win32con.HORZRES)
    printable_h = hdc.GetDeviceCaps(win32con.VERTRES)

    # scale the image to fit the page while keeping its aspect ratio,
    # then center it on the page
    scale = min(printable_w / img.width, printable_h / img.height)
    out_w = int(img.width * scale)
    out_h = int(img.height * scale)
    x_offset = (printable_w - out_w) // 2
    y_offset = (printable_h - out_h) // 2

    hdc.StartDoc(path.name)
    hdc.StartPage()
    dib = ImageWin.Dib(img)
    dib.draw(hdc.GetHandleOutput(), (x_offset, y_offset, x_offset + out_w, y_offset + out_h))
    hdc.EndPage()
    hdc.EndDoc()
    hdc.DeleteDC()


def _print_unix(path: Path, printer: Optional[str], orientation: str) -> None:
    from PIL import Image

    landscape = _resolve_landscape(Image.open(path), orientation)

    cmd = ["lp"]
    if printer:
        cmd += ["-d", printer]
    # CUPS: 4 = landscape, 3 = portrait
    cmd += ["-o", f"orientation-requested={4 if landscape else 3}"]
    cmd.append(str(path))
    subprocess.run(cmd, check=True)
