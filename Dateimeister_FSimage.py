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

# Imagetype-Werte, fuer die der RAW-Sonderpfad gilt.
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
        # Imagetype aus dem Thumbnail (kein Fallback auf Globals.imagetype).
        # ------------------------------------------------------------------
        self.imagetype = thumbnail.get_imagetype() if thumbnail is not None else None
        if self.imagetype is None:
            raise RuntimeError(
                "MyFSImage: thumbnail.get_imagetype() lieferte None. "
                "Das Thumbnail muss vor dem Oeffnen von MyFSImage "
                "mit set_imagetype() initialisiert werden."
            )

        # ------------------------------------------------------------------
        # Bild laden. Bei RAW zwei Varianten: eingebettetes JPEG (schnell)
        # und volle Sensor-Auflaesung (langsam, lazy).
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
        relh_button = .25

        dict_widgets = {}
        dict_widgets["1"] = {
          "WIDGET": tk.Label, "VAR": "future_use", "OFFSET": 0.00, "RELH": .6, "RELW": relw_button,
          "ANCHOR": "START", "TEXT": "future_use", "FONT": self.text_font}
        dict_widgets["2"] = {
          "WIDGET": tk.Button, "VAR": "Button_fit", "OFFSET": 0.00, "RELH": relh_button, "RELW": relw_button,
          "ANCHOR": "START", "CALLBACK": self.fit_handler,
          "TEXT": "Fit Canvas", "STATE": tk.ACTIVE, "TT": "Scale Image to fit", "FONT": self.text_font}
        dict_widgets["3"] = {
          "WIDGET": tk.Button, "VAR": "Button_exclude", "OFFSET": 0.00, "RELH": relh_button, "RELW": relw_button,
          "ANCHOR": "START", "CALLBACK": self.on_button_state,
          "TEXT": "Exclude", "STATE": tk.ACTIVE, "TT": "include / exclude", "FONT": self.text_font}
        dict_widgets["4"] = {
          "WIDGET": tk.Button, "VAR": "Button_all_meta", "OFFSET": 0.00, "RELH": relh_button, "RELW": relw_button,
          "ANCHOR": "START", "CALLBACK": self.on_button_all_meta,
          "TEXT": "view all meta", "STATE": tk.ACTIVE, "TT": "view all metadata", "FONT": self.text_font}
        tools.create_widgets_from_dict(dict_widgets, self.frame_1_1, "VERTICAL", font=self.text_font, bgcolor=tools._bgcolor)

        dict_widgets = {}
        dict_widgets["1"] = {
          "WIDGET": tk.Label, "VAR": "Label_fileinfo", "OFFSET": 0.00, "RELH": .6, "RELW": relw_button,
          "ANCHOR": "START", "TEXT": "file info", "FONT": self.text_font, "JUSTIFY": "left"}
        dict_widgets["2"] = {
          "WIDGET": tk.Button, "VAR": "Button_fscale", "OFFSET": 0.00, "RELH": relh_button, "RELW": relw_button,
          "ANCHOR": "START", "CALLBACK": self.fscale_handler,
          "TEXT": "Full scale", "STATE": tk.ACTIVE, "TT": "show image in full resolution", "FONT": self.text_font}
        dict_widgets["3"] = {
          "WIDGET": tk.Label, "VAR": "Label_status", "OFFSET": 0.00, "RELH": relh_button, "RELW": relw_button,
          "ANCHOR": "START", "TEXT": "In/Ex", "FONT": self.text_font}
        dict_widgets["4"] = {
          "WIDGET": tk.Button, "VAR": "Button_print", "OFFSET": 0.0, "RELH": relh_button, "RELW": relw_button,
          "ANCHOR": "START", "CALLBACK": self.print_handler,
          "TEXT": "Print", "STATE": tk.ACTIVE, "TT": "send image to print preview", "FONT": self.text_font}
        tools.create_widgets_from_dict(dict_widgets, self.frame_1_2, "VERTICAL", font=self.text_font, bgcolor=tools._bgcolor)

        self.f = tk.Canvas(self.frame_canvas)
        self.f.configure(background="#d9d9d9")
        self.f.configure(borderwidth="2")
        self.f.configure(highlightbackground="#d9d9d9")
        self.f.configure(highlightcolor="black")
        self.f.configure(insertbackground="black")
        self.f.configure(relief="ridge")
        self.f.configure(selectbackground="#c4c4c4")
        self.f.configure(selectforeground="black")

        self.V_I = Scrollbar(self.frame_canvas)
        self.V_I.config(command=self.f.yview)
        self.f.config(yscrollcommand=self.V_I.set)
        self.H_I = Scrollbar(self.frame_canvas, orient=HORIZONTAL)
        self.H_I.config(command=self.f.xview)
        self.f.config(xscrollcommand=self.H_I.set)

        tools.place_box_with_scrollbars(self, self.frame_canvas, self.f, self.H_I, self.V_I,
                                        rw=0.01, d_n=0.0, d_e=0.0, d_s=0.0, d_w=0.0)

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

        self.f.bind("<MouseWheel>", self.mousewheel_handler)
        self.root.protocol("WM_DELETE_WINDOW", self.close_handler)

        self.root.title(str_title_prefix + file)
        self.show_all_meta = False

        Globals.eventManager.bind("FileStateChanged", self.on_file_state_changed)
        Globals.eventManager.bind("Closing", self.on_closing)

        self.zoomfaktor = 1.0
        self.f.focus_set()
        self.image_zoom(self.zoomfaktor)

        mytext = "{:s}\ncreated {:s} size {:.3f}".format(
            thumbnail.getFile(), thumbnail.get_filectime(), thumbnail.get_filesize())
        self.Label_fileinfo.configure(text=mytext)

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

    def display_progress(self, progress: int):
        self.scale_progress.set(progress)

    def on_scale_motion(self, event):
        self.preview_engine.show_preview(event, self.scale_progress.winfo_width())

    def activate(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

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

    def scrollx(self, amount, unit):
        self.f.xview_scroll(amount, unit)
        return "break"

    def scrolly(self, amount, unit):
        self.f.yview_scroll(amount, unit)
        return "break"

    def fit_handler(self):
        self.button_fit()

    def print_handler(self):
        """Print button: fires a PrintRequestEvent.

        Der Aufrufer ist dafuer verantwortlich, dass die Datei, die an
        den PrintPreview uebergeben wird, druckbar ist. Bei RAW-Dateien
        wird das aktuell angezeigte Bild (eingebettetes JPEG oder volle
        Sensor-Auflaesung) als temporaere PNG-Datei exportiert, weil
        PrintPreview mit PIL.Image.open arbeitet und keine RAW-Formate
        lesen kann. Bei allen anderen Imagetypen wird der Originalpfad
        uebergeben.

        Was gedruckt wird, entspricht immer dem, was aktuell auf dem
        Canvas sichtbar ist. Will der Nutzer die volle RAW-Auflaesung
        drucken, muss er vorher auf 'Full scale' klicken.
        """
        if self.imagetype != _RAW_IMAGETYPE:
            # Nicht-RAW: Originaldatei geht direkt an den PrintPreview.
            filename = self.file
        else:
            # RAW: aktuell angezeigtes Bild als PNG exportieren.
            import uuid
            filename = os.path.join(
                Globals.temp_files_path,
                f"print_{uuid.uuid4().hex}.png"
            )
            # self.image zeigt auf image_embedded oder image_full -
            # also genau das, was gerade auf dem Canvas dargestellt ist.
            self.image.save(filename, format="PNG")

        Globals.eventManager.generate(
            "PrintRequestEvent",
            PrintRequestEvent(filename, self)
        )

    def fscale_handler(self):
        """Button 'Full scale'.

        Nicht-RAW: zeigt das Bild in voller Aufloesung (zoomfaktor 1).

        RAW: schaltet zwischen eingebettetem JPEG (schnell, evtl. kleiner
        als der Sensor) und voller Sensor-Auflaesung (langsam, postprocess).
        Der Button-Text zeigt, was der naechste Klick tut.
        """
        if self.imagetype == _RAW_IMAGETYPE:
            if self.raw_mode == "embedded":
                self._load_full_raw()
                self.raw_mode = "full"
                self.Button_fscale.config(text="Use embedded")
            else:
                self.image = self.image_embedded
                self.raw_mode = "embedded"
                self.Button_fscale.config(text="Full scale")
            self.image_zoom(1)
        else:
            self.image_zoom(1)

    def _load_full_raw(self):
        """Laedt die volle Sensor-Aufloesung per postprocess().

        Kann 1-2 Sekunden dauern. Zeigt waehrenddessen einen Hinweis
        im Status-Label.
        """
        import rawpy_loader
        self.Label_status.config(text="Loading full RAW...")
        self.root.update_idletasks()
        try:
            self.image_full = rawpy_loader.load_raw_full(self.file)
        except Exception as e:
            tools.info_box(f"RAW konnte nicht geladen werden: {e}", "fehler")
            return
        self.image = self.image_full

    def on_button_state(self):
        if self.thumbnail.getState() == INCLUDE:
            new_state = EXCLUDE
        else:
            new_state = INCLUDE
        Globals.eventManager.generate(
            "FileStateChanged",
            FileStateEvent(self.file, new_state)
        )

    def on_button_all_meta(self):
        """Wechselt zwischen 'nur Auswahl' und 'alle Metadaten'."""
        if not self.show_all_meta:
            all_meta = self._read_all_metadata()
            self._populate_metadata_tree(all_meta)
            self.Button_all_meta.config(text="view selected meta")
            self.show_all_meta = True
        else:
            self._populate_metadata_tree()
            self.Button_all_meta.config(text="view all meta")
            self.show_all_meta = False

    def on_closing(self, event):
        print(f"Duplicate closing: {event.obj} {self.caller}") if self.debug else True
        self._close_images()
        if event.obj is self.caller:
            self.close_handler()

    def on_file_state_changed(self, event):
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
        Globals.eventManager.unbind("FileStateChanged", self.on_file_state_changed)
        Globals.eventManager.unbind("Closing", self.on_closing)
        Globals.eventManager.generate(
            "Closing",
            ClosingEvent(self.file, self)
        )
        self._close_images()
        self.root.destroy()

    def _close_images(self):
        """Schliesst alle im Speicher gehaltenen Bilder (idempotent)."""
        for attr in ("image_embedded", "image_full"):
            img = getattr(self, attr, None)
            if img is not None:
                try:
                    img.close()
                except Exception:
                    pass
                setattr(self, attr, None)
        self.image = None

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
        self.image_zoom(self.zoomfaktor)

    def button_fit(self):
        self.image_zoom(0)

    def image_zoom(self, zoomfaktor):
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
        """Liest ALLE verfuegbaren Metadaten.

        Bei JPEG/PNG/TIFF: img.info, PNG text-Chunks, EXIF.
        Bei RAW: kombinierte Daten aus load_raw_metadata (kuratiert) und
        load_raw_all_exif (alle EXIF-Tags aus dem eingebetteten JPEG).
        Liefert: {category: {key: value, ...}, ...}
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
        """Fuellt den Treeview mit Metadaten.
        metadata=None -> thumbnail.metadata.
        metadata=dict -> diese Struktur verwenden.
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