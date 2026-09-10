"""
print_preview.py - a window that shows photos selected for printing as a
scrollable grid, lets the user select/deselect them (with unlimited
undo/redo of the selection), delete unwanted ones, and print the
selected/all photos via print_utils.print_photos().

Usage from Dateimeister:

    from print_preview import PrintPreview

    self.preview = PrintPreview(self.root, rows=3, printer=None)
    ...
    # whenever the user picks another photo for printing:
    self.preview.add_photo(file_path)
"""

import tkinter as tk
from pathlib import Path

from PIL import Image, ImageOps, ImageTk

import tools
import print_utils
from typing import Callable


class PrintPreview:
    def __init__(
        self,
        parent,
        rows: int = 3,
        row_overflow_factor: float = 2.0,
        gap: int = 10,
        canvas_ratio: float = 0.9,
        selection_margin_pct: float = 0.05,
        printer: str = None,
        dry_run: bool = False,
        preview_dir: str = None,
        debug: bool = False,
        close_callback: Callable = None
    ):
        """
        rows : number of rows that should fit in the currently visible
            canvas height - thumbnail height is derived as
            canvas_height / rows, so resizing the window rescales photos
            while keeping `rows` rows visible at once.
        row_overflow_factor : a row keeps accepting further photos as
            long as its cumulative width stays below
            row_overflow_factor * visible_canvas_width. Once the next
            photo would push it past that, a new row is started instead.
            Default 2.0 (a row may extend to twice the visible width
            before wrapping).
        preview_dir : folder for dry-run preview PNGs, passed through to
            print_utils.print_photos(). Defaults to a temp folder there
            if omitted (see print_utils.print_photos docs).
        """
        self.parent = parent
        self.rows = rows
        self.row_overflow_factor = row_overflow_factor
        self.gap = gap
        self.canvas_ratio = canvas_ratio
        self.selection_margin_pct = selection_margin_pct
        self.printer = printer
        self.preview_dir = preview_dir
        self.debug = debug
        self.close_callback = close_callback

        self.photos = []  # ordered list of dicts, see add_photo()
        self.item_to_index = {}  # canvas image item id -> index in self.photos
        self.selected = set()  # currently selected indices
        self.undo_stack = []  # list of (old_selection, new_selection) pairs
        self.redo_stack = []
        self.thumb_height = 150  # recalculated as soon as the canvas has a real size

        self.window = tk.Toplevel(parent)
        self.window.title("Print Preview")
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        win_w, win_h = screen_w // 2, screen_h // 2
        pos_x, pos_y = (screen_w - win_w) // 2, (screen_h - win_h) // 2
        self.window.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")

        # row 0 (canvas) : row 1 (controls) = canvas_ratio : (1 - canvas_ratio)
        self.window.rowconfigure(0, weight=int(round(canvas_ratio * 100)))
        self.window.rowconfigure(1, weight=int(round((1 - canvas_ratio) * 100)))
        self.window.columnconfigure(0, weight=1)

        self._build_canvas_area()
        self._build_control_area(dry_run)
        self._update_printer_label()
        self._update_button_states()

        self.resize_timer = tools.RestartableTimer(self.window, 250, self._on_resize_settled)
        self.canvas_frame.bind("<Configure>", self._on_canvas_configure)
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_canvas_area(self):
        self.canvas_frame = tk.Frame(self.window)
        self.canvas_frame.grid(row=0, column=0, sticky="nsew")
        self.canvas_frame.rowconfigure(0, weight=1)
        self.canvas_frame.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.canvas_frame, bg="white")
        self.canvas.grid(row=0, column=0, sticky="nsew")

        vbar = tk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        vbar.grid(row=0, column=1, sticky="ns")
        hbar = tk.Scrollbar(self.canvas_frame, orient="horizontal", command=self.canvas.xview)
        hbar.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

        self.canvas.bind("<Button-1>", self._on_click)

    def _build_control_area(self, dry_run: bool):
        self.control_frame = tk.Frame(self.window)
        self.control_frame.grid(row=1, column=0, sticky="nsew")

        self.btn_delete = tk.Button(
            self.control_frame, text="Delete selected", command=self.delete_selected
        )
        self.btn_delete.pack(side="left", padx=4, pady=4)

        self.btn_print_selected = tk.Button(
            self.control_frame, text="Print selected", command=self.print_selected
        )
        self.btn_print_selected.pack(side="left", padx=4, pady=4)

        tk.Button(self.control_frame, text="Print all", command=self.print_all).pack(
            side="left", padx=4, pady=4
        )

        self.btn_undo = tk.Button(self.control_frame, text="Undo", command=self.undo)
        self.btn_undo.pack(side="left", padx=4, pady=4)

        self.btn_redo = tk.Button(self.control_frame, text="Redo", command=self.redo)
        self.btn_redo.pack(side="left", padx=4, pady=4)
        tk.Button(self.control_frame, text="Choose Printer", command=self.choose_printer).pack(
            side="left", padx=4, pady=4
        )

        self.printer_label = tk.Label(self.control_frame, text="Printer: (none)")
        self.printer_label.pack(side="left", padx=12, pady=4)

        self.dry_run_var = tk.BooleanVar(value=dry_run)
        tk.Checkbutton(self.control_frame, text="Dry run", variable=self.dry_run_var).pack(
            side="left", padx=4, pady=4
        )

    # ------------------------------------------------------------------ #
    # Adding photos
    # ------------------------------------------------------------------ #

    def add_photo(self, file_path: str):
        path = Path(file_path)
        if not path.is_file():
            tools.info_box(f"File not found: {path}", "fehler")
            return

        pil = Image.open(path)
        pil = ImageOps.exif_transpose(pil)  # respect camera orientation
        if pil.mode != "RGB":
            pil = pil.convert("RGB")

        entry = {
            "file": str(path),
            "pil_image": pil,
            "photo": None,
            "img_id": None,
            "rect_id": None,
            "x": 0,
            "y": 0,
            "w": 0,
            "h": 0,
        }

        if self.canvas.winfo_height() <= 1:
            self.window.update_idletasks()
        self._recompute_thumb_height()

        self._render_thumb(entry)
        entry["img_id"] = self.canvas.create_image(0, 0, anchor="nw", image=entry["photo"])
        self.item_to_index[entry["img_id"]] = len(self.photos)
        self.photos.append(entry)
        self._relayout()

    # ------------------------------------------------------------------ #
    # Layout / scaling
    # ------------------------------------------------------------------ #

    def _on_canvas_configure(self, event):
        self.resize_timer.start()  # debounce: only re-render once resizing settles

    def _on_resize_settled(self):
        old_height = self.thumb_height
        self._recompute_thumb_height()
        if self.thumb_height != old_height:
            self._rescale_all()
        else:
            self._relayout()

    def _recompute_thumb_height(self):
        canvas_h = self.canvas.winfo_height()
        if canvas_h <= 1:
            return
        self.thumb_height = max(20, int((canvas_h - (self.rows + 1) * self.gap) / self.rows))

    def _render_thumb(self, entry):
        pil = entry["pil_image"]
        scale = self.thumb_height / pil.height
        w = max(1, int(pil.width * scale))
        h = self.thumb_height
        resized = pil.resize((w, h), Image.LANCZOS)
        entry["photo"] = ImageTk.PhotoImage(resized)
        entry["w"], entry["h"] = w, h
        if entry["img_id"] is not None:
            self.canvas.itemconfig(entry["img_id"], image=entry["photo"])

    def _rescale_all(self):
        for entry in self.photos:
            self._render_thumb(entry)
        self._relayout()

    def _relayout(self):
        visible_width = max(1, self.canvas.winfo_width())
        max_row_width = self.row_overflow_factor * visible_width

        x = self.gap
        y = self.gap
        row_width = 0  # cumulative width of photos + internal gaps in the current row
        max_x = 0

        for entry in self.photos:
            w = entry["w"]

            if row_width > 0:
                candidate_width = row_width + self.gap + w
                if candidate_width >= max_row_width:
                    # this photo starts a new row instead of joining the current one
                    x = self.gap
                    y += self.thumb_height + self.gap
                    row_width = 0

            self.canvas.coords(entry["img_id"], x, y)
            entry["x"], entry["y"] = x, y
            if entry["rect_id"] is not None:
                self.canvas.coords(entry["rect_id"], *self._rect_coords(entry))

            max_x = max(max_x, x + w)
            x += w + self.gap
            row_width = row_width + (self.gap if row_width > 0 else 0) + w

        total_height = y + self.thumb_height + self.gap
        total_width = max(max_x + self.gap, visible_width)
        self.canvas.configure(scrollregion=(0, 0, total_width, total_height))

    # ------------------------------------------------------------------ #
    # Selection (click handling + undo/redo)
    # ------------------------------------------------------------------ #

    def _on_click(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        idx = self._hit_test(cx, cy)
        if idx is None:
            return

        ctrl_held = bool(event.state & 0x0004)
        if ctrl_held:
            new_sel = set(self.selected)
            if idx in new_sel:
                new_sel.discard(idx)
            else:
                new_sel.add(idx)
        else:
            new_sel = {idx}
        self._set_selection(new_sel)

    def _hit_test(self, cx, cy):
        for item in self.canvas.find_overlapping(cx, cy, cx, cy):
            if item in self.item_to_index:
                return self.item_to_index[item]
        return None

    def _rect_coords(self, entry):
        mx = entry["w"] * self.selection_margin_pct
        my = entry["h"] * self.selection_margin_pct
        return (
            entry["x"] + mx,
            entry["y"] + my,
            entry["x"] + entry["w"] - mx,
            entry["y"] + entry["h"] - my,
        )

    def _refresh_selection_visuals(self):
        for i, entry in enumerate(self.photos):
            if i in self.selected:
                if entry["rect_id"] is None:
                    entry["rect_id"] = self.canvas.create_rectangle(
                        *self._rect_coords(entry), outline="red", width=2, dash=(4, 2)
                    )
                else:
                    self.canvas.coords(entry["rect_id"], *self._rect_coords(entry))
            else:
                if entry["rect_id"] is not None:
                    self.canvas.delete(entry["rect_id"])
                    entry["rect_id"] = None

    def _update_button_states(self):
        self.btn_delete.config(state=tk.NORMAL if self.selected else tk.DISABLED)
        self.btn_print_selected.config(state=tk.NORMAL if self.selected else tk.DISABLED)
        self.btn_undo.config(state=tk.NORMAL if self.undo_stack else tk.DISABLED)
        self.btn_redo.config(state=tk.NORMAL if self.redo_stack else tk.DISABLED)

    def _set_selection(self, new_selection: set):
        old_selection = set(self.selected)
        if old_selection == new_selection:
            return
        self.undo_stack.append(("select", old_selection, set(new_selection)))
        self.redo_stack.clear()
        self.selected = set(new_selection)
        self._refresh_selection_visuals()
        self._update_button_states()

    def undo(self):
        if not self.undo_stack:
            return
        action = self.undo_stack.pop()
        self.redo_stack.append(action)
        kind = action[0]
        if kind == "select":
            _, old_selection, _new_selection = action
            self.selected = set(old_selection)
            self._refresh_selection_visuals()
        elif kind == "delete":
            _, removed, old_selection, _new_selection = action
            self._reinsert_entries(removed)
            self.selected = set(old_selection)
            self._relayout()
            self._refresh_selection_visuals()
        self._update_button_states()

    def redo(self):
        if not self.redo_stack:
            return
        action = self.redo_stack.pop()
        self.undo_stack.append(action)
        kind = action[0]
        if kind == "select":
            _, _old_selection, new_selection = action
            self.selected = set(new_selection)
            self._refresh_selection_visuals()
        elif kind == "delete":
            _, removed, _old_selection, new_selection = action
            self._remove_entries(removed)
            self.selected = set(new_selection)
            self._relayout()
            self._refresh_selection_visuals()
        self._update_button_states()

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #

    def delete_selected(self):
        if not self.selected:
            return

        old_selection = set(self.selected)
        removed = []  # list of (original_position, entry)
        remaining = []
        for i, entry in enumerate(self.photos):
            if i in self.selected:
                self.canvas.delete(entry["img_id"])
                if entry["rect_id"] is not None:
                    self.canvas.delete(entry["rect_id"])
                entry["img_id"] = None
                entry["rect_id"] = None
                removed.append((i, entry))
            else:
                remaining.append(entry)

        self.photos = remaining
        self.selected = set()
        self.item_to_index = {entry["img_id"]: i for i, entry in enumerate(self.photos)}

        self.undo_stack.append(("delete", removed, old_selection, set()))
        self.redo_stack.clear()

        self._relayout()
        self._update_button_states()

    def _reinsert_entries(self, removed):
        """Undo a delete: put entries back at their original positions and
        recreate their canvas image (the old canvas item was destroyed)."""
        for pos, entry in removed:
            entry["img_id"] = self.canvas.create_image(0, 0, anchor="nw", image=entry["photo"])
            entry["rect_id"] = None  # (re-)created by _refresh_selection_visuals() if selected
            self.photos.insert(pos, entry)
        self.item_to_index = {e["img_id"]: i for i, e in enumerate(self.photos)}

    def _remove_entries(self, removed):
        """Redo a delete: remove the same entries again."""
        removed_ids = {id(entry) for _, entry in removed}
        remaining = []
        for entry in self.photos:
            if id(entry) in removed_ids:
                self.canvas.delete(entry["img_id"])
                if entry["rect_id"] is not None:
                    self.canvas.delete(entry["rect_id"])
                entry["img_id"] = None
                entry["rect_id"] = None
            else:
                remaining.append(entry)
        self.photos = remaining
        self.item_to_index = {e["img_id"]: i for i, e in enumerate(self.photos)}

    # ------------------------------------------------------------------ #
    # Printing
    # ------------------------------------------------------------------ #

    def print_selected(self):
        files = [self.photos[i]["file"] for i in sorted(self.selected)]
        self._print(files)

    def print_all(self):
        files = [entry["file"] for entry in self.photos]
        self._print(files)

    def _print(self, files):
        if not files:
            tools.info_box("No photos to print.", "info")
            return
        self._ensure_printer()
        print_utils.print_photos(
            files,
            printer=self.printer,
            dry_run=self.dry_run_var.get(),
            preview_dir=self.preview_dir,
        )

    def _ensure_printer(self):
        if not self.printer:
            self.choose_printer()

    def choose_printer(self):
        chosen = print_utils.choose_printer(self.window)
        if chosen:
            self.printer = chosen
        self._update_printer_label()

    def _update_printer_label(self):
        self.printer_label.config(text=f"Printer: {self.printer or '(none)'}")

    def on_close(self):
        self.close_callback()
        self.window.destroy()
        