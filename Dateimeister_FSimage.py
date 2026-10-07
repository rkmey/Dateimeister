#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

# In this module we store the full-size images.

import sys
import os
import configparser
import re
import locale
import ctypes
import time
import operator
import threading
import copy
import subprocess
import shutil

import tkinter as tk
import tkinter.ttk as ttk
from tkinter.constants import *
from tkinter import filedialog as fd
from tkinter import messagebox
from tkinter import Scrollbar
from tkinter import ttk
from tkinter import Frame
from tkinter import Label
from tkinter import Canvas
from tkinter import Menu
from tkinter.font import Font
from time import gmtime, strftime

from PIL import Image, ImageTk
from datetime import datetime, timezone
from typing import Callable

import tools
import dateimeister_video as DV
import Tooltip as TT

from tools import Globals, INCLUDE, EXCLUDE, FileStateEvent, ClosingEvent, PrintRequestEvent


# ----------------------------------------------------------------------
# Metadata treeview: heading labels
# ----------------------------------------------------------------------
HEAD_CATEGORY    = "Category"
HEAD_KEY         = "Key"
HEAD_VALUE       = "Value"

NO_METADATA_TEXT = "(no metadata)"

# Imagetype value for which the RAW special path applies.
_RAW_IMAGETYPE = "RAW"


class MyFSImage:

    # The class "constructor" - It's actually an initializer
    def __init__(
        self,
        file: str = None,
        thumbnail: tools.MyThumbnail = None,
        caller: object = None,  # can be several class instances
        str_title_prefix: str = None,
        str_include: str = None,
        str_exclude: str = None,
        str_included: str = None,
        str_excluded: str = None,
        debug: bool = False
    ):

        self.caller = caller
        self.thumbnail = thumbnail
        self.str_include = str_include
        self.str_exclude = str_exclude
        self.str_included = str_included
        self.str_excluded = str_excluded
        self.debug = debug
        self.file = file

        # ------------------------------------------------------------------
        # Imagetype comes from the thumbnail (no fallback to Globals.imagetype).
        # ------------------------------------------------------------------
        self.imagetype = thumbnail.get_imagetype() if thumbnail is not None else None
        if self.imagetype is None:
            raise RuntimeError(
                "MyFSImage: thumbnail.get_imagetype() returned None. "
                "The thumbnail must be initialized with set_imagetype() "
                "before opening MyFSImage."
            )

        # ------------------------------------------------------------------
        # Load image. For RAW two variants: embedded JPEG (fast) and full
        # sensor resolution (slow, lazy).
        # ------------------------------------------------------------------
        self.image_embedded = None
        self.image_full     = None
        self.raw_mode       = None

        if self.imagetype == _RAW_IMAGETYPE:
            import rawpy_loader
            self.image_embedded = rawpy_loader.load_raw_embedded(file)
            self.image = self.image_embedded
            self.raw_mode = "embedded"
        else:
            self.image = Image.open(file)

        # Create secondary (or popup) window.
        self.root = tk.Toplevel()
        # Window size
        self.physical_width  = self.root.winfo_screenwidth()
        self.physical_height = self.root.winfo_screenheight()
        self.screen_width  = int(self.root.winfo_screenwidth() * .75)
        self.screen_height = int(self.root.winfo_screenheight() * .75)
        print("Screen is " + str(self.screen_width) + " x " + str(self.screen_height) + " physical: " + str(self.physical_width) + " x " + str(self.physical_height))
        v_dim = str(self.screen_width) + 'x' + str(self.screen_height)
        self.root.geometry(v_dim)
        self.root.minsize(int(self.physical_width / 4), int(self.physical_height / 4))
        self.root.resizable(True, True)

        gap = .005
        relw_frame_canvas = .75
        relh_frame_canvas = 1 - gap
        relw_frame_1      = (1 - relw_frame_canvas) / 2 - 2 * gap
        relw_frame_2      = (1 - relw_frame_canvas) - gap
        relh_1            = .3 - gap
        relh_2            = 1 - relh_1 - 4 * gap

        # We store the layout parameters on self so we can restore them
        # after leaving fullscreen.
        self._gap = gap
        self._relw_frame_canvas = relw_frame_canvas
        self._relh_frame_canvas = relh_frame_canvas
        self._relw_frame_1 = relw_frame_1
        self._relw_frame_2 = relw_frame_2
        self._relh_1 = relh_1
        self._relh_2 = relh_2

        self.frame_canvas = tk.Frame(self.root)
        self.frame_canvas.place(relx=gap, rely=gap, relheight=relh_frame_canvas, relwidth=relw_frame_canvas)
        self.frame_canvas.configure(relief='flat', background=tools._bgcolor)
        self.frame_canvas.configure(background=tools._bgcolor_dbg) if self.debug else True
        self.frame_canvas.update()

        self.frame_1_1 = tk.Frame(self.root)
        self.frame_1_1.place(relx=relw_frame_canvas + 2 * gap, rely=gap, relheight=relh_1, relwidth=relw_frame_1)
        self.frame_1_1.configure(relief='flat', background=tools._bgcolor)
        self.frame_1_1.configure(background=tools._bgcolor_dbg) if self.debug else True
        self.frame_1_1.update()

        self.frame_1_2 = tk.Frame(self.root)
        self.frame_1_2.place(relx=relw_frame_canvas + relw_frame_1 + 3 * gap, rely=gap, relheight=relh_1, relwidth=relw_frame_1)
        self.frame_1_2.configure(relief='flat', background=tools._bgcolor)
        self.frame_1_2.configure(background=tools._bgcolor_dbg) if self.debug else True
        self.frame_1_2.update()

        self.frame_2 = tk.Frame(self.root)
        self.frame_2.place(relx=relw_frame_canvas + 2 * gap, rely=relh_1 + 3 * gap, relheight=relh_2, relwidth=relw_frame_2 - 2 * gap)
        self.frame_2.configure(relief='flat', background=tools._bgcolor)
        self.frame_2.configure(background=tools._bgcolor_dbg) if self.debug else True
        self.frame_2.update()

        self.text_font = Font(family="Helvetica", size=6)
        relw_button = 0.975
        # For RAW we need space for one extra button and one extra label.
        if self.imagetype == _RAW_IMAGETYPE:
            relh_button = .16
        else:
            relh_button = .2

        # ------------------------------------------------------------------
        # Left column of buttons: Fit Canvas, optional RAW toggle, Exclude,
        # view all meta.
        # ------------------------------------------------------------------
        dict_widgets = {}
        dict_widgets["1"] = {
          "WIDGET": tk.Label, "VAR": "future_use", "OFFSET": 0.00, "RELH": .6, "RELW": relw_button,
          "ANCHOR": "START", "TEXT": "future_use", "FONT": self.text_font}
        dict_widgets["2"] = {
          "WIDGET": tk.Button, "VAR": "Button_fit", "OFFSET": 0.00, "RELH": relh_button, "RELW": relw_button,
          "ANCHOR": "START", "CALLBACK": self.fit_handler,
          "TEXT": "Fit Canvas", "STATE": tk.ACTIVE, "TT": "Scale Image to fit", "FONT": self.text_font}
        if self.imagetype == _RAW_IMAGETYPE:
            # Toggle between embedded JPEG and full sensor resolution.
            dict_widgets["3"] = {
              "WIDGET": tk.Button, "VAR": "Button_raw", "OFFSET": 0.00, "RELH": relh_button, "RELW": relw_button,
              "ANCHOR": "START", "CALLBACK": self.on_button_raw,
              "TEXT": "raw full", "STATE": tk.ACTIVE, "TT": "for RAW toggle between embedded JPEG and full resolution", "FONT": self.text_font}
        dict_widgets["4"] = {
          "WIDGET": tk.Button, "VAR": "Button_exclude", "OFFSET": 0.00, "RELH": relh_button, "RELW": relw_button,
          "ANCHOR": "START", "CALLBACK": self.on_button_state,
          "TEXT": "Exclude", "STATE": tk.ACTIVE, "TT": "include / exclude", "FONT": self.text_font}
        dict_widgets["5"] = {
          "WIDGET": tk.Button, "VAR": "Button_all_meta", "OFFSET": 0.00, "RELH": relh_button, "RELW": relw_button,
          "ANCHOR": "START", "CALLBACK": self.on_button_all_meta,
          "TEXT": "view all meta", "STATE": tk.ACTIVE, "TT": "view all metadata", "FONT": self.text_font}
        dict_widgets["6"] = {
          "WIDGET": tk.Label, "VAR": "label_toggle_view", "OFFSET": 0.00, "RELH": relh_button, "RELW": relw_button,
          "ANCHOR": "START", "TEXT": "Toggle Window / fullscreen", "FONT": self.text_font}
        tools.create_widgets_from_dict(dict_widgets, self.frame_1_1, "VERTICAL", font=self.text_font, bgcolor=tools._bgcolor)

        # ------------------------------------------------------------------
        # Right column: file info, Full scale, optional RAW info label,
        # Include/Exclude status label, Print, Fullscreen.
        # ------------------------------------------------------------------
        dict_widgets = {}
        dict_widgets["1"] = {
          "WIDGET": tk.Label, "VAR": "Label_fileinfo", "OFFSET": 0.00, "RELH": .6, "RELW": relw_button,
          "ANCHOR": "START", "TEXT": "file info", "FONT": self.text_font, "JUSTIFY": "left"}
        dict_widgets["2"] = {
          "WIDGET": tk.Button, "VAR": "Button_fscale", "OFFSET": 0.00, "RELH": relh_button, "RELW": relw_button,
          "ANCHOR": "START", "CALLBACK": self.fscale_handler,
          "TEXT": "Full scale", "STATE": tk.ACTIVE, "TT": "show image in full resolution", "FONT": self.text_font}
        if self.imagetype == _RAW_IMAGETYPE:
            # Status label for the RAW mode.
            dict_widgets["3"] = {
              "WIDGET": tk.Label, "VAR": "Label_rawinfo", "OFFSET": 0.00, "RELH": relh_button, "RELW": relw_button,
              "ANCHOR": "START", "TEXT": "RAW using embedded", "FONT": self.text_font, "JUSTIFY": "left"}
        dict_widgets["4"] = {
          "WIDGET": tk.Label, "VAR": "Label_status", "OFFSET": 0.00, "RELH": relh_button, "RELW": relw_button,
          "ANCHOR": "START", "TEXT": "In/Ex", "FONT": self.text_font}
        dict_widgets["5"] = {
          "WIDGET": tk.Button, "VAR": "Button_print", "OFFSET": 0.0, "RELH": relh_button, "RELW": relw_button,
          "ANCHOR": "START", "CALLBACK": self.print_handler,
          "TEXT": "Print", "STATE": tk.ACTIVE, "TT": "send image to print preview", "FONT": self.text_font}
        # --- FULLSCREEN ---
        dict_widgets["6"] = {
          "WIDGET": tk.Button, "VAR": "Button_fullscreen", "OFFSET": 0.0, "RELH": relh_button, "RELW": relh_button,
          "ANCHOR": "START", "CALLBACK": self.toggle_fullscreen,
          "TEXT": "\u26f6", "STATE": tk.ACTIVE, "TT": "full screen, esc to return to window", "FONT": self.text_font}
        tools.create_widgets_from_dict(dict_widgets, self.frame_1_2, "VERTICAL", font=self.text_font, bgcolor=tools._bgcolor)

        # create the canvas
        self.f = tk.Canvas(self.frame_canvas)
        self.f.configure(background="#d9d9d9")
        self.f.configure(borderwidth="2")
        self.f.configure(highlightbackground="#d9d9d9")
        self.f.configure(highlightcolor="black")
        self.f.configure(insertbackground="black")
        self.f.configure(relief="ridge")
        self.f.configure(selectbackground="#c4c4c4")
        self.f.configure(selectforeground="black")

        # canvas scrollbars
        self.V_I = Scrollbar(self.frame_canvas)
        self.V_I.config(command=self.f.yview)
        self.f.config(yscrollcommand=self.V_I.set)
        self.H_I = Scrollbar(self.frame_canvas, orient=HORIZONTAL)
        self.H_I.config(command=self.f.xview)
        self.f.config(xscrollcommand=self.H_I.set)

        # position of canvas and scrollbars within frame
        tools.place_box_with_scrollbars(self, self.frame_canvas, self.f, self.H_I, self.V_I,
                                        rw=0.01, d_n=0.0, d_e=0.0, d_s=0.0, d_w=0.0)

        # Bind keys to canvas for scrolling
        self.f.bind("<Left>",  lambda event: self.scrollx(-1, "unit"))
        self.f.bind("<Right>", lambda event: self.scrollx( 1, "unit"))
        self.f.bind("<Up>",    lambda event: self.scrolly(-1, "unit"))
        self.f.bind("<Down>",  lambda event: self.scrolly( 1, "unit"))

        if self.thumbnail.getState() == INCLUDE:
            self.Button_exclude.config(text=self.str_exclude)
            self.Label_status.config(text=self.str_included)
        else:
            self.Button_exclude.config(text=self.str_include)
            self.Label_status.config(text=self.str_excluded)

        # Mouse wheel and window close handler.
        self.f.bind("<MouseWheel>", self.mousewheel_handler)
        self.root.protocol("WM_DELETE_WINDOW", self.close_handler)

        self.root.title(str_title_prefix + file)
        self.show_all_meta = False

        # Register event handlers.
        Globals.eventManager.bind("FileStateChanged", self.on_file_state_changed)
        Globals.eventManager.bind("Closing", self.on_closing)

        self.zoomfaktor = 1.0
        self.f.focus_set()
        self.image_zoom(self.zoomfaktor)

        mytext = "{:s}\ncreated {:s} size {:.3f}".format(
            thumbnail.getFile(), thumbnail.get_filectime(), thumbnail.get_filesize())
        self.Label_fileinfo.configure(text=mytext)

        # ------------------------------------------------------------------
        # Metadata treeview.
        # ------------------------------------------------------------------
        style = ttk.Style(self.root)
        style.configure("Metadata.Treeview", font=self.text_font)
        style.configure("Metadata.Treeview.Heading", font=self.text_font)

        self.tree_metadata = tools.ScrolledTreeView(self.frame_2, style="Metadata.Treeview")
        self.tree_metadata.place(relx=0.0, rely=0.0, relheight=1.0, relwidth=1.0)
        self.tree_metadata.configure(columns="Col1, Col2, Col3")
        self.tree_metadata.heading("#0", text=HEAD_CATEGORY, anchor="w")
        self.tree_metadata.heading("#1", text=HEAD_KEY, anchor="w")
        self.tree_metadata.heading("#2", text=HEAD_VALUE, anchor="w")
        self.tree_metadata.column("#0", width=120, minwidth=120, stretch=True, anchor="w")
        self.tree_metadata.column("#1", width=180, minwidth=180, stretch=True, anchor="w")
        self.tree_metadata.column("#2", width=240, minwidth=240, stretch=True, anchor="w")
        self.tree_metadata.config(selectmode=tk.BROWSE)

        self._populate_metadata_tree()

        self.width = 0
        self.height = 0
        self.adjust_zoom = 0
        self.timer = tools.RestartableTimer(self.root, 666, self.resize)
        self.root.bind("<Configure>", self.on_configure)
        self.root.after(0, self.resize)

        # --- FULLSCREEN ---
        # State for the fullscreen mode and the auto-hide overlay.
        self.is_fullscreen = False
        self._hide_timer_id = None
        self._mouse_watch_id = None
        self._last_mouse_pos = None

    # ------------------------------------------------------------------
    # Progress / zoom callbacks (kept for future use)
    # ------------------------------------------------------------------
    def display_progress(self, progress: int):
        self.scale_progress.set(progress)

    def on_scale_motion(self, event):
        self.preview_engine.show_preview(event, self.scale_progress.winfo_width())

    def activate(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    # ------------------------------------------------------------------
    # Resize handling
    # ------------------------------------------------------------------
    def on_configure(self, event):
        x = event.widget
        self.adjust_zoom = 1.0
        if x == self.root:
            if (self.width != event.width or self.height != event.height):
                self.timer.start()

    def resize(self):
        try:
            if not self.root.winfo_exists():
                if hasattr(self, 'timer') and self.timer:
                    try:
                        self.timer.cancel()
                    except Exception:
                        pass
                    self.timer = None
                return
        except Exception:
            return

        self.debug_info_resize("TIMER") if self.debug else True
        old_width = self.width
        old_height = self.height
        self.root.update()
        new_width = self.root.winfo_width()
        new_height = self.root.winfo_height()
        if (old_width != new_width or old_height != new_height):
            self.width = new_width
            self.height = new_height
            if old_width != 0 and old_height != 0 and new_width != 0 and new_height != 0:
                self.adjust_zoom = min(new_width / old_width, new_height / old_height)
            else:
                self.adjust_zoom = 1.0
            self.text_font.configure(size=tools.calc_fontsize(
                self.physical_width, self.physical_height, self.width, self.height, self.debug))
            self.Label_fileinfo.update()
            self.Label_fileinfo.configure(wraplength=int(self.Label_fileinfo.winfo_width() * 0.95))
            try:
                fm = Font(font=self.text_font)
                rowheight = fm.metrics("linespace") + 2
                style = ttk.Style(self.root)
                style.configure("Metadata.Treeview", font=self.text_font, rowheight=rowheight)
                style.configure("Metadata.Treeview.Heading", font=self.text_font)
            except Exception:
                pass
        self.zoomfaktor = self.zoomfaktor * self.adjust_zoom
        self.image_zoom(self.zoomfaktor)

    def debug_info_resize(self, text):
        print("{:s} elapsed start resize".format(text))

    # ------------------------------------------------------------------
    # Fullscreen
    # ------------------------------------------------------------------
    def toggle_fullscreen(self, event=None):
        """Enter or leave fullscreen. Escape always leaves."""
        if self.is_fullscreen:
            self.exit_fullscreen()
            return

        self.is_fullscreen = True

        # Hide the side frames; the canvas fills the whole window.
        self.frame_1_1.place_forget()
        self.frame_1_2.place_forget()
        self.frame_2.place_forget()
        self.frame_canvas.place(relx=0, rely=0, relheight=1.0, relwidth=1.0)

        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", self.exit_fullscreen)

        # Show the overlay with the controls and start the mouse watch.
        self._show_controls_overlay()
        self._start_mouse_watch()

        # Redraw the image at the same zoom mode.
        self._reapply_zoom()

    def exit_fullscreen(self, event=None):
        """Leave fullscreen and restore the normal layout."""
        if not self.is_fullscreen:
            return
        self.is_fullscreen = False

        # Stop the timers.
        if self._hide_timer_id:
            self.root.after_cancel(self._hide_timer_id)
            self._hide_timer_id = None
        if self._mouse_watch_id:
            self.root.after_cancel(self._mouse_watch_id)
            self._mouse_watch_id = None

        self.root.attributes("-fullscreen", False)
        self.root.unbind("<Escape>")

        # Detach the overlay frames and put them back in their original position.
        self.frame_1_1.place_forget()
        self.frame_1_2.place_forget()
        self.frame_2.place_forget()

        gap = self._gap
        relw_frame_canvas = self._relw_frame_canvas
        relh_frame_canvas = self._relh_frame_canvas
        relw_frame_1 = self._relw_frame_1
        relw_frame_2 = self._relw_frame_2
        relh_1 = self._relh_1
        relh_2 = self._relh_2

        self.frame_canvas.place(relx=gap, rely=gap, relheight=relh_frame_canvas, relwidth=relw_frame_canvas)
        self.frame_1_1.place(relx=relw_frame_canvas + 2 * gap, rely=gap, relheight=relh_1, relwidth=relw_frame_1)
        self.frame_1_2.place(relx=relw_frame_canvas + relw_frame_1 + 3 * gap, rely=gap, relheight=relh_1, relwidth=relw_frame_1)
        self.frame_2.place(relx=relw_frame_canvas + 2 * gap, rely=relh_1 + 3 * gap, relheight=relh_2, relwidth=relw_frame_2 - 2 * gap)

        self._reapply_zoom()

    def _show_controls_overlay(self):
        """Show the control frames as an overlay on top of the canvas.

        The two button frames (frame_1_1, frame_1_2) are placed side by
        side on the right edge of the canvas, with a small margin so
        the vertical scrollbar of the canvas stays visible.
        """
        # Total width reserved for the two frames together, and the
        # margin to the right edge (room for the canvas scrollbar).
        total_width = 0.30
        scrollbar_margin = 0.02
        overlay_rely = 0.02
        overlay_height = 0.30

        left = 1.0 - total_width - scrollbar_margin

        # Two frames side by side, each half of total_width.
        self.frame_1_1.place(in_=self.frame_canvas,
                             relx=left,
                             rely=overlay_rely,
                             relheight=overlay_height,
                             relwidth=total_width / 2)
        self.frame_1_2.place(in_=self.frame_canvas,
                             relx=left + total_width / 2,
                             rely=overlay_rely,
                             relheight=overlay_height,
                             relwidth=total_width / 2)
        self.frame_1_1.lift()
        self.frame_1_2.lift()

        # Restart the hide timer.
        if self._hide_timer_id:
            self.root.after_cancel(self._hide_timer_id)
        self._hide_timer_id = self.root.after(2500, self._hide_controls_overlay)

    def _hide_controls_overlay(self):
        """Hide the control frames (leave fullscreen active)."""
        self._hide_timer_id = None
        if self.is_fullscreen:
            self.frame_1_1.place_forget()
            self.frame_1_2.place_forget()

    def _start_mouse_watch(self):
        """Watch the mouse position and show the controls on movement."""
        pos = (self.root.winfo_pointerx(), self.root.winfo_pointery())
        if pos != self._last_mouse_pos:
            self._last_mouse_pos = pos
            self._show_controls_overlay()

        if self.is_fullscreen:
            self._mouse_watch_id = self.root.after(150, self._start_mouse_watch)

    def _reapply_zoom(self):
        """Redraw the image at the current zoom mode after a layout change.

        If the user had 'Fit Canvas' active, we compute the fit factor
        again for the new canvas size. Otherwise we keep the current
        zoom factor.
        """
        self.root.update_idletasks()
        self.f.update_idletasks()
        if getattr(self, "_zoom_mode", "factor") == "fit":
            self.image_zoom(0)
        else:
            self.image_zoom(self.zoomfaktor)

    # ------------------------------------------------------------------
    # Canvas scrolling
    # ------------------------------------------------------------------
    def scrollx(self, amount, unit):
        self.f.xview_scroll(amount, unit)
        return "break"

    def scrolly(self, amount, unit):
        self.f.yview_scroll(amount, unit)
        return "break"

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------
    def fit_handler(self):
        self.button_fit()

    def print_handler(self):
        """Print button: fires a PrintRequestEvent. ..."""
        if self.imagetype != _RAW_IMAGETYPE:
            filename = self.file
        else:
            if self.image is None:
                # Image already released (window is closing). Ignore.
                return
            import uuid
            filename = os.path.join(
                Globals.temp_files_path,
                f"print_{uuid.uuid4().hex}.png"
            )
            self.image.save(filename, format="PNG")

        Globals.eventManager.generate(
            "PrintRequestEvent",
            PrintRequestEvent(filename, self)
        )

    def on_button_raw(self):
        """Toggle button for RAW images.

        After the window is opened, the embedded JPEG is shown. The first
        click loads the full sensor resolution (postprocess) and displays
        it. Further clicks toggle between embedded and full. The full
        image is loaded only once and cached in image_full. The button
        text shows what the next click will do.

        If loading the full image fails, an info box is shown and the
        state stays unchanged (embedded), so the user can try again.
        """
        if self.imagetype != _RAW_IMAGETYPE:
            return

        if self.raw_mode == "embedded":
            if self.image_full is None:
                if not self._load_full_raw():
                    return
            self.image = self.image_full
            self.raw_mode = "full"
            self.Button_raw.config(text="Use embedded")
            self.Label_rawinfo.config(text="RAW using FULL")
        else:
            self.image = self.image_embedded
            self.raw_mode = "embedded"
            self.Button_raw.config(text="raw full")
            self.Label_rawinfo.config(text="RAW using embedded")
        # Fit the image to the canvas so the visual difference between
        # embedded and full is immediately visible.
        self._zoom_mode = "fit"
        self.image_zoom(0)

    def fscale_handler(self):
        """Show the current image at 100% (pixel-for-pixel)."""
        self._zoom_mode = "factor"
        self.image_zoom(1)

    def _load_full_raw(self):
        """Load the full sensor resolution via postprocess().

        May take 1-2 seconds. Shows a hint in Label_rawinfo while loading.

        Returns:
            True on success (self.image_full is set)
            False on error (info_box shown, image_full stays None)
        """
        print(f"Loading full image {self.file}")
        import rawpy_loader
        old_text = self.Label_rawinfo.cget("text")
        self.Label_rawinfo.config(text="Loading full RAW...")
        self.root.update_idletasks()
        try:
            self.image_full = rawpy_loader.load_raw_full(self.file)
            return True
        except Exception as e:
            tools.info_box(
                f"RAW could not be loaded:\n{e}",
                "fehler"
            )
            self.Label_rawinfo.config(text=old_text)
            return False

    def on_button_state(self):
        """Toggle INCLUDE / EXCLUDE for this image."""
        if self.thumbnail.getState() == INCLUDE:
            new_state = EXCLUDE
        else:
            new_state = INCLUDE
        Globals.eventManager.generate(
            "FileStateChanged",
            FileStateEvent(self.file, new_state)
        )

    def on_button_all_meta(self):
        """Toggle between selected metadata and all metadata."""
        if not self.show_all_meta:
            all_meta = self._read_all_metadata()
            self._populate_metadata_tree(all_meta)
            self.Button_all_meta.config(text="view selected meta")
            self.show_all_meta = True
        else:
            self._populate_metadata_tree()
            self.Button_all_meta.config(text="view all meta")
            self.show_all_meta = False

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_closing(self, event):
        """Parent window is closing; close ourselves if we are the caller."""
        print(f"FSImage closing: {event.obj} {self.caller}") if self.debug else True
        if event.obj is self.caller:
            self.close_handler()

    def on_file_state_changed(self, event):
        """React to FileStateChanged for our own file."""
        if self.file == event.filename:
            print(f"FSIMAGE received state changed event, file: {self.file} event-file: {event.filename} state: {self.thumbnail.getState()} new state: {event.state}") if self.debug else True
            if event.state == INCLUDE:
                self.Button_exclude.config(text=self.str_exclude)
                self.Label_status.config(text=self.str_included)
            else:
                self.Button_exclude.config(text=self.str_include)
                self.Label_status.config(text=self.str_excluded)
            self.thumbnail.setState(event.state)

    def close_handler(self):
        """Unbind events, fire ClosingEvent, destroy the window."""
        # Cancel fullscreen timers so nothing fires after destroy.
        if self._hide_timer_id:
            try:
                self.root.after_cancel(self._hide_timer_id)
            except Exception:
                pass
            self._hide_timer_id = None
        if self._mouse_watch_id:
            try:
                self.root.after_cancel(self._mouse_watch_id)
            except Exception:
                pass
            self._mouse_watch_id = None

        Globals.eventManager.unbind("FileStateChanged", self.on_file_state_changed)
        Globals.eventManager.unbind("Closing", self.on_closing)
        Globals.eventManager.generate(
            "Closing",
            ClosingEvent(self.file, self)
        )
        self._close_images()
        self.root.destroy()

    def _close_images(self):
        """Close all images held in memory (idempotent)."""
        for attr in ("image_embedded", "image_full"):
            img = getattr(self, attr, None)
            if img is not None:
                try:
                    img.close()
                except Exception:
                    pass
                setattr(self, attr, None)
        self.image = None

    # ------------------------------------------------------------------
    # Mouse wheel zoom
    # ------------------------------------------------------------------
    def mousewheel_handler(self, event):
        zoomincrement = (event.delta / 120) / 100
        if zoomincrement > 0:
            if self.zoomfaktor + zoomincrement <= 1:
                newzoomfaktor = self.zoomfaktor + zoomincrement
            else:
                newzoomfaktor = 1.0
        else:
            if self.zoomfaktor + zoomincrement >= .1:
                newzoomfaktor = self.zoomfaktor + zoomincrement
            else:
                newzoomfaktor = .1
        self.zoomfaktor = newzoomfaktor
        self._zoom_mode = "factor"
        self.image_zoom(self.zoomfaktor)

    def button_fit(self):
        """Fit the image to the canvas (zoom factor computed automatically)."""
        self._zoom_mode = "fit"
        self.image_zoom(0)

    def image_zoom(self, zoomfaktor):
        """Show self.image on the canvas with the given zoom factor.

        zoomfaktor == 0 means: compute the factor so the image fits the canvas.
        zoomfaktor == 1 means: 100% (pixel-for-pixel).
        """
        image_width_orig, image_height_orig = self.image.size
        self.f.update()
        canvas_width = self.f.winfo_width()
        canvas_height = self.f.winfo_height()
        if zoomfaktor == 0:
            faktor = min(canvas_height / image_height_orig, canvas_width / image_width_orig)
            self.zoomfaktor = faktor
            print("... calculate faktor for Image to fit in Canvas")
        else:
            faktor = zoomfaktor
            self.zoomfaktor = faktor

        newsize = (int(image_width_orig * faktor), int(image_height_orig * faktor))
        r_img = self.image.resize(newsize, Image.Resampling.NEAREST)
        self.pimg = ImageTk.PhotoImage(r_img)
        self.f.delete('images')
        self.id = self.f.create_image(0, 0, anchor='nw', image=self.pimg, tags='images')
        self.f.tag_raise("rect")
        self.f.tag_raise("text")
        self.f.update()

        if newsize[0] <= canvas_width:
            self.H_I.pack_forget()
        else:
            self.H_I.pack(side=BOTTOM, fill=BOTH)
        if newsize[1] <= canvas_height:
            self.V_I.pack_forget()
        else:
            self.V_I.pack(side=RIGHT, fill=Y)

        self.f.config(scrollregion=self.f.bbox("all"))

    # ------------------------------------------------------------------
    # Metadata read all
    # ------------------------------------------------------------------
    def _read_all_metadata(self):
        """Read ALL available metadata.

        For JPEG/PNG/TIFF: img.info, PNG text chunks, EXIF.
        For RAW: combined data from load_raw_metadata (curated) and
        load_raw_all_exif (all EXIF tags from the embedded JPEG).
        Returns: {category: {key: value, ...}, ...}
        """
        # --- RAW ---
        if self.imagetype == _RAW_IMAGETYPE:
            import rawpy_loader
            result = rawpy_loader.load_raw_metadata(self.file)
            extra = rawpy_loader.load_raw_all_exif(self.file)
            for cat, entries in extra.items():
                result.setdefault(cat, {}).update(entries)
            return result

        # --- STILL ---
        from PIL import ExifTags
        TAGS = ExifTags.TAGS
        GPSTAGS = ExifTags.GPSTAGS
        result = {}

        def _stringify(v):
            from PIL.TiffImagePlugin import IFDRational
            if isinstance(v, bytes):
                try:
                    s = v.decode("ascii")
                    if s.isprintable():
                        return s
                except Exception:
                    pass
                if len(v) <= 16:
                    return v.hex(" ")
                return f"(binary, {len(v)} bytes)"
            if isinstance(v, (tuple, list)):
                return ", ".join(_stringify(x) for x in v)
            if isinstance(v, dict):
                return "{" + ", ".join(f"{k}={_stringify(x)}" for k, x in v.items()) + "}"
            if isinstance(v, IFDRational):
                try:
                    if v.denominator == 1:
                        return str(v.numerator)
                    return f"{v.numerator}/{v.denominator}"
                except Exception:
                    return str(v)
            return str(v)

        try:
            with Image.open(self.file) as img:
                info = {}
                for k, v in (img.info or {}).items():
                    if k == "exif":
                        continue
                    info[k] = _stringify(v)
                if info:
                    result["Info"] = info

                png_text = getattr(img, "text", None)
                if png_text:
                    result["Text"] = {k: _stringify(v) for k, v in png_text.items()}

                exif = img.getexif()
                if exif:
                    main = {}
                    for tag_id, value in exif.items():
                        tag_name = TAGS.get(tag_id, str(tag_id))
                        if tag_name in ("ExifOffset", "GPSInfo", "InteropOffset"):
                            try:
                                sub = exif.get_ifd(tag_id)
                            except Exception:
                                sub = {}
                            if tag_name == "GPSInfo":
                                result["GPS"] = {
                                    GPSTAGS.get(k, str(k)): _stringify(v)
                                    for k, v in sub.items()
                                }
                            else:
                                cat = "Exif" if tag_name == "ExifOffset" else "Interop"
                                result[cat] = {
                                    TAGS.get(k, str(k)): _stringify(v)
                                    for k, v in sub.items()
                                }
                        else:
                            main[tag_name] = _stringify(value)
                    if main:
                        result["EXIF"] = main
        except Exception as e:
            print(f"Error reading metadata: {e}") if self.debug else True
        return result
        
    # ------------------------------------------------------------------
    # Metadata treeview content
    # ------------------------------------------------------------------
    def _populate_metadata_tree(self, metadata=None):
        """Fill the treeview with metadata.

        metadata=None -> thumbnail.metadata.
        metadata=dict -> use this structure instead.
        """
        tree = self.tree_metadata
        for item in tree.get_children(""):
            tree.delete(item)
        if metadata is None:
            metadata = self.thumbnail.metadata
        if not metadata:
            tree.insert("", "end", text="", values=("", NO_METADATA_TEXT))
            return
        prev_cat = None
        for category, entries in metadata.items():
            if not entries:
                continue
            cat_text = "" if category == prev_cat else str(category)
            prev_cat = category
            first_in_cat = True
            for key, value in entries.items():
                tree.insert("", "end",
                            text=cat_text if first_in_cat else "",
                            values=(str(key), str(value)))
                first_in_cat = False

    def __del__(self):
        self.a = 1
        #print("*** Deleting FSImage object. File is " + str(self.file))