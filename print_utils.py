"""
Add this to tools.py. Usage from any other script:

    from tools import print_photos
    print_photos(["/path/to/img1.jpg", "/path/to/img2.png"])
    print_photos(["/path/to/img1.jpg"], printer="Office Laser")
"""

import hashlib
import os
import subprocess
import sys
import tempfile
import time
import re
from pathlib import Path
from typing import List, Optional
import tkinter as tk
from tkinter import ttk

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

# Windows' built-in "print to file" virtual printers - these need an
# explicit output filename passed to StartDoc(), otherwise Windows tries
# to show its own save dialog internally, which crashes hard (native
# "Windows fatal exception: code 0x80040155 / REGDB_E_CLASSNOTREG") when
# there is no interactive UI thread to host that dialog.

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
        
    printer = result["printer"]
    file_ext = _file_printer_extension(printer)
    print(f"printer chosen is {printer}, ext is {file_ext}")

    return printer


def _file_printer_extension(printer_name: str) -> Optional[str]:
    file_ext = None
    match = re.search(rf".*?microsoft.*?pdf", printer_name, re.I)
    if match:
        file_ext = filetype = ".pdf"
    else:
        match = re.search(rf".*?microsoft.*?writer", printer_name, re.I)
        if match:
            file_ext = filetype = ".xps"
    return file_ext



def configure_printer(printer_name: str, parent_hwnd: int = 0):
    """
    Opens the printer's native settings dialog (as provided by the
    manufacturer's driver) so the user can pick options that have no
    generic Windows API equivalent - most importantly a borderless photo
    paper / media type, which each vendor names and exposes differently.

    Call this once, then pass the returned object as `devmode` to
    print_photos()/_print_windows() to reuse exactly those settings for
    every subsequent print job.

    Parameters
    ----------
    printer_name : str
        Name of the printer to configure (e.g. from choose_printer()).
    parent_hwnd : int, optional
        Window handle to attach the dialog to, e.g. self.root.winfo_id()
        in a Tk app. Defaults to 0 (no parent).

    Returns
    -------
    DEVMODE or None
        The configured settings, or None if the user cancelled the dialog.
        Windows-only.
    """
    import win32print
    import win32con

    hprinter = win32print.OpenPrinter(printer_name)
    try:
        devmode = win32print.GetPrinter(hprinter, 2)["pDevMode"]
        result = win32print.DocumentProperties(
            parent_hwnd,
            hprinter,
            printer_name,
            devmode,
            devmode,
            win32con.DM_IN_PROMPT | win32con.DM_IN_BUFFER | win32con.DM_OUT_BUFFER,
        )
        if result != 1:  # IDOK
            return None
        return devmode
    finally:
        win32print.ClosePrinter(hprinter)


def print_photos(
    files: List[str],
    printer: Optional[str] = None,
    delay: float = 2.0,
    orientation: str = "auto",
    dry_run: bool = False,
    preview_dir: Optional[str] = None,
    devmode=None,
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
        printer is used. Ignored when dry_run is True, or when devmode
        is given (the devmode already targets a specific printer).
    delay : float, optional
        Seconds to wait between print jobs, giving the spooler time to
        pick up each job before the next one is sent. Default: 2.0.
    orientation : str, optional
        "auto" (default) picks landscape or portrait per image based on
        its aspect ratio. Can be forced to "landscape" or "portrait" for
        all images instead. Ignored when devmode is given - the
        orientation from configure_printer() is used as-is.
    dry_run : bool, optional
        If True, nothing is actually sent to a printer. Instead, a PNG
        preview of the page (paper size, orientation, scaling and
        centering) is saved next to the source image (or in preview_dir)
        and opened for viewing. Useful for testing without wasting ink
        or paper.
    preview_dir : str, optional
        Folder used for two purposes that never overlap in a single
        call: (1) dry-run PNG previews, and (2) the actual output file
        when printing to a virtual "print to file" printer such as
        "Microsoft Print to PDF" or "Microsoft XPS Document Writer".
        Defaults to a "dateimeister_print_preview" folder inside the
        system temp directory (not the source photo's folder, to avoid
        cluttering NAS/photo directories).
    devmode : DEVMODE, optional
        Windows only. Settings obtained from configure_printer(), e.g.
        to enable a borderless photo paper media type that has no
        generic API equivalent. When given, this is used as-is instead
        of building a fresh devmode from `printer`/`orientation`.

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
            + (f" -> {printer}" if printer and not dry_run and devmode is None else "")
        )

        try:
            if dry_run:
                _preview_photo(path, orientation, preview_dir)
            elif os.name == "nt":
                _print_windows(path, printer, orientation, devmode, preview_dir)
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

    out_dir = Path(preview_dir) if preview_dir else Path(tempfile.gettempdir()) / "dateimeister_print_preview"
    out_dir.mkdir(parents=True, exist_ok=True)
    # include a short hash of the full source path so that same-named files
    # from different folders don't collide/overwrite each other
    unique = hashlib.md5(str(path.resolve()).encode("utf-8")).hexdigest()[:8]
    preview_path = out_dir / f"preview_{path.stem}_{unique}.png"
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


def _print_windows(
    path: Path,
    printer: Optional[str],
    orientation: str,
    devmode=None,
    preview_dir: Optional[str] = None,
) -> None:
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

    if devmode is not None:
        # Use the caller-configured settings as-is (e.g. from
        # configure_printer(), which may include a borderless photo
        # paper media type - that has no generic API equivalent, so we
        # don't touch orientation/paper size ourselves here).
        printer_name = devmode.DeviceName or printer_name
    else:
        landscape = _resolve_landscape(img, orientation)
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

    # printable area of the page, in device pixels (reflects orientation
    # and, if a borderless media type was configured, the full page size)
    printable_w = hdc.GetDeviceCaps(win32con.HORZRES)
    printable_h = hdc.GetDeviceCaps(win32con.VERTRES)

    # For borderless printing we want to fill the page completely rather
    # than fit-with-margins, so we scale to *cover* the page and crop any
    # overhang instead of scaling to fit inside it.
    if devmode is not None:
        scale = max(printable_w / img.width, printable_h / img.height)
    else:
        scale = min(printable_w / img.width, printable_h / img.height)
    out_w = int(img.width * scale)
    out_h = int(img.height * scale)
    x_offset = (printable_w - out_w) // 2
    y_offset = (printable_h - out_h) // 2

    hdc.StartDoc(path.name, _build_file_printer_output(printer_name, path, preview_dir))
    hdc.StartPage()
    dib = ImageWin.Dib(img)
    dib.draw(hdc.GetHandleOutput(), (x_offset, y_offset, x_offset + out_w, y_offset + out_h))
    hdc.EndPage()
    hdc.EndDoc()
    hdc.DeleteDC()


def _build_file_printer_output(printer_name: str, path: Path, preview_dir: Optional[str]):
    """
    For virtual "print to file" printers (Microsoft Print to PDF / XPS
    Document Writer), build and return the output file path that must be
    passed to StartDoc(). Returns None for regular printers, where the
    spooler handles the destination itself.
    """
    ext = _file_printer_extension(printer_name)
    if ext is None:
        return None

    out_dir = Path(preview_dir) if preview_dir else Path(tempfile.gettempdir()) / "dateimeister_print_output"
    out_dir.mkdir(parents=True, exist_ok=True)
    unique = hashlib.md5(str(path.resolve()).encode("utf-8")).hexdigest()[:8]
    output_path = out_dir / f"{path.stem}_{unique}{ext}"
    print(f"[INFO] '{printer_name}' writes to a file instead of paper: {output_path} ext is {ext}")
    return str(output_path)


def _print_unix(path: Path, printer: Optional[str], orientation: str) -> None:
    # Note: true borderless printing on CUPS also depends on the driver.
    # Many photo-capable drivers (e.g. Gutenprint) expose a borderless
    # media size, typically named like "na_index-4x6_4x6.borderless" or
    # similar - run `lpoptions -p <printer> -l` to see what your driver
    # calls it, then pass it via cmd += ["-o", "media=<that-name>"].
    from PIL import Image

    landscape = _resolve_landscape(Image.open(path), orientation)

    cmd = ["lp"]
    if printer:
        cmd += ["-d", printer]
    # CUPS: 4 = landscape, 3 = portrait
    cmd += ["-o", f"orientation-requested={4 if landscape else 3}"]
    cmd.append(str(path))
    subprocess.run(cmd, check=True)
