import os
import tkinter as tk
from tkinter.constants import *
from tkinter import filedialog as fd
from tkinter import messagebox
from tkinter.font import Font
import tkinter.ttk as ttk

from PIL import Image, ImageTk, ImageDraw, ExifTags
import Tooltip as TT
import time
from datetime import datetime, timezone
from time import gmtime, strftime
import operator
import argparse

import ctypes
import sys
import hashlib
import re
import configparser 
import Undo_Redo as UR
import dateimeister_config_xml as DX
import dateimeister_generator as DG
import Dateimeister_exec as DM
import Dateimeister_FSimage as FS
import Dateimeister_processlist as DP
import Dateimeister_camera as DCAM
import print_utils
from print_preview import PrintPreview

import tools
from tools import Globals, INCLUDE, EXCLUDE, FileStateEvent, ClosingEvent, PrintRequestEvent, CameraChangedEvent

from ini_validator import load_and_validate_ini 

import cv2
import matplotlib.pyplot as plt

from enum import Enum
class action(Enum):
    PRESS   = 1
    RELEASE = 2
class dragposition(Enum):
    BEFORE  = 1
    BEHIND  = 2
    
CFG_NEW          = 0
CFG_OPEN_CONFIG       = 1
CFG_OPEN_APPLY_CONFIG = 2
CFG_SAVE_CONFIG       = 3
CFG_SAVE_CONFIG_AS    = 4
CFG_APPLY_CONFIG      = 5
CFG_OPEN_RECENT       = 6

NEW_INDIR             = 0
NEW_OUTDIR            = 1
FILE_OPEN             = 2
FILE_CLOSE            = 3
FILE_EXIT             = 4
FILE_OPEN_RECENT      = 5

class pt(Enum):
    DROP_FROM_SOURCE  = 1
    DROP_FROM_TARGET  = 2
    COPY_SELECTED     = 3
    COPY_SINGLE       = 4
    DELETE_SELECTED   = 5
    DELETE_SINGLE     = 6
    COPY_SELECTED_HEAD = 7
    COPY_SELECTED_TAIL = 8
    

# process types as configured per suffix in the camera xml
PROCESS_JPEG     = "JPEG"
PROCESS_USE_JPEG = "USE_JPEG"
PROCESS_RAW      = "RAW"
# labels of the file-menu entries (addressed by label, not by index)
MENU_LABEL_CHOOSE_PRINTER = "Choose Printer..."
MENU_LABEL_PRINT          = "Print selected"

class ScrollableCanvas(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.select_ctr = 0

    def on_configure(self, event):
        self.configure(scrollregion=self.bbox("all"))
        #print ("<Configure> called")

class MyImage:
    def __init__(self, filename, mts, canvas, tag):
        self.filename = filename
        self.mts = mts
        self.tag = tag
        self.canvas = canvas
        self.selected = 0
        self.was_selected = False
        # file statistics for tooltip, FSImage display
        statinfo = os.stat(filename)
        st_ctime = statinfo.st_ctime
        st_mtime = statinfo.st_mtime
        self.filectime = datetime.fromtimestamp(st_ctime).strftime('%Y-%m-%d %H:%M')
        self.filemtime = datetime.fromtimestamp(st_mtime).strftime('%Y-%m-%d %H:%M')
        self.filesize  = os.stat(filename).st_size/(1024*1024.0) 
        
    def get_filectime(self):
        return self.filectime
        
    def get_filemtime(self):
        return self.filemtime
        
    def get_filesize(self):
        return self.filesize
                        
    def getFile(self):
        return self.filename    

    def get_filename(self):
        return self.filename
    def get_mts(self):
        return self.mts
    def get_image(self):
        return Diatisch.dict_filename_images[Diatisch.idx_akt][self.filename]
    def get_image_from_index(self, index): # used for process_list which gets index from historized process
        return Diatisch.dict_filename_images[index][self.filename]
    def get_ctr(self):
        return self.selected
    def select(self, canvas, ctr):
        #print("  find with tag ", self.tag, ": ", str(self.canvas.find_withtag(self.tag)))
        for i in canvas.find_withtag(self.tag):
            canvas.itemconfigure(i, state = 'normal')
        if not self.is_selected(): 
            changed = True
        else:
            changed = False
        self.selected = ctr
        return changed # True if prior state was not selected, False otherwise
    def unselect(self, canvas):
        for i in canvas.find_withtag(self.tag):
            canvas.itemconfigure(i, state = 'hidden')
        if not self.is_selected(): 
            changed = False
        else:
            changed = True
        self.selected = 0
        return changed # True if prior state was selected, False otherwise
    def is_selected(self):
        if self.selected > 0:
            return True
        else:
            return False
    def get_tag(self):
        return self.tag
    # type (e.g. JPEG, RAW) and process type (JPEG, USE_JPEG, RAW) are looked up by filename, so that
    # copies of MyImage (history, target) need no extra constructor parameters
    @property
    def imgtype(self):
        return Diatisch.dict_file_meta.get(self.filename, ("", ""))[0]
    @property
    def process_type(self):
        return Diatisch.dict_file_meta.get(self.filename, ("", ""))[1]
        
     
class Thumbnail:
    #image = "" # hier stehen Klassenvariablen, im Gegensatz zu den Instanzvariablen
    # The class "constructor" - It's actually an initializer 
    def __init__(self, image, file, player, canvas, debug, canvas_type, fs_close, fs_button, process_type = None, showfile = None):
        self.image = image
        self.file = file
        self.showfile = showfile if showfile else file
        self.process_type = (process_type if process_type else getattr(image, "process_type", "")) or ""
        self.process_type = self.process_type.upper()
        self.player = player 
        self.fsimage = None
        self.state = FS.INCLUDE
        self.canvas = canvas
        self.debug = debug
        self.canvas_type = canvas_type
        self.fs_close = fs_close # called on unregister = close
        self.fs_button = fs_button # called on button pressed
        #self.setState(self.state)
        # file statistics for tooltip, FSImage display
        statinfo = os.stat(file)
        st_ctime = statinfo.st_ctime
        st_mtime = statinfo.st_mtime
        self.filectime = datetime.fromtimestamp(st_ctime).strftime('%Y-%m-%d %H:%M')
        self.filemtime = datetime.fromtimestamp(st_mtime).strftime('%Y-%m-%d %H:%M')
        self.filesize  = os.stat(file).st_size/(1024*1024.0) 

        # ------------------------------------------------------------------
        # Metadata store: always exists, so MyFSImage can always access it.
        # The categories match tools.MyThumbnail so MyFSImage can treat
        # both thumbnail types alike.
        # ------------------------------------------------------------------
        self.metadata = {
            "EXIF": {},
            "GPS": {},
            "Video": {},
            "File": {},
            "General": {},
        }
        self.metadata_read = False

    # ------------------------------------------------------------------
    # Metadata (needed by MyFSImage._populate_metadata_tree)
    # ------------------------------------------------------------------
    def set_metadata(self):
        """Read metadata once. For Diatisch only still images are shown
        (RAW handled via rawpy, everything else via PIL/EXIF)."""
        if self.metadata_read:
            return
        path = self.file
        if not os.path.exists(path):
            self.metadata_read = True
            return
        try:
            if self.is_raw():
                import rawpy_loader
                raw_meta = rawpy_loader.load_raw_metadata(path)
                for cat, entries in raw_meta.items():
                    self.metadata.setdefault(cat, {}).update(entries)
            else:
                ex = self._extract_useful_exif(path)
                for k, v in ex.items():
                    self.metadata["EXIF"][k] = v
            stat = os.stat(path)
            self.metadata["File"]["Size"] = str(stat.st_size)
            self.metadata["File"]["Modified"] = datetime.fromtimestamp(
                stat.st_mtime).strftime('%Y-%m-%d %H:%M')
        except Exception as e:
            print(f"Thumbnail.set_metadata: {path}: {type(e).__name__}: {e}") if self.debug else True
        self.metadata_read = True

    @staticmethod
    def _extract_useful_exif(path):
        """Same selection of tags as tools.MyThumbnail.extract_useful_exif."""
        useful = {}
        try:
            img = Image.open(path)
            exif = img.getexif()
            if not exif:
                return useful
            tag_map = {v: k for k, v in ExifTags.TAGS.items()}

            def get(tag_name):
                tag_id = tag_map.get(tag_name)
                if tag_id in exif:
                    return str(exif[tag_id])
                return None

            if (v := get("FNumber")):
                useful["Aperture"] = f"f/{v}"
            if (v := get("ExposureTime")):
                useful["Exposure Time"] = v
            if (v := get("ISOSpeedRatings")):
                useful["ISO"] = v
            if (v := get("FocalLength")):
                useful["Focal Length"] = v
            if (v := get("Model")):
                useful["Camera Model"] = v
            if (v := get("DateTimeOriginal")):
                useful["Original Date"] = v
            if (v := get("ExposureBiasValue")):
                useful["Exposure Bias Value"] = v
            if (v := get("WhiteBalance")):
                useful["White Balance"] = v
            if (v := get("Orientation")):
                useful["Orientation"] = v
            w, h = img.size
            useful["Width"] = str(w)
            useful["Height"] = str(h)
        except Exception:
            pass
        return useful

    def get_metadata(self):
        return self.metadata

    def get_filectime(self):
        return self.filectime
        
    def get_filemtime(self):
        return self.filemtime
        
    def get_filesize(self):
        return self.filesize
                        
    def getFile(self):
        return self.file    
  
    def get_image(self):
        return self.image
        
    def setState(self, state, caller = None, do_save = True):
        print("Thumbnail.setState, state = {:d}".format(state)) if self.debug else True
        if state != self.state:
            state_changed = True
        else:
            state_changed = False
        self.state = state # neuer Status
        if self.fsimage is not None: #call fsimage.exclude_call
            self.fsimage.exclude_call(state) # synchronisiert das FSImge, falls vorhanden
            if self.fs_button is not None: #call button-method if exists and fsimage is none
                self.fs_button(self.canvas_type, self, self.state, self.image)

    def getState(self):
        return self.state   

    def register_FSimage(self, fsimage):
        self.fsimage = fsimage
        if fsimage is None and self.fs_close is not None: #call close-method if exists and fsimage is none
            self.fs_close(self.canvas_type, self, self.state, self.image)

    def getPlayer(self):
        return self.player   

    def get_imagetype(self): # FSImage expects this method
        return 'STILL'

    # same query methods as tools.MyThumbnail, so that FSImage can treat both alike
    def is_raw(self):
        return self.process_type == PROCESS_RAW

    def is_video(self):
        return False

    def is_broken(self):
        return False

    def get_process_type(self):
        return self.process_type

    def getShowfile(self):
        return self.showfile

    def __del__(self):
        if self.player is not None:
            self.player.pstop()
            del self.player
        print("*** Deleting Thumbnail-Objekt. " + self.file)


class Diatisch:
    line_width = 5
    line_color = "red"
    # 20240813 we want to store images only once per canvas not in every MyImage-object, access is via filename which is stored in MyImage object
    #  we need dict as a "global" class variable because we want to access it also from methods of MyImage-objects.
    idx_high = 0 # Index into dict, incrementented by each call to load images
    idx_akt  = 0 # current index into dict according to history (undo / redo)
    dict_filename_images = {}
    dict_filename_images[idx_akt] = {} # Filename -> MyImage contains all source filenames which is sufficient as target files are a subset of source files
    dict_file_meta = {} # filename -> (type, process type), used by MyImage.imgtype / process_type
    def __init__(self, debug, root = None, list_imagefiles = None, list_result = None, callback = None): # if called from own main root will be initialized there
        if root is None:
            self.root = tk.Toplevel()
        else:
            self.root = root
        self.title = "Diatisch"

        self.text_font = Font(family="Helvetica", size=6)
        self.timer = tools.RestartableTimer(self.root, 666, self.resize)  # ms

        self.root.title(self.title)
        self.dirchk = tools.DirChecker(self.root, debug)   # Hintergrundpruefung der Verzeichnisse/Dateien (siehe tools.py)
        self.list_imagefiles = list_imagefiles
        #print("List Imagefiles is: " + str(list_imagefiles))
        # Fenstergröße
        self.physical_width  = self.root.winfo_screenwidth()
        self.physical_height = self.root.winfo_screenheight()
        self.screen_width  = int(self.root.winfo_screenwidth() * .75) # adjust as needed
        self.screen_height = int(self.root.winfo_screenheight() * .5) # adjust as needed
        print("Bildschirm ist " + str(self.screen_width) + " x " + str(self.screen_height) + " physical: " + str(self.physical_width) + " x " + str(self.physical_height))
        v_dim=str(self.screen_width)+'x'+str(self.screen_height)
        self.root.geometry(v_dim)
        self.root.minsize(int(self.physical_width / 2), int(self.physical_height / 2))  # (minimum ) width , ( minimum) height

        self.m, self.n = 10, 5
        self.image_width = 1500  # Adjust as needed
        self.row_height  = 200
        self.xpos = 0
        self.ypos = 0
        self.root.bind("<Configure>", self.on_configure) # we want to know if size changes
        
        print("Diatisch Debug is: ", debug)
        if debug == 'Y' or debug == 'y':
            self.debug   = True # debug all
            self.debug_p = True # debug process history
        elif debug == 'N' or debug == 'n' or not debug:
            self.debug   = False # no debug all
            self.debug_p = False # no debug process history
        elif debug == 'P' or debug == 'p':
            self.debug   = False # no debug all
            self.debug_p = True  # debug process history
        else:
            print("Debug parameter {:s} not allowed, only j, n or p".format(debug))
            exit(-1)

        self.width  = 0
        self.height = 0

        self.frame_labels_height = 0.04 # needed for calculation of font size
        self.label_height = 0.8 # needed for calculation of font size
        labels_w = .47

        self.Frame_labels = tk.Frame(self.root)
        self.Frame_labels.place(relx=.0, rely=0.00, relheight=self.frame_labels_height, relwidth=labels_w)
        self.Frame_labels.configure(relief='flat')
        self.Frame_labels.configure(background=tools._bgcolor_dbg) if self.debug else True # uncomment for same colour as window (default) or depend on debug

        #set some defaults
        relw_button = 0.1
        relh_button = 0.8
        relw_label = 0.2
        relh_label = 0.8
        gap = 0.0

        # the sort radio buttons
        self.rbvalue = tk.StringVar()
        self.dict_sort_method = {} # here we keep type(JPEG...) -> sort method(1...4)
        self.rbg = tk.StringVar()

        dict_widgets = {}
        dict_widgets["0"] = {
          "WIDGET":tk.Label,"VAR":"Label_source_ctr","OFFSET":gap,"RELH":relh_label,"RELW":relw_label,"ANCHOR":"CENTER","TEXT":"Num Images Source: 0","FONT":self.text_font}
        dict_widgets["1"] = {
          "WIDGET":tk.Radiobutton,"VAR":"rb_g1","OFFSET":0.00,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"CENTER","CALLBACK":self.rb_g,
          "RB_VAR":self.rbg,"RB_VALUE":"1","TEXT":"sort within type","STATE":tk.NORMAL,"TT":"sort images within type first","FONT":self.text_font}
        dict_widgets["2"] = {
          "WIDGET":tk.Radiobutton,"VAR":"rb_g2","OFFSET":0.00,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"CENTER","CALLBACK":self.rb_g,
          "RB_VAR":self.rbg,"RB_VALUE":"2","TEXT":"sort all","STATE":tk.NORMAL,"TT":"sort images globally over all types","FONT":self.text_font}
        dict_widgets["3"] = {
          "WIDGET":tk.Radiobutton,"VAR":"rb_sort_canvas1","OFFSET":0.01,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"CENTER","CALLBACK":self.rb_sort,
          "RB_VAR":self.rbvalue,"RB_VALUE":"1","TEXT":"sort name asc","STATE":tk.NORMAL,"TT":"sort images by name(ascending)","FONT":self.text_font}
        dict_widgets["4"] = {
          "WIDGET":tk.Radiobutton,"VAR":"rb_sort_canvas2","OFFSET":0.00,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"CENTER","CALLBACK":self.rb_sort,
          "RB_VAR":self.rbvalue,"RB_VALUE":"2","TEXT":"sort name desc","STATE":tk.NORMAL,"TT":"sort images by name(descending)","FONT":self.text_font}
        dict_widgets["5"] = {
          "WIDGET":tk.Radiobutton,"VAR":"rb_sort_canvas3","OFFSET":0.00,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"CENTER","CALLBACK":self.rb_sort,
          "RB_VAR":self.rbvalue,"RB_VALUE":"3","TEXT":"sort mod. asc","STATE":tk.NORMAL,"TT":"sort images by modification date(ascending)","FONT":self.text_font}
        dict_widgets["6"] = {
          "WIDGET":tk.Radiobutton,"VAR":"rb_sort_canvas4","OFFSET":0.00,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"CENTER","CALLBACK":self.rb_sort,
          "RB_VAR":self.rbvalue,"RB_VALUE":"4","TEXT":"sort mod. desc","STATE":tk.NORMAL,"TT":"sort images by modification date(descending)","FONT":self.text_font}
        tools.create_widgets_from_dict(dict_widgets, self.Frame_labels, "HORIZONTAL", font = self.text_font, bgcolor = tools._bgcolor)
        self.rbg.set("1")
        self.rbvalue.set("1")
        
        # Frame for process_id, camera and num target
        self.Frame_labels2 = tk.Frame(self.root)
        self.Frame_labels2.place(relx=labels_w, rely=0.00, relheight=self.frame_labels_height, relwidth=0.98-labels_w)
        self.Frame_labels2.configure(relief='flat')
        self.Frame_labels2.configure(background=tools._bgcolor_dbg) if self.debug else True # uncomment for same colour as window (default) or depend on debug

        # create label for process_id, camera information and button (change camera) and label for target counter
        relh = .8
        gap = .001
        # for the combobox
        self.cb_camera_var = tk.StringVar(value="Test")
        
        dict_widgets = {}
        dict_widgets["1"] = {
          "WIDGET":tk.Label,"VAR":"Label_process_id","OFFSET":gap,"RELH":self.label_height,"RELW":.12,"ANCHOR":"CENTER","TEXT":"Process ID: 0","FONT":self.text_font}
        dict_widgets["2"] = {
          "WIDGET":tk.Label,"VAR":"Label_camera","OFFSET":gap,"RELH":self.label_height,"RELW":.1,"ANCHOR":"CENTER","TEXT":"Camera: ","FONT":self.text_font}
        dict_widgets["3"] = {
          "WIDGET":ttk.Combobox,"VAR":"cb_camera","OFFSET":gap,"RELH":70,"RELW":.5,"ANCHOR":"CENTER","FONT":self.text_font}
        dict_widgets["4"] = {
          "WIDGET":tk.Button,"VAR":"button_camera","OFFSET":gap,"RELH":relh,"RELW":.15,"ANCHOR":"CENTER","CALLBACK":self.button_camera_pressed,
          "TEXT":"edit camera...","STATE":tk.ACTIVE,"TT":"Choose camera...","FONT":self.text_font}
        dict_widgets["5"] = {
          "WIDGET":tk.Label,"VAR":"Label_target_ctr","OFFSET":gap,"RELH":self.label_height,"RELW":.20,"ANCHOR":"CENTER","TEXT":"Num Images Target: 0","FONT":self.text_font}
        tools.create_widgets_from_dict(dict_widgets, self.Frame_labels2, "HORIZONTAL", font = self.text_font, bgcolor = tools._bgcolor)
        self.cb_camera.config(textvariable=self.cb_camera_var)
        self.cb_camera.configure(state = 'readonly') # camera is chosen from the list, index of the selection gives the camera name
        self.cb_camera.bind('<<ComboboxSelected>>', self.on_camera_selected)

        self.Frame_source = tk.Frame(self.root)
        self.Frame_source.place(relx=.01, rely=0.05, relheight=0.75, relwidth=0.48)
        self.Frame_source.configure(relief='flat')
        self.Frame_source.configure(background=tools._bgcolor_dbg) if self.debug else True # uncomment for same colour as window (default) or depend on debug

        self.Frame_target = tk.Frame(self.root)
        self.Frame_target.place(relx=.51, rely=0.05, relheight=0.75, relwidth=0.48)
        self.Frame_target.configure(relief='flat')
        self.Frame_target.configure(background=tools._bgcolor_dbg) if self.debug else True # uncomment for same colour as window (default) or depend on debug

        self.Frame_source_ctl = tk.Frame(self.root)
        self.Frame_source_ctl.place(relx=.01, rely=0.82, relheight=0.05, relwidth=0.48)
        self.Frame_source_ctl.configure(relief='flat')
        self.Frame_source_ctl.configure(background=tools._bgcolor_dbg) if self.debug else True # uncomment for same colour as window (default) or depend on debug

        self.Frame_target_ctl = tk.Frame(self.root)
        self.Frame_target_ctl.place(relx=.51, rely=0.82, relheight=0.05, relwidth=0.48)
        self.Frame_target_ctl.configure(relief='flat')
        self.Frame_target_ctl.configure(background=tools._bgcolor_dbg) if self.debug else True # uncomment for same colour as window (default) or depend on debug
        
        # frames for listboxes
        # indir
        self.Frame_indir = tk.LabelFrame(self.root)
        self.Frame_indir.place(relx=.005, rely=0.87, relheight=0.12, relwidth=0.33)
        self.Frame_indir.configure(relief='groove')
        self.Frame_indir.configure(borderwidth="2")
        self.Frame_indir.configure(text = "indirs")
        self.Frame_indir.configure(background=tools._bgcolor_dbg) if self.debug else True # uncomment for same colour as window (default) or depend on debug
        self.Frame_indir.update()
        # subframes for listbox and buttons new / apply, checkbox recursive
        divide = .8
        self.Frame_indir_lb = tk.LabelFrame(self.Frame_indir)
        self.Frame_indir_lb.place(relx=.0, rely=0.0, relheight=1, relwidth=divide)
        self.Frame_indir_lb.configure(relief='groove')
        self.Frame_indir_lb.configure(borderwidth="2")
        self.Frame_indir_lb.configure(background=tools._bgcolor_dbg) if self.debug else True
        self.Frame_indir_lb.update()
        self.Frame_indir_misc = tk.LabelFrame(self.Frame_indir)
        self.Frame_indir_misc.place(relx=divide, rely=0.0, relheight=1, relwidth=1-divide)
        self.Frame_indir_misc.configure(relief='groove')
        self.Frame_indir_misc.configure(borderwidth="2")
        self.Frame_indir_misc.configure(background=tools._bgcolor_dbg) if self.debug else True
        self.Frame_indir_misc.update()
        # cfg
        self.Frame_cfg = tk.LabelFrame(self.root)
        self.Frame_cfg.place(relx=.33, rely=0.87, relheight=0.12, relwidth=0.33)
        self.Frame_cfg.configure(relief='groove')
        self.Frame_cfg.configure(borderwidth="2")
        self.Frame_cfg.configure(text = "cfg files")
        self.Frame_cfg.configure(background=tools._bgcolor_dbg) if self.debug else True
        self.Frame_cfg.update()
        # subframes for listbox and button
        divide = .8
        self.Frame_cfg_lb = tk.LabelFrame(self.Frame_cfg)
        self.Frame_cfg_lb.place(relx=.0, rely=0.0, relheight=1, relwidth=divide)
        self.Frame_cfg_lb.configure(relief='groove')
        self.Frame_cfg_lb.configure(borderwidth="2")
        self.Frame_cfg_lb.configure(background=tools._bgcolor_dbg) if self.debug else True
        self.Frame_cfg_lb.update()
        self.Frame_cfg_misc = tk.LabelFrame(self.Frame_cfg)
        self.Frame_cfg_misc.place(relx=divide, rely=0.0, relheight=1, relwidth=1-divide)
        self.Frame_cfg_misc.configure(relief='groove')
        self.Frame_cfg_misc.configure(borderwidth="2")
        self.Frame_cfg_misc.configure(background=tools._bgcolor_dbg) if self.debug else True
        self.Frame_cfg_misc.update()
        # outdir
        self.Frame_outdir = tk.LabelFrame(self.root)
        self.Frame_outdir.place(relx=.66, rely=0.87, relheight=0.12, relwidth=0.33)
        self.Frame_outdir.configure(relief='groove')
        self.Frame_outdir.configure(borderwidth="2")
        self.Frame_outdir.configure(text = "outdirs")
        self.Frame_outdir.configure(background=tools._bgcolor_dbg) if self.debug else True
        self.Frame_outdir.update()
        # subframes for listbox and button
        divide = .8
        self.Frame_outdir_lb = tk.LabelFrame(self.Frame_outdir)
        self.Frame_outdir_lb.place(relx=.0, rely=0.0, relheight=1, relwidth=divide)
        self.Frame_outdir_lb.configure(relief='groove')
        self.Frame_outdir_lb.configure(borderwidth="2")
        self.Frame_outdir_lb.configure(background=tools._bgcolor_dbg) if self.debug else True
        self.Frame_outdir_lb.update()
        self.Frame_outdir_misc = tk.LabelFrame(self.Frame_outdir)
        self.Frame_outdir_misc.place(relx=divide, rely=0.0, relheight=1, relwidth=1-divide)
        self.Frame_outdir_misc.configure(relief='groove')
        self.Frame_outdir_misc.configure(borderwidth="2")
        self.Frame_outdir_misc.configure(background=tools._bgcolor_dbg) if self.debug else True
        self.Frame_outdir_misc.update()
 
        # listbox for Indirs
        w = .75
        self.listbox_indir_var = tk.StringVar()
        self.listbox_indir = tk.Listbox(self.Frame_indir_lb)
        self.listbox_indir.configure(font=self.text_font)
        self.listbox_indir.configure(selectmode='single')
        self.listbox_indir.configure(listvariable=self.listbox_indir_var)
        self.listbox_indir.bind('<Motion>', self.tooltip_lb_indir)    
        # Scrollbars
        VI_INDIR = tk.Scrollbar(self.Frame_indir_lb, orient= VERTICAL)
        VI_INDIR.config(command = self.listbox_indir.yview)
        self.listbox_indir.config(yscrollcommand = VI_INDIR.set)
        HI_INDIR = tk.Scrollbar(self.Frame_indir_lb, orient= HORIZONTAL)
        HI_INDIR.config(command = self.listbox_indir.xview)
        tools.place_box_with_scrollbars(self, self.Frame_indir_lb, self.listbox_indir, HI_INDIR, VI_INDIR, .04, .0, .0, .0, .0)
        self.listbox_indir.config(xscrollcommand = HI_INDIR.set)
        self.listbox_indir.bind('<Double-1>', self.listbox_indir_double)
        self.listbox_indir.bind("<<ListboxSelect>>", lambda event: self.listbox_indir_check_exist(event))
        # Buttons and checkbox
        #set some defaults
        relw_button = 0.95
        relh_button = 0.95
        relw_entry = 0.8
        relh_entry = 0.8
        relw_label = 0.8
        relh_label = 0.8
        offset_entry = .01
        dict_widgets = {}
        dict_widgets["1"] = {
          "WIDGET":tk.Button,"VAR":"button_apply_indir","OFFSET":0.00,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"CENTER",
          "CALLBACK":self.listbox_indir_double,"TEXT":"Apply selected","STATE":tk.NORMAL,"TT":"Apply Indir selected","FONT":self.text_font}
        dict_widgets["2"] = {
          "WIDGET":tk.Button,"VAR":"button_new_indir","OFFSET":0.00,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"CENTER",
          "CALLBACK":self.new_indir,"TEXT":"New...","STATE":tk.NORMAL,"TT":"SELECT NEW Indir from Fileopen Dialog","FONT":self.text_font}
        dict_widgets["3"] = {
          "WIDGET":tk.Checkbutton,"VAR":"cb_recursive","OFFSET":0.1,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"START",
          "RB_VAR":"cb_recursive_var","RB_TYPE":tk.IntVar,"RB_VALUE":"1","TEXT":"recursive","STATE":tk.NORMAL,"TT":"include all subdirs(recursive)","FONT":self.text_font}
        tools.create_widgets_from_dict(dict_widgets, self.Frame_indir_misc, "VERTICAL", font = self.text_font, bgcolor = tools._bgcolor)

        self.cb_recursive_var.set(1)

        # listbox for config files
        self.listbox_cfg_var = tk.StringVar()
        self.listbox_cfg = tk.Listbox(self.Frame_cfg_lb)
        self.listbox_cfg.configure(font=self.text_font)
        self.listbox_cfg.configure(selectmode='single')
        self.listbox_cfg.configure(listvariable=self.listbox_cfg_var)
        self.listbox_cfg.bind('<Motion>', self.tooltip_lb_cfg)    
        # Scrollbars
        VI_CFG = tk.Scrollbar(self.Frame_cfg_lb, orient= VERTICAL)
        VI_CFG.config(command = self.listbox_cfg.yview)
        self.listbox_cfg.config(yscrollcommand = VI_CFG.set)
        HI_CFG = tk.Scrollbar(self.Frame_cfg_lb, orient= HORIZONTAL)
        HI_CFG.config(command = self.listbox_cfg.xview)
        tools.place_box_with_scrollbars(self, self.Frame_cfg_lb, self.listbox_cfg, HI_CFG, VI_CFG, .04, .0, .0, .0, .0)
        self.listbox_cfg.config(xscrollcommand = HI_CFG.set)
        self.listbox_cfg.bind('<Double-1>', self.listbox_cfg_double)
        self.listbox_cfg.bind("<<ListboxSelect>>", lambda event: self.listbox_cfg_check_exist(event))
        # Button
        self.button_apply_cfg = tk.Button(self.Frame_cfg_misc, text="Apply selected", command=self.listbox_cfg_double)
        self.button_apply_cfg.place(relx=.0, rely=0.0, relheight=0.3, relwidth=1)
        self.button_apply_cfg.configure(font=self.text_font)

        # listbox for outdirs
        self.listbox_outdir_var = tk.StringVar()
        self.listbox_outdir = tk.Listbox(self.Frame_outdir_lb)
        self.listbox_outdir.configure(font=self.text_font)
        self.listbox_outdir.configure(selectmode='single')
        self.listbox_outdir.configure(listvariable=self.listbox_outdir_var)
        self.listbox_outdir.bind('<Motion>', self.tooltip_lb_outdir)    
        # Scrollbars
        VI_OUTDIR = tk.Scrollbar(self.Frame_outdir_lb, orient= VERTICAL)
        VI_OUTDIR.config(command = self.listbox_outdir.yview)
        self.listbox_outdir.config(yscrollcommand = VI_OUTDIR.set)
        HI_OUTDIR = tk.Scrollbar(self.Frame_outdir_lb, orient= HORIZONTAL)
        HI_OUTDIR.config(command = self.listbox_outdir.xview)
        tools.place_box_with_scrollbars(self, self.Frame_outdir_lb, self.listbox_outdir, HI_OUTDIR, VI_OUTDIR, .04, .0, .0, .0, .0)
        self.listbox_outdir.config(xscrollcommand = HI_OUTDIR.set)
        self.listbox_outdir.bind("<<ListboxSelect>>", lambda event: self.listbox_outdir_check_exist(event))
        # Button
        self.button_apply_outdir = tk.Button(self.Frame_outdir_misc, text="New...", command=self.new_outdir)
        self.button_apply_outdir.place(relx=0, rely=0.0, relheight=.3, relwidth=1)
        self.button_apply_outdir.configure(font=self.text_font)


        # canvas source with scrollbars
        self.source_canvas = ScrollableCanvas(self.Frame_source, bg="yellow")
        self.source_canvas.place(relx=0.0, rely=0.0, relheight=.98, relwidth=.98)

        self.V_source = tk.Scrollbar(self.Frame_source, orient = tk.VERTICAL)
        self.V_source.config(command=self.source_canvas.yview)
        self.source_canvas.config(yscrollcommand=self.V_source.set)
        self.V_source.place(relx = 1, rely = 0,     relheight = 0.98, relwidth = 0.02, anchor = tk.NE)        

        self.H_source = tk.Scrollbar(self.Frame_source, orient = tk.HORIZONTAL)
        self.H_source.config(command=self.source_canvas.xview)
        self.source_canvas.config(xscrollcommand=self.H_source.set)
        self.H_source.place(relx = 0, rely = 1, relheight = 0.02, relwidth = 0.98, anchor = tk.SW)

        self.source_canvas.bind("<Left>",  lambda event: self.source_canvas.xview(tk.SCROLL, -1, "unit"))
        self.source_canvas.bind("<Right>", lambda event: self.source_canvas.xview(tk.SCROLL,  1, "unit"))
        self.source_canvas.bind("<Up>",    lambda event: self.source_canvas.yview(tk.SCROLL, -1, "unit"))
        self.source_canvas.bind("<Down>",  lambda event: self.source_canvas.yview(tk.SCROLL,  1, "unit"))
 
        # canvas target with scrollbars
        self.target_canvas = ScrollableCanvas(self.Frame_target, bg="darkgrey")
        self.target_canvas.place(relx=0.0, rely=0.0, relheight=.98, relwidth=.98)
        self.target_canvas.config(xscrollincrement = 10)

        self.V_target = tk.Scrollbar(self.Frame_target, orient = tk.VERTICAL)
        self.V_target.config(command=self.target_canvas.yview)
        self.target_canvas.config(yscrollcommand=self.V_target.set)  
        self.V_target.place(relx = 1, rely = 0,     relheight = 0.98, relwidth = 0.02, anchor = tk.NE)        

        self.H_target = tk.Scrollbar(self.Frame_target, orient = tk.HORIZONTAL)
        self.H_target.config(command=self.target_canvas.xview)
        self.target_canvas.config(xscrollcommand=self.H_target.set)
        self.H_target.place(relx = 0, rely = 1, relheight = 0.02, relwidth = 0.98, anchor = tk.SW)
        
        self.target_canvas.bind("<Left>",  lambda event: self.target_canvas.xview(tk.SCROLL, -1, "unit"))
        self.target_canvas.bind("<Right>", lambda event: self.target_canvas.xview(tk.SCROLL,  1, "unit"))
        self.target_canvas.bind("<Up>",    lambda event: self.target_canvas.yview(tk.SCROLL, -1, "unit"))
        self.target_canvas.bind("<Down>",  lambda event: self.target_canvas.yview(tk.SCROLL,  1, "unit"))
 
        # source control buttons
        anz_button_source = 5
        buttonpos_source  = 0.0
        relwidth_source   = 1 / anz_button_source
        self.select_all_button = tk.Button(self.Frame_source_ctl, text="Select all", command=self.select_all_source_images)
        self.select_all_button.place(relx=buttonpos_source, rely=0.01, relheight=0.98, relwidth=relwidth_source)
        buttonpos_source += relwidth_source
        self.copy_selected_button = tk.Button(self.Frame_source_ctl, text="Copy selected", command=self.copy_selected_source_images)
        self.copy_selected_button.place(relx=buttonpos_source, rely=0.01, relheight=0.98, relwidth=relwidth_source)
        buttonpos_source += relwidth_source
        self.copy_head_button = tk.Button(self.Frame_source_ctl, text="Copy Head", command=self.copy_selected_source_images_head)
        self.copy_head_button.place(relx=buttonpos_source, rely=0.01, relheight=0.98, relwidth=relwidth_source)
        buttonpos_source += relwidth_source
        self.copy_tail_button = tk.Button(self.Frame_source_ctl, text="Copy Tail", command=self.copy_selected_source_images_tail)
        self.copy_tail_button.place(relx=buttonpos_source, rely=0.01, relheight=0.98, relwidth=relwidth_source)

        # target control buttons
        anz_button_target = 5
        buttonpos_target  = 0.0
        relwidth_target   = 1 / anz_button_source
        self.delete_selected_button = tk.Button(self.Frame_target_ctl, text="Delete selected", command=self.delete_selected)
        self.delete_selected_button.place(relx=buttonpos_target, rely=0.01, relheight=0.98, relwidth=relwidth_target)
        buttonpos_target += relwidth_target
        self.button_undo = tk.Button(self.Frame_target_ctl, text="Undo", command=self.button_undo_h)
        self.button_undo.place(relx=buttonpos_target, rely=0.01, relheight=0.98, relwidth=relwidth_target)
        buttonpos_target += relwidth_target
        self.button_redo = tk.Button(self.Frame_target_ctl, text="Redo", command=self.button_redo_h)
        self.button_redo.place(relx=buttonpos_target, rely=0.01, relheight=0.98, relwidth=relwidth_target)
        buttonpos_target += relwidth_target
        self.button_processlist = tk.Button(self.Frame_target_ctl, text="Process List", command=self.button_processlist_pressed)
        self.button_processlist.place(relx=buttonpos_target, rely=0.01, relheight=0.98, relwidth=relwidth_target)
        buttonpos_target += relwidth_target
        self.button_exec = tk.Button(self.Frame_target_ctl, text="Exec", command=self.button_exec_pressed)
        self.button_exec.place(relx=buttonpos_target, rely=0.01, relheight=0.98, relwidth=relwidth_target)

        self.button_undo.config(state = tk.DISABLED)
        self.button_redo.config(state = tk.DISABLED)
        self.button_exec.config(state = tk.DISABLED)
        self.root.bind('<Control-z>', lambda event: self.process_undo(event))
        self.root.bind('<Control-y>', lambda event: self.process_redo(event))


        self.source_row, self.source_col = 0, 0
        self.target_row, self.target_col = 0, 0
        self.drag_started_in = ""

        #self.source_canvas.bind("<ButtonPress-1>", self.start_drag)
        #self.target_canvas.bind("<ButtonRelease-1>", self.drop)
        self.target_canvas.bind("<B1-Motion>", self.on_motion)
        self.root.bind("<ButtonPress-1>", self.start_drag)
        self.root.bind("<ButtonRelease-1>", self.drop)
        
        # bind double click to show FSImage
        self.source_canvas.bind("<Double-Button-1>", self.canvas_image_source_show)
        self.target_canvas.bind("<Double-Button-1>", self.canvas_image_target_show)


        # tooltips, context-menu
        self.tooltiptext_st = ""
        self.tooltiptext_tt = ""
        self.source_canvas.bind("<Button-3>", self.show_context_menu_source) 
        self.source_canvas.bind('<Motion>', self.tooltip_imagefile_source)    
        self.target_canvas.bind("<Button-3>", self.show_context_menu_target) 
        self.target_canvas.bind('<Motion>', self.tooltip_imagefile_target)    
        #self.target_canvas.bind('<Motion>', lambda event, i = self.target_canvas, j = self.dict_target_images, k = "target": self.tooltip_imagefile(event, i, j, k))    
        self.st = TT.ToolTip(self.source_canvas, "no images available", delay=0, follow = True)
        self.tt = TT.ToolTip(self.target_canvas, "no images available", delay=0, follow = True)
        self.tooltiptext_lb_indir = ""
        self.tt_lb_indir = TT.ToolTip(self.listbox_indir, "no item available", delay=0, follow = True)
        self.tooltiptext_lb_cfg = ""
        self.tt_lb_cfg = TT.ToolTip(self.listbox_cfg, "no item available", delay=0, follow = True)
        self.tooltiptext_lb_outdir = ""
        self.tt_lb_outdir = TT.ToolTip(self.listbox_outdir, "no item available", delay=0, follow = True)

        # temporary storage of dragged images while dragging
        self.list_dragged_images = []

        # dict and list of source / target images, to be historized
        self.dict_source_images = {} # ID -> MyImage
        self.dict_target_images = {} # ID -> MyImage
        self.list_source_images = []
        self.list_target_images = []
        self.dict_file_FSImage_source = {}
        self.dict_file_FSImage_target = {}
        self.list_result = list_result  # reference given from caller
        self.callback = None
        if callback:
            self.callback = callback
        
        # Undo /Redo control
        self.UR = UR.Undo_Redo_Diatisch(self.debug_p)
        self.dict_processid_histobj = {} # key processid to be applied value: histobj
        # Undo /Redo control end

        self.event_source = None
        self.event_target = None

        # Create the context menues
        self.context_menu_source = tk.Menu(self.source_canvas, tearoff=0)
        self.context_menu_source.add_command(label="Show"   , command=self.canvas_image_source_event)    
        self.context_menu_source.add_command(label="Copy Selected"   , command=self.copy_selected_source_images)    
        self.context_menu_source.add_command(label="Copy "   , command=self.copy_single_source_image)    
        self.context_menu_source.add_command(label="Print", command=self.print_image_under_menu)
        self.context_menu_target = tk.Menu(self.target_canvas, tearoff=0)
        self.context_menu_target.add_command(label="Show"   , command=self.canvas_image_target_event)  
        self.context_menu_target.add_command(label="Delete Selected"   , command=self.delete_selected_target_images)    
        self.context_menu_target.add_command(label="Delete "   , command=self.delete_single_target_image)    

        self.context_menu_target.add_command(label="Print", command=self.print_image_under_menu)

        self.default_indir  = ""
        self.datadir = ""
        self.config_files_xml = ""
        self.config_files_subdir = ""
        self.cmd_files_subdir    = ""
        self.config_file = ""
        self.ctr_targetfiles = 0
        self.indir = ""
        self.win_exec = None
        self.win_processlist = None
        self.imagetype  = "JPEG"
        self.imagetypes = "JPG, JPEG"
        self.dict_gen_files = {}
        self.dict_gen_files_delete = {}
        self.dict_gen_files_delrelpath = {}
        self.dict_gen_files[self.imagetype] = {}
        self.dict_gen_files_delete[self.imagetype] = {}
        self.dict_gen_files_delrelpath[self.imagetype] = {}
        self.dict_templates = {}
        self.outdir = None
        self.scroll = False
        self.delay = 1000
        self.canvas_to_scroll = None
        self.scrolltype = ''

        self.timestamp1 = datetime.now() 
        self.timestamp2 = datetime.now() 
        self.timestamp3 = datetime.now() 
        self.timestamp4 = datetime.now() 
        self.timestamp5 = datetime.now() 
        self.timestamp_scroll = datetime.now() 
        self.image_press = None
        self.image_release = None
        
        self.root.protocol("WM_DELETE_WINDOW", self.close_handler)
        
        # the following two change attributes are for a transaction of press / release. 
        # They are set to false in start_drag, changed in selection() and used in drop to decide about rebuild canvas and historization
        self.canvas_target_rebuild_required = False
        self.selection_changed = False
        self.dist_frame = 20 # distance of dotted select frame from border in Pixels
        self.single_image_to_copy   = None # name of single image selected by menuitem to copy from source to target
        self.single_image_to_delete = None # name of single image selected by menuitem to delete from target
        self.image_files = []
        self.dict_file_FSImage_source = {} # dict for keeping track of FS Images
        self.dict_file_FSImage_target = {} # dict for keeping track of FS Images
        self.sort_method = 0
        # print
        self.printer = None
        self.preview = None
        self.image_to_print = None # image under the context menu
        # camera data of the currently selected camera (see load_camera_data)
        self.camera = ""
        self.camera_names = []        # names parallel to the values of the combobox
        self.dict_cameras = {}        # TYPE -> "SUF1, SUF2" (only types / suffixes which Diatisch can show)
        self.dict_process_image = {}  # SUFFIX -> process type (JPEG, USE_JPEG, RAW)
        self.dict_suffix_type = {}    # SUFFIX -> TYPE
        self.dict_firstname_fullname = {} # (folder, firstname) -> companion JPEG for RAW / USE_JPEG
        self.loaded_dir = None        # directory of the last load (None if loaded from lists), needed for reload on camera change

        # automatic font fit for all text widgets (central helper: tools.FontFitter)
        self.font_fitter = tools.FontFitter(
            self.text_font,
            class_params={
                "Label": {
                    "pad_x": 2,
                    "min_size": 6
                },
                "Button": {
                    "pad_x": 2,
                    "min_size": 6 
                },
                "ttk.Combobox": {
                    "pad_x": 2,
                    "min_size": 9
                }
            }
        )
        #self.font_fitter.exclude.update({self.lb_camera, self.lb_gen}) # exclude widgets from automatic resize

        self.root.bind("<Configure>", self.on_configure)
        self.root.after(0, self.resize) # force window height / width to work and call initial resize for fonts
        self.init()
        # historize initial state
        self.historize_process("initial")
        self.processid_displayed = self.UR.get_processid_akt() # used for keep track of predecessor of processid to be displayed from selection in procell_list, initialized to actual processid

    def init(self):
        self.read_ini()

        # initialize the event handler which we use for communication between windows (include / exclude) if not exist
        if not Globals.eventManager:
            Globals.eventManager = tools.EventManager()
        # zentrale Drucklogik: nimmt PrintRequestEvent von überall entgegen
        Globals.eventManager.bind("PrintRequestEvent", self.handle_print_request)
        # if camera changed we should know
        Globals.eventManager.bind("CameraChangedEvent", self.handle_camera_changed)        
        
        self.update_combobox_camera()

        # Menubar
        self.menubar = tk.Menu(self.root)
        self.root.configure(menu = self.menubar)

        # The file menu
        self.filemenu = tk.Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label="New Indir", command=self.new_indir)
        self.filemenu.add_command(label="New Outdir", command=self.new_outdir)
        self.filemenu.add_command(label="Open", command=self.load_images)
        self.filemenu.add_command(label="Close", command=self.close_indir)
        # printing, same as in Dateimeister_support
        self.filemenu.add_separator()
        self.filemenu.add_command(label=MENU_LABEL_CHOOSE_PRINTER, command=self.choose_printer)
        self.filemenu.add_command(label=MENU_LABEL_PRINT, command=self.print_selected, state=DISABLED)
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Exit", command=self.root.quit)
        self.menubar.add_cascade(label="File", menu=self.filemenu)
        self.recentmenu_file = tk.Menu(self.menubar, tearoff=0)
        self.filemenu.add_cascade(label="Open Recent", menu=self.recentmenu_file)

        # The config Menu
        self.configmenu = tk.Menu(self.menubar, tearoff=0)
        self.configmenu.add_command(label="New", command=self.donothing)
        self.configmenu.add_command(label="Open config", command=self.open_config)
        self.configmenu.add_command(label="Open and apply config", command=self.open_apply_config)
        self.configmenu.add_command(label="Save config", command=self.save_config)
        self.configmenu.add_command(label="Save config as...", command=self.saveas_config)
        self.configmenu.add_command(label="Apply config", command=self.apply_config)
        self.menubar.add_cascade(label="Config", menu=self.configmenu)
        self.recentmenu_cfg = tk.Menu(self.menubar, tearoff=0)
        self.configmenu.add_cascade(label="Open Recent", menu=self.recentmenu_cfg)

        # the tools menu
        self.toolsmenu = tk.Menu(self.menubar, tearoff=0)
        self.toolsmenu.add_command(label="Edit Cameras...", command = self.cameras_edit)
        self.menubar.add_cascade(label="Tools", menu=self.toolsmenu)

        # the help menu
        self.helpmenu = tk.Menu(self.menubar, tearoff=0)
        self.helpmenu.add_command(label="Help Index", command=self.donothing)
        self.helpmenu.add_command(label="About...", command=self.donothing)
        self.menubar.add_cascade(label="Help", menu=self.helpmenu)

        self.endis_menu_items()
        self.update_listbox_cfg()
        self.update_listbox_indir()
        self.update_listbox_outdir()
        
        #DX.delete_diatisch_item(self.config_files_xml, "indirs", "indir", "name", "e:/fotos/dateimeister")
        
        # read the templates and build names for genfiles
        self.dict_templates = {}
        self.dict_gen_filenames = {}
        try:
            file = open(self.templatefile)
        except FileNotFoundError:
            print("File does not exist: " + self.templatefile)
        templates = file.read().replace('\n', '<<<NL>>>')
        #print(templates)
        regpattern = r'\[([^\]]+)\](.*?)\[/\1\]'
        list_t = re.findall(regpattern, templates)
        for ii in list_t:
            templatename = ii[0].upper()
            file_prefix  = ii[0].lower()
            template     = ii[1]
            #print("templatename: " + templatename)
            #print(template)
            self.dict_templates[templatename] = template
            
            # the associated genfile
            fn = '_' + file_prefix + '_' + self.imagetype + '_diatisch.cmd'
            cmd_file_name = os.path.join(self.datadir, self.cmd_files_subdir, fn) # include path
            self.dict_gen_filenames[templatename] = cmd_file_name
        
        templates = re.sub(r'<<<NL>>>', '\n', templates)
        #print(templates)

        if self.list_imagefiles:
            self.load_images(None, self.list_imagefiles)

    def update_combobox_camera(self, keep_camera = None):
        # fill the camera combobox, newest camera (usedate) first. If keep_camera is given and still exists it stays selected.
        # Also (re)loads the camera data (types, suffixes, process types) of the selected camera.
        dict_cameras = DX.get_cameras_types_suffixes(self.config_files_xml)
        dict_usedate = DX.get_cameras_usedate(self.config_files_xml)
        dict_pi_all  = DX.get_process_image_per_camera(self.config_files_xml)
        entries = []
        for camera, d1 in dict_cameras.items():
            st = camera
            for cam_type, suffixes in d1.items():
                pi = dict_pi_all.get(camera, {}).get(cam_type, {})
                st += f" {cam_type}("
                st += ",".join(f" {s}:{pi.get(s.upper(), '?')}" for s in suffixes)
                st += ")"
            entries.append({"camera": camera, "usedate": dict_usedate.get(camera, ""), "display": st})
        entries.sort(key = lambda e: e["usedate"], reverse = True)

        self.camera_names = [e["camera"] for e in entries]
        list_cam = [e["display"] for e in entries]
        self.cb_camera.configure(values = list_cam)
        idx = 0
        if keep_camera and keep_camera.upper() in self.camera_names:
            idx = self.camera_names.index(keep_camera.upper())
        if list_cam:
            self.cb_camera.current(idx)
            self.cb_camera_var.set(list_cam[idx])
            self.load_camera_data(self.camera_names[idx])
        else:
            self.cb_camera_var.set("")
            self.load_camera_data("")
        if self.debug:
            print("Sortierte Kameraliste:")
            for e in entries:
                print(f"{e['usedate']}  {e['camera']}  {e['display']}")

    def get_current_camera(self):
        # name of the camera selected in the combobox ("" if none)
        idx = self.cb_camera.current()
        if 0 <= idx < len(self.camera_names):
            return self.camera_names[idx]
        return ""

    def load_camera_data(self, camera):
        # build the per-camera dicts. Only suffixes whose process type is allowed by proc_types in the ini (and is not VIDEO)
        # are used, because Diatisch shows still images.
        self.camera = camera
        self.dict_cameras = {}
        self.dict_process_image = {}
        self.dict_suffix_type = {}
        allowed = {p.strip().upper() for p in self.proctypes.split(",") if p.strip()} - {"VIDEO"}
        if camera:
            cam_key = camera.upper()
            dict_types = DX.get_cameras_types_suffixes(self.config_files_xml).get(cam_key, {})
            pi = DX.get_process_image_per_camera(self.config_files_xml).get(cam_key, {})
            for type_name, suffixes in dict_types.items():
                usable = []
                for s in suffixes:
                    s = s.strip()
                    process = pi.get(type_name, {}).get(s.upper(), "")
                    if s and process in allowed:
                        usable.append(s)
                        self.dict_process_image[s.upper()] = process
                        self.dict_suffix_type[s.upper()] = type_name
                    else:
                        print(f"camera {camera} type {type_name} suffix {s}: process type '{process}' not usable in Diatisch, skipped") if self.debug else True
                if usable:
                    self.dict_cameras[type_name] = ", ".join(usable)
        if not self.dict_cameras: # no camera or no usable type: behave like before (JPEG only)
            print("Diatisch: no usable camera types, using default JPEG: JPG, JPEG")
            self.dict_cameras["JPEG"] = "JPG, JPEG"
            for s in ("JPG", "JPEG"):
                self.dict_process_image[s] = PROCESS_JPEG
                self.dict_suffix_type[s]   = "JPEG"
        print(f"Diatisch camera {camera}: types {self.dict_cameras}") if self.debug else True

    def process_type_of(self, filename):
        # process type (JPEG, USE_JPEG, RAW) of a file according to its suffix, "" if unknown
        ext = os.path.splitext(filename)[1].lstrip(".").upper()
        return self.dict_process_image.get(ext, "")

    def type_of(self, filename):
        ext = os.path.splitext(filename)[1].lstrip(".").upper()
        return self.dict_suffix_type.get(ext, "")

    def on_camera_selected(self, event = None):
        # user picked another camera in the combobox
        camera = self.get_current_camera()
        if not camera or camera.upper() == self.camera.upper():
            return
        ts = strftime("%Y%m%d-%H:%M:%S", time.localtime())
        try:
            DX.update_camera_usedate(self.config_files_xml, camera, ts) # so it is the preselected one next time
        except Exception as e:
            print(f"cannot update usedate of camera {camera}: {e}")
        self.load_camera_data(camera)
        self.reload_after_camera_change()

    def reload_after_camera_change(self):
        # rebuild the source images with the types / suffixes of the current camera. Target images which are still
        # visible in the new source list are kept (in their order), the others are dropped. Undo brings everything back.
        keep = [i.get_filename() for i in self.list_target_images]
        if self.loaded_dir:
            self.load_images(self.loaded_dir, None, None, keep)
        elif self.list_source_images:
            sources = [i.get_filename() for i in self.list_source_images]
            self.load_images(None, sources, None, keep)

    # --- companion JPEG and thumbnails -----------------------------------------------------------------------------------
    @staticmethod
    def _companion_key(path):
        return (os.path.normcase(os.path.normpath(os.path.dirname(path))), os.path.splitext(os.path.basename(path))[0].lower())

    def _collect_companions(self, files):
        # remember the JPEGs by (folder, firstname), so RAW / USE_JPEG files find the JPEG with the same name
        self.dict_firstname_fullname = {}
        for f in files:
            if self.process_type_of(f) == PROCESS_JPEG:
                self.dict_firstname_fullname[self._companion_key(f)] = f # more than one: the last one counts

    def _companion(self, file):
        c = self.dict_firstname_fullname.get(self._companion_key(file))
        if c and os.path.normcase(c) != os.path.normcase(file):
            return c
        base = os.path.splitext(file)[0] # e.g. file list from Dateimeister: look into the folder
        for suffix, process in self.dict_process_image.items():
            if process == PROCESS_JPEG:
                for s in (suffix.lower(), suffix):
                    cand = base + "." + s
                    if tools.isfile_fast(cand):   # network share: short test, no long timeout
                        return cand
        return None

    def get_showfile(self, file):
        # file which the detail window (FSImage) shows: companion JPEG for USE_JPEG, otherwise the file itself
        if self.process_type_of(file) == PROCESS_USE_JPEG:
            return self._companion(file) or file
        return file

    def _load_raw_pil(self, filename):
        # embedded JPEG of a RAW file as PIL image, None if not possible
        try:
            import rawpy_loader
            pil, w, h = rawpy_loader.load_raw_thumbnail(filename, height = self.row_height)
            return pil
        except Exception as e:
            print(f"RAW not displayable: {filename} ({type(e).__name__}: {e})") if self.debug else True
            return None

    def _placeholder_image(self, label):
        img = Image.new("RGB", (int(self.row_height * 1.5), self.row_height), "#2f4f8f")
        ImageDraw.Draw(img).text((10, 10), label or "?", fill = "white")
        return img

    def make_photo(self, filename, canvas):
        # thumbnail for a file depending on its process type. RAW: embedded JPEG, otherwise companion JPEG,
        # otherwise (and for unreadable files) a blue rectangle, so that the file stays visible and selectable.
        ptype = self.process_type_of(filename)
        pil = None
        try:
            if ptype == PROCESS_RAW:
                pil = self._load_raw_pil(filename)
                if pil is None:
                    comp = self._companion(filename)
                    if comp:
                        pil = Image.open(comp)
            elif ptype == PROCESS_USE_JPEG:
                comp = self._companion(filename)
                if comp:
                    pil = Image.open(comp)
            else: # JPEG or unknown suffix (e.g. from config file): try as normal image
                pil = Image.open(filename)
            if pil is not None:
                w, h = pil.size
                faktor = min(self.row_height / h, self.image_width / w)
                pil.thumbnail((int(w * faktor), int(h * faktor)))
        except Exception as e:
            print(f"Image not readable: {filename} ({type(e).__name__}: {e})")
            pil = None
        if pil is None:
            pil = self._placeholder_image(ptype or "?")
        return ImageTk.PhotoImage(pil, master = canvas)

    def create_fsimage(self, canvas_type, img, file):
        # detail window for source or target image. file = original filename (key in dict_file_FSImage_*)
        showfile = self.get_showfile(file)
        if canvas_type == "Source":
            canvas, prefix, text = self.source_canvas, "Source: ", "Copy"
        else:
            canvas, prefix, text = self.target_canvas, "Target: ", "Delete"
        thumbnail = Thumbnail(img, file, None, canvas, self.debug, canvas_type, self.fs_close, self.fs_button,
                              process_type = self.process_type_of(file), showfile = showfile)
        # read metadata once, so MyFSImage always has something to show
        try:
            thumbnail.set_metadata()
        except Exception as e:
            print(f"create_fsimage: set_metadata failed for {file}: {type(e).__name__}: {e}") if self.debug else True
        return FS.MyFSImage(
            file = showfile,
            thumbnail = thumbnail,
            caller = self,
            str_title_prefix = prefix,
            str_include = text,
            str_exclude = text,
            str_included = "",
            str_excluded = "",
            debug = self.debug
        )

    def xupdate_combobox_camera(self):
       # update the camera combobox
        dict_t, dict_s, dict_pi = DX.get_camera_xml(self.config_files_xml, debug = self.debug)
        print (f"dict_t is {dict_t}") if self.debug else True
        print (f"dict_s is {dict_s}") if self.debug else True
        print (f"dict_pi is {dict_pi}") if self.debug else True
        dict_cameras_usedate = DX.get_cameras_usedate(self.config_files_xml)
        list_cam = []
        for camera in dict_t:
            st = camera
            d1 = dict_t[camera]
            for type in d1:
                st += ' ' + type + '('
                suffixes = dict_t[camera][type]
                suffix_list = [x.strip() for x in suffixes.split(",")]
                i = 0
                for p in suffix_list:
                    i += 1
                    st += ' ' + p + ':' + dict_pi[p]
                    if i < len(suffix_list):
                        st += ','
                st += ')'    
            print(f"ST is {st}")
            
            list_cam.append(st)
        self.cb_camera.config(values = list_cam)    
        camera, cam_key = DX.get_recent_camera(self.config_files_xml, debug = self.debug)
        self.cb_camera_var.set(cam_key)

    # --- printing (same as in Dateimeister_support) -----------------------------------------------------------------------
    def choose_printer(self):
        ret = print_utils.choose_printer(self.root)
        print(f"Printer selected is {ret}") if self.debug else True
        self.printer = ret

    def _is_own_print_source(self, source):
        # Dateimeister and Diatisch share the event manager. Only handle requests from our own windows.
        if source is self:
            return True
        for d in (self.dict_file_FSImage_source, self.dict_file_FSImage_target):
            for v in d.values():
                if v is source:
                    return True
        return getattr(source, "caller", None) is self or getattr(source, "main", None) is self

    def handle_print_request(self, event):
        # central print logic: takes PrintRequestEvent from FSImage or from our own context menu,
        # creates / reuses the one PrintPreview and calls add_photo(filename).
        filename = event.filename
        print(f"Print request: file={filename} source={event.source}") if self.debug else True
        if not self._is_own_print_source(event.source):
            return
        if self.preview is None or not self._is_preview_window_alive(self.preview):
            self.preview = PrintPreview(
                self.root,
                rows = 3,
                preview_dir = Globals.temp_files_path,
                printer = self.printer,
                close_callback = self.preview_closed
            )
        self.preview.add_photo(filename)
        self.preview.bring_to_front()
        self.filemenu.entryconfig(MENU_LABEL_PRINT, state = NORMAL)

    @staticmethod
    def _is_preview_window_alive(preview):
        try:
            return bool(preview.window.winfo_exists())
        except tk.TclError:
            return False

    def preview_closed(self):
        # callback called by PrintPreview when it is closed
        print("PRINT Preview closed") if self.debug else True
        self.preview = None
        self.filemenu.entryconfig(MENU_LABEL_PRINT, state = DISABLED)

    def print_selected(self):
        # file menu 'Print selected': forward to the visible PrintPreview
        if self.preview is None or not self._is_preview_window_alive(self.preview):
            return
        self.preview.print_selected()

    def print_image_under_menu(self):
        # context menu 'Print' of source / target canvas
        if self.image_to_print is not None:
            self.print_image(self.image_to_print)

    def print_image(self, img):
        filename = img.get_filename()
        ptype = self.process_type_of(filename)
        printfile = filename
        if ptype == PROCESS_RAW:
            # embedded JPEG in original size as temporary PNG; fallback: companion JPEG
            pil = None
            try:
                import rawpy_loader
                pil = rawpy_loader.load_raw_embedded(filename)
            except Exception as e:
                print(f"RAW not loadable: {filename} ({type(e).__name__}: {e})")
            if pil is not None:
                import uuid
                os.makedirs(Globals.temp_files_path, exist_ok = True)
                printfile = os.path.join(Globals.temp_files_path, f"print_{uuid.uuid4().hex}.png")
                pil.save(printfile, format = "PNG")
            else:
                printfile = self._companion(filename)
                if not printfile:
                    tools.info_box(f"RAW konnte nicht geladen werden: {filename}", "fehler")
                    return
        elif ptype == PROCESS_USE_JPEG:
            printfile = self._companion(filename)
            if not printfile:
                tools.info_box(f"Kein Begleit-JPEG gefunden: {filename}", "fehler")
                return
        Globals.eventManager.generate("PrintRequestEvent", PrintRequestEvent(printfile, self))

    # --- camera changed ---------------------------------------------------------------------------------------------------
    def handle_camera_changed(self, event):
        # called when Dateimeister_camera fires the event that a camera has been changed
        print(f"camera changed event received for camera: {event.camera}") if self.debug else True
        try:
            if not self.root.winfo_exists():
                return
        except tk.TclError:
            return
        old = self.camera
        # cameras / types / suffixes may have changed: rebuild combobox and camera data, keep our camera if it still exists
        self.update_combobox_camera(keep_camera = old)
        if self.camera.upper() == (event.camera or "").upper() or self.camera.upper() != old.upper():
            print(f"camera {self.camera} changed, reload required") if self.debug else True
            self.reload_after_camera_change()

    def read_ini(self):
        inifile = "Diatisch.ini" 
        # Properties
        # we let ini_validator.py do te work
        from diatisch_ini_properties import dict_ini_spec # contains all the properties
        # we create the attributes in 'self' except those which have a "target" (Globals) in the line. the attributes are also generated in cfg
        # diatisch only needs attributes in self, so the parameter for the target_registry is set to None
        cfg, has_errors, has_warnings, problems = load_and_validate_ini(inifile, spec = dict_ini_spec, target = self, target_registry={"Globals": tools.Globals})
        print("Ini-Datei ist vollständig und gültig.")
        print("Beispiel: config_files_xml =", self.config_files_xml, type(self.config_files_xml), self.uncomment)
        
        # some operations on selected properties
        self.platform = self.platform.upper()
        self.uncomment += " "
        if self.platform != "UNIX" and self.platform != "WINDOWS":
            messagebox.showerror("INIT", "Platform must be Windows or Unix, not " + self.platform)
            exit()
        # datadir / config_files_subdir are also needed in Globals (camera treeview). A key can only appear once in
        # dict_ini_spec, so the attribute in self may be missing -> fall back to the Globals value
        if not self.datadir:
            self.datadir = getattr(Globals, "datadir", "") or ""
        if not self.config_files_subdir:
            self.config_files_subdir = getattr(Globals, "config_files_subdir", "") or ""
        # temp dir for print previews (RAW -> PNG, PrintPreview)
        temp_subdir = getattr(Globals, "temp_files_subdir", None) or "daten/temp"
        Globals.temp_files_path = os.path.join(self.datadir, temp_subdir)
        try:
            os.makedirs(Globals.temp_files_path, exist_ok = True)
        except OSError as e:
            print(f"cannot create temp dir {Globals.temp_files_path}: {e}")
        # end properties

    def close_child_windows(self): #closes fs-images    
        # cleanup
        # delete all fsimage by close-call
        for t in self.dict_file_FSImage_source:
            u = self.dict_file_FSImage_source[t]
            Globals.eventManager.generate(
                "ClosingEvent",
                ClosingEvent("", self) # file, self, see tools
            )
            
        self.dict_file_FSImage_source = {}
        for t in self.dict_file_FSImage_target:
            u = self.dict_file_FSImage_target[t]
            Globals.eventManager.generate(
                "ClosingEvent",
                ClosingEvent("", self) # file, self, see tools
            )
        self.dict_file_FSImage_target = {}

    def recent_config_cfg(self, item):
        # get and apply configfile from recent-menu
        print("** Menuitem selected: " + item) if self.debug else True
        self.config_file = item
        self.filemenu.entryconfig(CFG_SAVE_CONFIG, state=NORMAL)
        self.root.title(self.title + ' ' + self.config_file)
        self.filemenu.entryconfig(CFG_SAVE_CONFIG_AS, state=NORMAL)
        
        # apply config file
        sourcefiles = DX.get_filenames_diatisch(self.config_file, "sourcefiles", "sourcefile")
        targetfiles = DX.get_filenames_diatisch(self.config_file, "targetfiles", "targetfile")
        self.load_images(None, sourcefiles, targetfiles)
    
    def listbox_cfg_double(self, event = None): # used also for Button
        # get and apply configfile from listbox
        selected_indices = self.listbox_cfg.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Listbox cfg files: nothing selected", parent = self.Frame_cfg)
        else:
            cfgfile = ",".join([self.listbox_cfg.get(i) for i in selected_indices]) # because listbox has single selection
            print("cfg file selected is: " + cfgfile) if self.debug else True
            self.config_file = cfgfile
            self.root.title(self.title + ' ' + self.config_file)
            # build lists of source and target files
            sourcefiles = DX.get_filenames_diatisch(cfgfile, "sourcefiles", "sourcefile")
            for i in sourcefiles:
                print ("sourcefile: " + i) if self.debug else True
            targetfiles = DX.get_filenames_diatisch(cfgfile, "targetfiles", "targetfile")
            for i in targetfiles:
                print ("targetfile: " + i) if self.debug else True
            self.load_images(None, sourcefiles, targetfiles)
        
        
    def listbox_cfg_check_exist(self, event):
        self.dirchk.check_on_select(self.listbox_cfg, "Configfile", title = "error", isfile = True)

    def _set_recent_state(self, menu, item, ok):
        """Recent-Menueeintrag fuer item (Label beginnt mit item + ' (usedate:') ent-/aktivieren."""
        try:
            last = menu.index("end")
            if last is None:
                return
            for i in range(last + 1):
                try:
                    if menu.entrycget(i, "label").startswith(item + ' (usedate:'):
                        menu.entryconfig(i, state = NORMAL if ok else DISABLED)
                except tk.TclError:             # Separator o.ae. ohne Label
                    pass
        except tk.TclError:                     # Menue wurde inzwischen neu aufgebaut/zerstoert
            pass

    def update_listbox_cfg(self):
        # fill cfg listbox and recentmenu cfg
        self.listbox_cfg.delete(0, 'end')
        self.recentmenu_cfg.delete(0, "end")
        print("xmlfile: " + self.config_files_xml)

        result = DX.get_diatisch_items_usedate(self.config_files_xml, "config_files", "configfile", "filename")
        dict_filename_usedate = {}
        for tfile in result:
            #print("infile: " + tfile) if self.debug else True
            attribute = result[tfile]
            searchattr = 'usedate'
            for attribut in attribute:
                #print("  " + attribut + " = " + attribute[attribut]) if self.debug else True
                if attribut == searchattr:
                    dict_filename_usedate[tfile] = attribute[searchattr]
            
        # descending by usedate
        sorted_d = dict( sorted(dict_filename_usedate.items(), key=operator.itemgetter(1), reverse=True))
        # make list
        ii = 0
        indexes = []
        for item in sorted_d:
            self.listbox_cfg.insert(END, item)
            usedate = dict_filename_usedate[item]
            labeltext = item + ' (usedate: ' + usedate + ')'
            self.recentmenu_cfg.add_command(label=labeltext, command = lambda item=item: self.recent_config_cfg(item))
            # Menueeintrag deaktivieren, sobald die Hintergrundpruefung "nicht vorhanden" meldet
            self.dirchk.check_bg(item, lambda ok, item = item: self._set_recent_state(self.recentmenu_cfg, item, ok), True)
            ii += 1
        self.dirchk.check_list(self.listbox_cfg, None, list(sorted_d), True)
        self.listbox_cfg.selection_clear(0, "end")
        if ii > 0:
            self.listbox_cfg.selection_set(0)
            #self.button_cfg_from_list.config(state = NORMAL)
        else: 
            #self.button_cfg_from_list.config(state = DISABLED)
            True

    def update_listbox_indir(self):
        # fill indir listbox and recentmenu
        self.listbox_indir.delete(0, 'end')
        self.recentmenu_file.delete(0, "end")
        result = DX.get_diatisch_items_usedate(self.config_files_xml, "indirs", "indir", "name")
        dict_filename_usedate = {}
        for item in result:
            #print("infile: " + item) if self.debug else True
            attribute = result[item]
            searchattr = 'usedate'
            for attribut in attribute:
                #print("  " + attribut + " = " + attribute[attribut]) if self.debug else True
                if attribut == searchattr:
                    dict_filename_usedate[item] = attribute[searchattr]
            
        # descending by usedate
        sorted_d = dict( sorted(dict_filename_usedate.items(), key=operator.itemgetter(1), reverse=True))
        # make list
        ii = 0
        indexes = []
        for item in sorted_d:
            self.listbox_indir.insert(END, item)
            usedate = dict_filename_usedate[item]
            labeltext = item + ' (usedate: ' + usedate + ')'
            self.recentmenu_file.add_command(label=labeltext, command = lambda item=item: self.recent_config_indir(item))
            # Menueeintrag deaktivieren, sobald die Hintergrundpruefung "nicht vorhanden" meldet
            self.dirchk.check_bg(item, lambda ok, item = item: self._set_recent_state(self.recentmenu_file, item, ok))
            ii += 1
        self.dirchk.check_list(self.listbox_indir, None, list(sorted_d))
        self.listbox_indir.selection_clear(0, "end")
        if ii > 0:
            self.listbox_indir.select_set(0)
            #self.button_indir_from_list.config(state = NORMAL)
        else: 
            #self.button_indir_from_list.config(state = DISABLED)
            True

    def update_listbox_outdir(self):
        # fill outdir listbox
        self.listbox_outdir.delete(0, 'end')
        result = DX.get_diatisch_items_usedate(self.config_files_xml, "outdirs", "outdir", "name")
        dict_filename_usedate = {}
        for item in result:
            #print("outfile: " + item) if self.debug else True
            attribute = result[item]
            searchattr = 'usedate'
            for attribut in attribute:
                #print("  " + attribut + " = " + attribute[attribut]) if self.debug else True
                if attribut == searchattr:
                    dict_filename_usedate[item] = attribute[searchattr]
            
        # descending by usedate
        sorted_d = dict( sorted(dict_filename_usedate.items(), key=operator.itemgetter(1), reverse=True))
        # make list
        ii = 0
        indexes = []
        for item in sorted_d:
            self.listbox_outdir.insert(END, item)
            usedate = dict_filename_usedate[item]
            labeltext = item + ' (usedate: ' + usedate + ')'
            ii += 1
        self.dirchk.check_list(self.listbox_outdir, None, list(sorted_d))
        self.listbox_outdir.selection_clear(0, "end")
        if ii > 0:
            self.listbox_outdir.select_set(0)
            #self.button_indir_from_list.config(state = NORMAL)
        else: 
            #self.button_outdir_from_list.config(state = DISABLED)
            True

    def recent_config_indir(self, item):
        # get and apply indir from recent-menu
        print("** Menuitem selected: " + item) if self.debug else True
        self.indir = item
        self.root.title(self.title + ' ' + self.indir)
        
        # load indir
        self.load_images(self.indir)

    def listbox_indir_double(self, event = None):
        selected_indices = self.listbox_indir.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Listbox Indir: nothing selected", parent = self.Frame_indir)
        else:
            indir = ",".join([self.listbox_indir.get(i) for i in selected_indices]) # because listbox has single selection
            print("indir selected is: " + indir) if self.debug else True
            self.indir = indir
            self.load_images(self.indir)
        
    def listbox_indir_check_exist(self, event):
        self.dirchk.check_on_select(self.listbox_indir, "Indir", parent = self.Frame_indir, title = "error")

    def listbox_outdir_check_exist(self, event):
        self.dirchk.check_on_select(self.listbox_outdir, "Outdir", title = "error")

    def on_configure(self, event):
        x = event.widget
        if x == self.root:
            #print("Onconfigure widget = {:s}".format(str(event.widget)))
            if (self.width != event.width or self.height != event.height):
                self.timer.start()

    def resize(self):
        # display debug info for resize, this is very difficult to debug
        self.debug_info_resize("TIMER") if self.debug else True
        old_width  = self.width
        old_height = self.height
        # we use the new dimension of the frame for calculating fontsize needed
        self.root.update()
        new_width  = self.root.winfo_width()
        new_height = self.root.winfo_height()
        if (old_width != new_width or old_height != new_height):
            # store new values
            self.width  = new_width
            self.height = new_height
            self.text_font.configure(size=int(.8 * tools.calc_fontsize(self.physical_width, self.physical_height, self.width, self.height, self.debug)))
            self.font_fitter.fit(self.root)

    def debug_info_resize(self, text):
        print("{:s} elapsed start resize".format(text))
        
    def button_camera_pressed(self):
        camera = self.get_current_camera() # camera names may contain blanks, so not parsed from the display text
        self.win_camera = DCAM.MyCameraTreeview(pmain = self, proctypes = self.proctypes, debug = self.debug, xmlfile = self.config_files_xml, cameraname = camera) 

    def cameras_edit(self):
        self.win_camera = DCAM.MyCameraTreeview(pmain = self, proctypes = self.proctypes, debug = self.debug, xmlfile = self.config_files_xml) 


    def load_images(self, p_indir = None, p_imagefiles_source = None, p_imagefiles_target = None, p_keep_targets = None):
        # if list-source is given use it, else ask for dir to open
        # if list-target is given use it
        # p_keep_targets: target files to keep (e.g. after a camera change), only files which are still in source are used
        directory = None
        if p_imagefiles_source: # imagefiles given by caller, no directory needed
            pass
        elif p_indir: # directory given by caller
            directory = p_indir
        else: # display dir dialog
            directory = fd.askdirectory(parent = self.root)
            if not directory: # cancelled, the current display stays untouched
                return False
        # close all FSImage-Windows
        self.close_child_windows()
        self.list_source_images = []
        self.dict_source_images = {}
        self.list_target_images = []
        self.dict_target_images = {}
        self.source_canvas.delete("all")
        self.target_canvas.delete("all")
        Diatisch.idx_high += 1
        Diatisch.idx_akt = Diatisch.idx_high
        Diatisch.dict_filename_images[Diatisch.idx_akt] = {}
        #self.UR.reset()
        tag_prefix = 'P'
        tag_no = 0
        missing = []
        try:
            if p_imagefiles_source:
                self.image_files = list(p_imagefiles_source)
                self._collect_companions(self.image_files)
            if directory: # read files from directory, one scan per type of the selected camera
                if self.cb_recursive_var.get():
                    recursive = "j"
                else:
                    recursive = "n"
                skip_top = getattr(Globals, "skip_dirs_top", None)
                skip_any = getattr(Globals, "skip_dirs_any", None)
                # count files first - do it inside a BusyDialog so the user sees something is going on
                busy = tools.BusyDialog(self.root, text="Dateien werden gezählt…")
                try:
                    if recursive == "j":
                        files_total = DG.count_files(directory, skip_top, skip_any) # same exclusions as the scan
                    else:
                        files_total = tools.count_files_top(directory)
                finally:
                    busy.close()
                # now scan with progress feedback (BusyDialog with cancel support)
                dict_source_target = {}
                dict_source_jpeg   = {}
                busy = tools.BusyDialog(self.root, text="Dateien werden geladen…")
                try:
                    for dateityp, endung in self.dict_cameras.items():
                        if busy.cancelled:
                            break
                        st, st_jpeg, st_tooold, relpath = \
                          DG.dateimeister(dateityp, endung, directory, "", "n", recursive, False, "", None, 0, busy, files_total, skip_top, skip_any, self.debug)
                        dict_source_target.update(st)
                        dict_source_jpeg.update(st_jpeg)
                finally:
                    busy.close()
                self.dict_source_target = dict_source_target
                self.image_files = sorted(dict_source_target)
                self._collect_companions(list(dict_source_jpeg) + self.image_files)
                # now make an entry for this indir.
                ts = strftime("%Y%m%d-%H:%M:%S", time.localtime())
                this_i = re.sub(r'\\', '/', directory).lower()
                # delete indir-entries from xml if number gt than max from ini, oldest and not existing first. we have to supply the necessary xml-information
                self.new_item_in_xml(self.max_indirs, this_i, ts, "indirs", "indir", "name")
                # now create new indir
                DX.new_dir_diatisch(self.config_files_xml, "indirs", "indir", "name", directory.lower(), ts)
            for img_file in self.image_files:
                if directory:
                    filename = os.path.join(directory, img_file)
                else:
                    filename = img_file
                if not tools.isfile_fast(filename):   # network share: short test, no long timeout
                    missing.append(filename)
                    continue
                tag_no += 1
                Diatisch.dict_file_meta[filename] = (self.type_of(filename), self.process_type_of(filename))
                photo = self.make_photo(filename, self.source_canvas)
                # insert into self.list_source_images
                i = MyImage(filename, os.stat(filename).st_mtime, self.source_canvas, tag_prefix + str(tag_no))
                self.list_source_images.append(i)
                Diatisch.dict_filename_images[Diatisch.idx_akt][filename] = photo

            self.dict_source_images = self.display_image_objects(self.list_source_images, self.source_canvas, self.Label_source_ctr)
            self.unselect_all(self.dict_source_images, self.source_canvas)
            self.source_canvas.configure(scrollregion=self.source_canvas.bbox("all")) # update scrollregion

            if p_keep_targets: # only files which are still in source
                p_imagefiles_target = [f for f in p_keep_targets if f in Diatisch.dict_filename_images[Diatisch.idx_akt]]
            if p_imagefiles_target: # imagefiles given by caller
                for filename in p_imagefiles_target:
                    if not tools.isfile_fast(filename):
                        missing.append(filename)
                        continue
                    tag_no += 1
                    if filename not in Diatisch.dict_filename_images[Diatisch.idx_akt]: # target which is not in source: needs own photo
                        Diatisch.dict_file_meta[filename] = (self.type_of(filename), self.process_type_of(filename))
                        Diatisch.dict_filename_images[Diatisch.idx_akt][filename] = self.make_photo(filename, self.source_canvas)
                    # insert into self.list_target_images
                    i = MyImage(filename, os.stat(filename).st_mtime, self.target_canvas, tag_prefix + str(tag_no))
                    self.list_target_images.append(i)

                self.dict_target_images = self.display_image_objects(self.list_target_images, self.target_canvas, self.Label_target_ctr)
                self.unselect_all(self.dict_target_images, self.target_canvas)
                self.target_canvas.configure(scrollregion=self.target_canvas.bbox("all")) # update scrollregion
                if len(self.list_target_images) > 0: # anz target images > 0
                    self.button_exec.config(state = tk.NORMAL)
        except Exception:
            import traceback
            traceback.print_exc()

        self.loaded_dir = directory # None if loaded from lists
        if directory:
            self.indir = directory
        print("LOAD ", directory)
        display_dir = "n.a."
        if directory:
            self.update_listbox_indir()
            display_dir = directory
        if missing:
            messagebox.showwarning("Load", "{:d} file(s) not found and skipped:\n{:s}".format(len(missing), "\n".join(missing[:10])), parent = self.root)
        # sort images according to radiobuttons
        self.rb_sort()
        self.historize_process("load directory {:s}".format(display_dir))
        self.root.lift()

    def close_indir(self):
        # if list-source is given use it, else ask for dir to open
        # if list-target is given use it
        self.list_source_images = []
        self.dict_source_images = {}
        self.list_target_images = []
        self.dict_target_images = {}
        self.source_canvas.delete("all")
        self.target_canvas.delete("all")
        self.close_child_windows()
        Diatisch.idx_high += 1
        Diatisch.idx_akt = Diatisch.idx_high
        Diatisch.dict_filename_images[Diatisch.idx_akt] = {}
        #self.UR.reset()
        self.historize_process("close directory {:s}".format(self.indir))

    def item_missing(self, t):
        """True, wenn Verzeichnis/Datei t nicht existiert. Ergebnis der Hintergrundpruefung aus dem Cache,
        sonst schnelle Pruefung (Netzpfade ohne langen Timeout)."""
        known = self.dirchk.cache.get(t)
        if known is not None:
            return not known
        return not tools.isdir_fast(t) and not tools.isfile_fast(t)

    def new_item_in_xml(self, max_items, item_chosen, ts, parent, entry, attrname):
        # if item_chosen does not exist so that a new item has to be created:
        # removes entries if max value from ini is reached. removes not existing and old entries first
        # leaves max - 1 entries so that caller can add new item
        # items are indirs or config_files which this method must not know, but only files and dirs are supported because existence is checked
        do_del = True
        d = DX.get_diatisch_items_usedate(self.config_files_xml, parent, entry, attrname)
        if item_chosen in d:
            do_del = False # existing item, no cleanup
        # delete item(s) from xml file only if a new one has been selected
        print("do_del: " + str(do_del) + " item_chosen: " + item_chosen) if self.debug else True
        if do_del: # 2 pass: in the first we delete entries with not existing item, in the second existing items (if necessary)
            for loop in range(1,3): # 3 is excluded
                d = DX.get_diatisch_items_usedate(self.config_files_xml, parent, entry, attrname)
                # sort descending by usedate
                dict_item_usedate = {}
                for ii in d:
                    dict_item_usedate[ii] = d[ii]['usedate'] # item -> usedate
                sorted_d = dict( sorted(dict_item_usedate.items(), key=operator.itemgetter(1), reverse=True))
                list_items = []
                for tdir in sorted_d:
                    list_items.append(tdir)
                num_to_delete = len(list_items) - int(max_items) + 1 # +1 for we will make a new item later. already deleted items are no more in get-items 
                if loop == 1:
                    print("loop is " + str(loop)) if self.debug else True
                    # delete only not existing items
                    if num_to_delete > 0:
                        ii = 0
                        for t in reversed(list_items): # now the oldest are on top
                            if self.item_missing(t):
                                if ii < num_to_delete:
                                    DX.delete_diatisch_item(self.config_files_xml, parent, entry, attrname, t)
                                    ii += 1
                                else:
                                    break
                elif loop == 2:
                    # delete existing items if necessary
                    if num_to_delete > 0:
                        ii = 0
                        for t in reversed(list_items): # now the oldest are on top
                            if ii < num_to_delete:
                                DX.delete_diatisch_item(self.config_files_xml, parent, entry, attrname, t)
                                ii += 1
                            else:
                                break

    def show_context_menu_source(self, event):
        # event has to be stored because some functions require x, y
        self.event_source = event
        text = "no image available"
        # falls wir keine anzeigbare Datei haben, müssen wir show-Item disablen
        canvas_x = self.source_canvas.canvasx(event.x)
        canvas_y = self.source_canvas.canvasy(event.y)
        if (closest := self.source_canvas.find_closest(self.source_canvas.canvasx(event.x), self.source_canvas.canvasy(event.y))):
            image_id = closest[0]
            img      = self.dict_source_images[image_id]
            text     = img.get_filename()
            self.context_menu_source.entryconfig(0, label = "Show " + text)
            self.context_menu_source.entryconfig(2, label = "Copy " + text)
            self.context_menu_source.entryconfig(3, label = "Print " + text)
            self.image_to_print = img
            self.single_image_to_copy = img # will be set to None in update_target_canvas after copying
            selected = False
            for i in self.list_source_images:
                if i.is_selected():
                    selected = True
                    break
            if selected: # at least one selected
                self.context_menu_source.entryconfig(1, state = tk.NORMAL)
            else:
                self.context_menu_source.entryconfig(1, state = tk.DISABLED)
            self.context_menu_source.post(event.x_root, event.y_root)
    
    def show_context_menu_target(self, event):
        # event has to be stored because some functions require x, y
        self.event_target = event
        text = "no image available"
        # falls wir keine anzeigbare Datei haben, müssen wir show-Item disablen
        canvas_x = self.target_canvas.canvasx(event.x)
        canvas_y = self.target_canvas.canvasy(event.y)
        if (closest := self.target_canvas.find_closest(self.target_canvas.canvasx(event.x), self.target_canvas.canvasy(event.y))):
            image_id = closest[0]
            img      = self.dict_target_images[image_id]
            text     = img.get_filename()
            self.context_menu_target.entryconfig(0, label = "Show " + text)
            self.context_menu_target.entryconfig(2, label = "Delete " + text)
            self.context_menu_target.entryconfig(3, label = "Print " + text)
            self.image_to_print = img
            self.single_image_to_delete = img # will be set to None in delete_target_canvas after delete
            selected = False
            for i in self.list_target_images:
                if i.is_selected():
                    selected = True
                    break
            if selected: # at least one selected
                self.context_menu_target.entryconfig(1, state = tk.NORMAL)
            else:
                self.context_menu_target.entryconfig(1, state = tk.DISABLED)
            self.context_menu_target.post(event.x_root, event.y_root)

    def tooltip_imagefile_source(self, event):
        tsnow = datetime.now()
        tdiff = abs(tsnow - self.timestamp1)
        milliseconds = tdiff.days * 86400 * 1000 + tdiff.seconds * 1000 + tdiff.microseconds / 1000
        if  milliseconds > 200:
            #print("Timer has finished, milliseconds is: ", milliseconds) if self.debug else True
            self.timestamp1 = tsnow
        else:
            return
        # Tooltip
        text = "no image available"
        if (closest := self.source_canvas.find_closest(self.source_canvas.canvasx(event.x), self.source_canvas.canvasy(event.y))):
            image_id = closest[0]
            if image_id in self.dict_source_images:
                img      = self.dict_source_images[image_id]
                text = "{:s}\n type {:s}, created {:s} size {:.3f}".format(img.getFile(), img.imgtype or "?", img.get_filectime(), img.get_filesize())
                if text != self.tooltiptext_st:
                    self.st.update(text)
                    self.tooltiptext_st = text

    def tooltip_imagefile_target(self, event):
        tsnow = datetime.now()
        tdiff = abs(tsnow - self.timestamp2)
        milliseconds = tdiff.days * 86400 * 1000 + tdiff.seconds * 1000 + tdiff.microseconds / 1000
        if  milliseconds > 200:
            self.timestamp2 = tsnow

        else:
            return
        # Tooltip
        text = "no image available"
        if (closest := self.target_canvas.find_closest(self.target_canvas.canvasx(event.x), self.target_canvas.canvasy(event.y))):
            image_id = closest[0]
            if image_id in self.dict_target_images:
                img      = self.dict_target_images[image_id]
                text = "{:s}\n type {:s}, created {:s} size {:.3f}".format(img.getFile(), img.imgtype or "?", img.get_filectime(), img.get_filesize())
                if text != self.tooltiptext_tt:
                    self.tt.update(text)
                    self.tooltiptext_tt = text
                       
    def tooltip_lb_indir(self, event):
        tsnow = datetime.now()
        tdiff = abs(tsnow - self.timestamp3)
        milliseconds = tdiff.days * 86400 * 1000 + tdiff.seconds * 1000 + tdiff.microseconds / 1000
        if  milliseconds > 200:
            #print("Timer has finished, milliseconds is: ", milliseconds) if self.debug else True
            self.timestamp3 = tsnow
        else:
            return
        # Tooltip
        text = "no item available"
        index = self.listbox_indir.nearest(event.y)
        text = self.listbox_indir.get(index)
        if text != self.tooltiptext_lb_indir:
            self.tt_lb_indir.update(text)
            self.tooltiptext_lb_indir = text

    def tooltip_lb_cfg(self, event):
        tsnow = datetime.now()
        tdiff = abs(tsnow - self.timestamp4)
        milliseconds = tdiff.days * 86400 * 1000 + tdiff.seconds * 1000 + tdiff.microseconds / 1000
        if  milliseconds > 200:
            #print("Timer has finished, milliseconds is: ", milliseconds) if self.debug else True
            self.timestamp4 = tsnow
        else:
            return
        # Tooltip
        text = "no item available"
        index = self.listbox_cfg.nearest(event.y)
        text = self.listbox_cfg.get(index)
        if text != self.tooltiptext_lb_cfg:
            self.tt_lb_cfg.update(text)
            self.tooltiptext_lb_cfg = text

    def tooltip_lb_outdir(self, event):
        tsnow = datetime.now()
        tdiff = abs(tsnow - self.timestamp5)
        milliseconds = tdiff.days * 86400 * 1000 + tdiff.seconds * 1000 + tdiff.microseconds / 1000
        if  milliseconds > 200:
            #print("Timer has finished, milliseconds is: ", milliseconds) if self.debug else True
            self.timestamp5 = tsnow
        else:
            return
        # Tooltip
        text = "no item available"
        index = self.listbox_outdir.nearest(event.y)
        text = self.listbox_outdir.get(index)
        if text != self.tooltiptext_lb_outdir:
            self.tt_lb_outdir.update(text)
            self.tooltiptext_lb_outdir = text

    def canvas_focus_source(self, event):
        print("Return on source vanvas") if self.debug else True
        if self.get_num_selected(self.list_source_images) == 1:
            self.canvas_image_source_show(event)
    def canvas_image_source_event(self):
        #print("Context menu show") if self.debug else True
        self.canvas_image_source_show(self.event_source)
    def canvas_image_source_show(self, event):
        # placeholder for call full screen display of image
        print("FSImage source show") if self.debug else True
        # get image
        canvas_x = self.source_canvas.canvasx(event.x)
        canvas_y = self.source_canvas.canvasy(event.y)
        if (closest := self.source_canvas.find_closest(self.source_canvas.canvasx(event.x), self.source_canvas.canvasy(event.y))):
            image_id = closest[0]
            img      = self.dict_source_images[image_id]
            file     = img.get_filename()
            if file in self.dict_file_FSImage_source: #dont display twice
                print ("FSImage Source exists for file: " + file) if self.debug else True
            else:
                fs_image = self.create_fsimage("Source", img, file)
                self.dict_file_FSImage_source[file] = fs_image
                self.historize_process("show source FSImage {:s}".format(file))

    def canvas_focus_target(self, event):
        print("Return on target vanvas") if self.debug else True
        if self.get_num_selected(self.list_target_images) == 1:
            self.canvas_image_target_show(event)
    def canvas_image_target_event(self):
        #print("Context menu show") if self.debug else True
        self.canvas_image_target_show(self.event_target)
    def canvas_image_target_show(self, event):
        # placeholder for call full screen display of image
        print("FSImage target show") if self.debug else True
        # get image
        canvas_x = self.target_canvas.canvasx(event.x)
        canvas_y = self.target_canvas.canvasy(event.y)
        if (closest := self.target_canvas.find_closest(self.target_canvas.canvasx(event.x), self.target_canvas.canvasy(event.y))):
            image_id = closest[0]
            img      = self.dict_target_images[image_id]
            file     = img.get_filename()
            if file in self.dict_file_FSImage_target: #dont display twice
                print ("FSImage Target exists for file: " + file) if self.debug else True
            else:
                fs_image = self.create_fsimage("Target", img, file)
                self.dict_file_FSImage_target[file] = fs_image
                self.historize_process("show target FSImage {:s}".format(file))

    def start_drag(self, event):
        # as we have a transaction of 2 steps (press / release) we have to keep the change attributes as member variables
        self.canvas_target_rebuild_required = False
        self.selection_changed = False
        # check where mouse is 
        source_rect = self.get_root_coordinates_for_widget(self.source_canvas)
        target_rect = self.get_root_coordinates_for_widget(self.target_canvas)
        #print ("source_canvas: ", str(source_rect)) if self.debug else True
        #print ("target_canvas: ", str(target_rect)) if self.debug else True
        #print ("event: ", " x_root: ", str(event.x_root), " y_root: ", str(event.y_root), " x: ", str(event.x), " y: ", str(event.y)) if self.debug else True
        #print ("Source canvasx: ", str(self.source_canvas.canvasx(event.x)), "canvasy: ", str(self.source_canvas.canvasy(event.y))) if self.debug else True
        self.image_press = None
        if (self.check_event_in_rect(event, source_rect)): # select Image(s)
            #print("Event in source_canvas") if self.debug else True
            self.drag_started_in = "source"
            img_closest_id, dist_event_left, dist_event_right = self.find_closest_item(event, source_rect, self.source_canvas, self.dict_source_images)
            if img_closest_id > 0:
                self.image_press = self.dict_source_images[img_closest_id]
                print("image found in source canvas, action = PRESS: ", self.image_press.get_filename()) if self.debug else True
                self.selection(event, self.source_canvas, self.dict_source_images, action.PRESS)
            else: # do nothing
                print("no image found in source canvas, action = PRESS") if self.debug else True
        elif (self.check_event_in_rect(event, target_rect)):
            #print("Event in target_canvas") if self.debug else True
            self.drag_started_in = "target"
            img_closest_id, dist_event_left, dist_event_right = self.find_closest_item(event, target_rect, self.target_canvas, self.dict_target_images)
            if img_closest_id > 0:
                self.image_press = self.dict_target_images[img_closest_id]
                print("image found in target canvas, action = PRESS: ", self.image_press.get_filename()) if self.debug else True
                self.selection(event, self.target_canvas, self.dict_target_images, action.PRESS)
            else: # do nothing
                print("no image found in target canvas, action = PRESS") if self.debug else True
        else:
            #rint("Event not in canvas")
            self.drag_started_in = ""
            True

    def on_motion(self, event):
        # bbox only depends on cumulated size of items
        # if canvas ist to small to view all items, canvas is a "window" into the bbox which can be scrolled
        # event which is bound to canvas has x and y which always refer to bbox regardless of scroll position
        # so x = -1 ALWAYS means that x is just left outside the canvas and x = canvas-width + 1 (pixel) means the same for the right border
        # y works in the same way
        tsnow = datetime.now()
        tdiff = abs(tsnow - self.timestamp_scroll)
        milliseconds = tdiff.days * 86400 * 1000 + tdiff.seconds * 1000 + tdiff.microseconds / 1000
        if  milliseconds > 200:
            #print("Timer has finished, milliseconds is: ", milliseconds) if self.debug else True
            self.timestamp_scroll = tsnow
        else:
            return
        print("on motion dif {:s}".format(str(tdiff))) if self.debug else True
        self.scroll = False
        canvas = self.target_canvas
        self.canvas_to_scroll = canvas
        x0 = int(canvas.canvasx(0))
        y0 = int(canvas.canvasy(0))
        x1 = int(canvas.canvasx(canvas.winfo_width()))
        y1 = int(canvas.canvasy(canvas.winfo_height()))
        b_x0 = 0
        b_y0 = 0
        b_x1 = 0
        b_y1 = 0
        canvas_width  = 0
        canvas_height = 0
        if canvas.bbox("all") is not None:
            b_x0 = canvas.bbox("all")[0]
            b_y0 = canvas.bbox("all")[1]
            b_x1 = canvas.bbox("all")[2]
            b_y1 = canvas.bbox("all")[3]
            canvas_width  = x1 - x0
            canvas_height = y1 - y0
        str_display = (" event: x = {:4d}, y = {:4d}, ").format(event.x, event.y) + \
            (" canvas: x0 = {:4d}, y0 = {:4d}, x1 = {:4d}, y1 = {:4d}").format(x0, y0, x1, y1) + \
            (" bbox: x0 = {:4d}, y0 = {:4d}, x1 = {:4d}, y1 = {:4d}").format(b_x0, b_y0, b_x1, b_y1) if self.debug else True
        if event.x < 0 and x0 > b_x0: # there is room for scrolling
            self.scroll = True
            self.scrolltype = 'HL'
            dist  = -event.x # dist in pixel
            self.delay = int(self.calc_scroll_delay(dist))
            self.do_scroll()
            print("Drag Motion left outside Target,  ", str_display) if self.debug else True
        if event.x > canvas_width and x1 < b_x1: # s.a.
            self.scroll = True
            self.scrolltype = 'HR'
            dist  = event.x - canvas_width # dist in pixel
            self.delay = int(self.calc_scroll_delay(dist))
            self.do_scroll()
            print("Drag Motion right outside Target, ", str_display) if self.debug else True
        if event.y < 0 and y0 > b_y0: # s.a.
            self.scroll = True
            self.scrolltype = 'VU'
            dist  = -event.y # dist in pixel
            self.delay = int(self.calc_scroll_delay(dist))
            self.do_scroll()
            print("Drag Motion above Target,         ", str_display) if self.debug else True
        if event.y > canvas_height and y1 < b_y1: # s.a.
            self.scroll = True
            self.scrolltype = 'VD'
            dist  = event.y - canvas_height # dist in pixel
            self.delay = int(self.calc_scroll_delay(dist))
            self.do_scroll()
            print("Drag Motion below Target,         ", str_display) if self.debug else True
        #self.scroll = False
        True
    
    def calc_scroll_delay(self, dist): # calc. scroll interval ms depending on dist of mouse pointer from canvas
        # leads to 1000 ms is 1 pixel away and 100 ms if 100 pixel away
        delay = -9.0 * dist + 1010.0
        delay = max(delay, 100.0)
        return delay
        
    def do_scroll(self): # scroll
        canvas = self.canvas_to_scroll
        print("scroll") if self.debug else True
        if self.scroll: # set by on_motion
            x0 = int(canvas.canvasx(0))
            y0 = int(canvas.canvasy(0))
            x1 = int(canvas.canvasx(canvas.winfo_width()))
            y1 = int(canvas.canvasy(canvas.winfo_height()))
            b_x0 = canvas.bbox("all")[0]
            b_y0 = canvas.bbox("all")[1]
            b_x1 = canvas.bbox("all")[2]
            b_y1 = canvas.bbox("all")[3]
            print("Scroll delay is " + str(self.delay) + " type is " + self.scrolltype)  if self.debug else True
            if self.scrolltype == 'HL':
                print("  scroll {:s} x0: {:04d}, b_x0: {:04d}".format(self.scrolltype, x0, b_x0)) if self.debug else True
                if x0 > b_x0:
                    canvas.xview(tk.SCROLL, -1, "unit")
                else:
                    self.scroll = False
            if self.scrolltype == 'HR':
                print("  scroll {:s} x1: {:04d}, b_x1: {:04d}".format(self.scrolltype, x1, b_x1)) if self.debug else True
                if x1 < b_x1:
                    canvas.xview(tk.SCROLL, 1, "unit")
                else:
                    self.scroll = False
            if self.scrolltype == 'VU':
                print("  scroll {:s} y0: {:04d}, b_y0: {:04d}".format(self.scrolltype, y0, b_y0)) if self.debug else True
                if y0 > b_y0:
                    canvas.yview(tk.SCROLL, -1, "unit")
                else:
                    self.scroll = False
            if self.scrolltype == 'VD':
                print("  scroll {:s} y1: {:04d}, b_y1: {:04d}".format(self.scrolltype, y1, b_y1)) if self.debug else True
                if y1 < b_y1:
                    canvas.yview(tk.SCROLL, 1, "unit")
                else:
                    self.scroll = False
            self.root.after(self.delay, self.do_scroll)

    def selection(self, event, canvas, dict_images, action): #select / unselect image(s) from mouse click
        # returns True if no further processing required else False (rebuild target-canvas
        if self.image_press is None: # no selection possible
            return
        img = self.image_press
        if event.state & 0x4: # ctrl-key is pressed 
            ctrl_pressed = True
        else:
            ctrl_pressed = False
        if self.image_press != self.image_release: # same image
            same = False
        else:
            same = True
        if img.is_selected(): # save state before call to unselect_all
            selected = True
        else:
            selected = False
        if ctrl_pressed == False:
            #print("unselect all: ", str(dict_images)) if self.debug else True
            c = self.unselect_all(dict_images, canvas)
            self.selection_changed = self.check_changed(self.selection_changed, c)
        print ("***** Action is: "+ str(action)+ ", Selected = "+ str(selected)+ ", actual image is: "+ str(img.get_filename())+ \
          ", image press is: " + (self.image_press.get_filename() if self.image_press is not None else "None") + \
          ", image  release: " + (self.image_release.get_filename() if self.image_release is not None else "None") + \
          ", same = "+ str(same)+ ", ctrl_pressed = "+ str(ctrl_pressed), \
          ", was_selected = " + str(img.was_selected)) if self.debug else True
        if selected:
            print("Sy") if self.debug else True
            if action == action.PRESS:
                print("SyP") if self.debug else True
                img.was_selected = True
                c = self.select_image(img, canvas) # select because unselect all has unselected this image
                self.selection_changed = self.check_changed(self.selection_changed, c)
            else: # action.RELEASE:
            # unselect only if actual image is the same as before
                print("SyR") if self.debug else True
                if same:
                    print("SyRSy") if self.debug else True
                    if img.was_selected:
                        print("SyRSyWy") if self.debug else True
                        c = self.unselect_image(img, canvas)
                        self.selection_changed = self.check_changed(self.selection_changed, c)
                    else:
                        print("SyRSyWn") if self.debug else True
                        img.was_selected = True
                        c = self.select_image(img, canvas) # select because unselect all has unselected this image
                        self.selection_changed = self.check_changed(self.selection_changed, c)
                else:
                    print("SyRSn") if self.debug else True
                    c = self.select_image(img, canvas)
                    self.selection_changed = self.check_changed(self.selection_changed, c)
                    self.canvas_target_rebuild_required = True # drop image requires action

        else: # not selected
            print("Sn") if self.debug else True
            if action == action.PRESS:
                print("SnP") if self.debug else True
                c = self.select_image(img, canvas)
                self.selection_changed = self.check_changed(self.selection_changed, c)
                img.was_selected = False
            else: # action.RELEASE:
            # unselect only if actual image is the same as before
                print("SnR") if self.debug else True
                if same:
                    print("SnRSy") if self.debug else True
                    if img.was_selected:
                        print("SnRSyWy") if self.debug else True
                        c = self.unselect_image(img, canvas)
                        self.selection_changed = self.check_changed(self.selection_changed, c)
                    else:
                        print("SnRSyWn") if self.debug else True
                        img.was_selected = True
                        c = self.select_image(img, canvas) # select because unselect all has unselected this image
                        self.selection_changed = self.check_changed(self.selection_changed, c)
                else:
                    print("SnRSn") if self.debug else True
                    c = self.select_image(img, canvas)
                    self.selection_changed = self.check_changed(self.selection_changed, c)
                    self.canvas_target_rebuild_required = True # drop image requires action
        return
    
    def check_changed(self, s, c):
        # if 1st arg is False, set to True is 2nd arg is true. Purpose: never reset a True value to False
        sret = s
        if s == False:
            if c == True:
                sret = True
        return sret

    
    # event handlers for context menus
    def copy_selected_source_images(self): # copy selected images from source to target
        # find last selected target image
        self.drag_started_in = "source" # must be set for the following functions
        self.file_at_dragposition = self.find_last_selected_target_image(self.list_target_images)
        target_rect = self.get_root_coordinates_for_widget(self.target_canvas)
        # save filename as update will reset them to None
        if self.file_at_dragposition:
            targetfile = self.file_at_dragposition
        else:
            targetfile = "no target selected"
        changed = self.update_target_canvas(None, self.dict_source_images, target_rect, pt.COPY_SELECTED)
        if changed:
            self.historize_process("copy selected source images next to {:s}".format(targetfile))        
    def copy_selected_source_images_head(self): # copy selected images from source to head of target
        # find last selected target image
        self.drag_started_in = "source" # must be set for the following functions
        # unselect all, otherwise update target canvas will append the list to last selected instead of front of canvas
        c = self.unselect_all(self.dict_target_images, self.target_canvas)
        self.file_at_dragposition = self.find_last_selected_target_image(self.list_target_images) # will return empty string
        target_rect = []
        changed = self.update_target_canvas(None, self.dict_source_images, target_rect, pt.COPY_SELECTED_HEAD)
        if changed or c: # if selection or canvas changed
            self.historize_process("copy selected source images HEAD")        
    def copy_selected_source_images_tail(self): # copy selected images from source to tail of target
        # find last selected target image
        self.drag_started_in = "source" # must be set for the following functions
        # unselect all, we dont want old images selected after copying new from source
        c = self.unselect_all(self.dict_target_images, self.target_canvas)
        self.file_at_dragposition = self.find_last_selected_target_image(self.list_target_images) # will return empty string
        target_rect = []
        changed = self.update_target_canvas(None, self.dict_source_images, target_rect, pt.COPY_SELECTED_TAIL)
        if changed or c: # if selection or canvas changed
            self.historize_process("copy selected source images TAIL")        
    def copy_single_source_image(self): # copy image under context menuitem select... from source to target
        # find last selected target image
        self.drag_started_in = "source" # must be set for the following functions
        self.file_at_dragposition = self.find_last_selected_target_image(self.list_target_images)
        target_rect = self.get_root_coordinates_for_widget(self.target_canvas)
        # save filenames as update will reset them to None
        if self.single_image_to_copy:
            sourcefile = self.single_image_to_copy.get_filename()
        else:
            sourcefile = "no source selected"
        if self.file_at_dragposition:
            targetfile = self.file_at_dragposition
        else:
            targetfile = "no target selected"
        #print("sourcefile: " + sourcefile + " targetfile: " + targetfile)
        changed = self.update_target_canvas(None, self.dict_source_images, target_rect, pt.COPY_SINGLE)
        if changed:
            self.historize_process("copy selected source image {:s} next to {:s}".format(sourcefile, targetfile))        
    def delete_selected_target_images(self): # delete selected images from target
        self.delete_target_canvas(self.dict_target_images, pt.DELETE_SELECTED)
        self.historize_process("delete selected target images")        
    def delete_single_target_image(self): # delete image under context menuitem delete... from target
        temp_filename = self.single_image_to_delete.get_filename() # because  the following delete sets filename to None
        self.delete_target_canvas(self.dict_target_images, pt.DELETE_SINGLE)
        self.historize_process("delete target image {:s}".format(temp_filename))        

    def fs_button(self, canvas_type, thumbnail, state, image):
        # this function is called if FSImage Exclude Button is pressed.
        # find out whether thumbnail belongs to source or target
        filename = image.get_filename()
        print("Diatisch.fs_button, type is {:s} state = {:d}, imagefile is {:s}".format(canvas_type, state, filename)) if self.debug else True
        if canvas_type == "Source": # copy Image and close
            self.single_image_to_copy = image
            self.copy_single_source_image()
            if filename in self.dict_file_FSImage_source:
                Globals.eventManager.generate(
                    "ClosingEvent",
                    ClosingEvent("", self) # file, self, see tools
                )
                self.dict_file_FSImage_source.pop(filename)
        elif canvas_type == "Target": # delete Image and close
            self.single_image_to_delete = image
            self.delete_single_target_image()
            if filename in self.dict_file_FSImage_target:
                Globals.eventManager.generate(
                    "ClosingEvent",
                    ClosingEvent("", self) # file, self, see tools
                )
                self.dict_file_FSImage_target.pop(filename)

    def fs_close(self, canvas_type, thumbnail, state, image):
        # this function is called if FSImage Exclude Button is pressed.
        # find out whether thumbnail belongs to source or target
        filename = image.get_filename()
        message = "Diatisch.fs_close, type is {:s} state = {:d}, imagefile is {:s}".format(canvas_type, state, filename)
        print(message) if self.debug else True
        self.historize_process(message)
        #if state == FS.EXCLUDE:
        if 0 == 1:
            if messagebox.askyesnocancel("Delete", "Delete image {:s}?".format(filename)) == True:
                print("delete") if self.debug else True
                self.single_image_to_delete = image
                self.delete_single_target_image()
            else:
                print("don't delete") if self.debug else True
    def find_last_selected_target_image(self, list_images): # helper function for finding last selected target (as insert point for copy)
        # find last selected target image
        ii = 0
        filename_of_last_selected = ""
        index = -1 # index of selected Image, the last will and shall win
        for i in list_images:
            if i.is_selected():
                filename_of_last_selected = i.get_filename()
                print("find selected target images, is_selected: ", filename_of_last_selected) if self.debug else True
                index = ii
            ii += 1
        print("find selected target images, index of last selected = ", str(index)) if self.debug else True
        return filename_of_last_selected

    def drop(self, event):
        # check if mouse is on target canvas
        #print("Drop") if self.debug else True
        # finish scrolling when button released - of course onla when scrolling
        self.scroll = False
        target_rect = self.get_root_coordinates_for_widget(self.target_canvas)
        source_rect = self.get_root_coordinates_for_widget(self.source_canvas)
        #print("Target rect is: ", str(target_rect)) if self.debug else True
        self.image_release = None
        changed = False
        if (self.check_event_in_rect(event, target_rect)): # there could be image(s) to drag
            print("*** Drop Event in target_canvas") if self.debug else True
            print ("Drop event: ", " x_root: ", str(event.x_root), " y_root: ", str(event.y_root), " x: ", str(event.x), " y: ", str(event.y)) if self.debug else True
            print ("Target canvasx: ", str(self.target_canvas.canvasx(event.x)), "canvasy: ", str(self.target_canvas.canvasy(event.y))) if self.debug else True
            img_closest_id, dist_event_left, dist_event_right = self.find_closest_item(event, target_rect, self.target_canvas, self.dict_target_images)
            if img_closest_id > 0:
                self.image_release = self.dict_target_images[img_closest_id]
                print("image found in target canvas, action = RELEASE: ", self.image_release.get_filename()) if self.debug else True
            if self.drag_started_in == "source": # drop images from source
                #for t in self.list_target_images:
                #    print("Before Target image: ", t.get_filename()) if self.debug else True
                # fill list of dragged images by checking if selected
                changed = self.update_target_canvas(event, self.dict_source_images, target_rect, pt.DROP_FROM_SOURCE)
            elif self.drag_started_in == "target": # move images within target
                # unselect image if it was selected and drop event is on saved image clicked (self.image_clicked)
                self.selection(event, self.target_canvas, self.dict_target_images, action.RELEASE) 
                print("canvas_target_rebuild_required = ", str(self.canvas_target_rebuild_required)) if self.debug else True
                if self.canvas_target_rebuild_required:
                    changed = self.update_target_canvas(event, self.dict_target_images, target_rect, pt.DROP_FROM_TARGET)
            else: # do nothing
                print("no image found in source canvas, action = RELEASE") if self.debug else True
                
            print("Drag Done.") if self.debug else True
            self.target_canvas.focus_set()
            self.target_canvas.bind('<Return>', self.canvas_focus_target)    # show FSImage for selected image
               
        elif (self.check_event_in_rect(event, source_rect)): # finish drag and drop mode
            print("Drop Event in source") if self.debug else True
            img_closest_id, dist_event_left, dist_event_right = self.find_closest_item(event, source_rect, self.source_canvas, self.dict_source_images)
            if img_closest_id > 0:
                self.image_release = self.dict_source_images[img_closest_id]
                print("image found in source canvas, action = RELEASE: ", self.image_release.get_filename()) if self.debug else True
                self.selection(event, self.source_canvas, self.dict_source_images, action.RELEASE)
            else: # do nothing
                print("no image found in source canvas, action = PRESS") if self.debug else True
            self.source_canvas.focus_set()
            self.source_canvas.bind('<Return>', self.canvas_focus_source)    # show FSImage for selected image
                
        else:
            print("Drop-Event not in target canvas") if self.debug else True

        if  changed or self.selection_changed: 
            self.historize_process("drop changed = {:s}, selectionchanged = {:s}".format('True' if changed else 'False', 'True' if self.selection_changed else 'False'))
        self.drag_started_in = ""

    def update_target_canvas(self, event, dict_images, target_rect, proctype):
        old_list_target_filenames = [] # for checking if list is changed
        new_list_target_filenames = [] # for checking if list is changed
        for i in self.list_target_images:
            old_list_target_filenames.append(i.get_filename()) 
        changed = False  # init to false
        print ("PROCTYPE is {:s}".format(str(proctype))) if self.debug else True
            
        # we want to know if filename of dragged images from source_canvas already exist. If so we don't want to drag them
        # may be in the future we will allow this but we have to rename them because Diatisch relies on uniqueness of filenames
        set_target_filenames = set() # create an empty set
        set_target_filenames.clear()
        if proctype == pt.DROP_FROM_SOURCE or proctype == pt.COPY_SELECTED or proctype == pt.COPY_SELECTED_HEAD or proctype == pt.COPY_SELECTED_TAIL or proctype == pt.COPY_SINGLE:
            for i in self.list_target_images:
                set_target_filenames.add(i.get_filename())

        list_dragged_images = []
        if proctype == pt.DROP_FROM_SOURCE or proctype == pt.COPY_SELECTED or proctype == pt.COPY_SELECTED_HEAD or proctype == pt.COPY_SELECTED_TAIL:
            for i in dict_images:
                img = dict_images[i]
                if img.is_selected():
                    if img.get_filename() not in set_target_filenames: # skip if already exists
                        newcopy = MyImage(img.get_filename(), img.get_mts(), self.target_canvas, img.get_tag()) # make a copy of the original source image because we need some independent attributes like selected 
                        newcopy.selected = img.selected
                        t = newcopy
                        #print("new image", " orig: ", str(img), " copy: ", str(t), " selected: ", str(t.is_selected())) if self.debug else True
                        list_dragged_images.append(t)
                        print("appended to list_dragged_images: ", t.get_filename(), " selected: ", str(t.is_selected())) if self.debug else True
                    else:
                        print("Dragged image: ", img.get_filename(), " skipped because it already exists") if self.debug else True
        elif proctype == pt.DROP_FROM_TARGET:
            for i in dict_images:
                img = dict_images[i]
                if img.is_selected():
                    if img.get_filename() not in set_target_filenames: # skip if already exists
                        t = img
                        list_dragged_images.append(t)
                        print("appended to list_dragged_images: ", t.get_filename(), " selected: ", str(t.is_selected())) if self.debug else True
                    else:
                        print("Dragged image: ", img.get_filename(), " skipped because it already exists") if self.debug else True
        elif proctype == pt.COPY_SINGLE:
            if self.single_image_to_copy is None:
                messagebox.showerror(str(proctype), "Internal error single image to copy is None.", parent = self.root)
                return
            img = self.single_image_to_copy
            if img.get_filename() not in set_target_filenames: # skip if already exists
                newcopy = MyImage(img.get_filename(), img.get_mts(), self.target_canvas, img.get_tag()) # make a copy of the original source image because we need some independent attributes like selected 
                newcopy.selected = img.selected
                t = newcopy
                #print("new image", " orig: ", str(img), " copy: ", str(t), " selected: ", str(t.is_selected())) if self.debug else True
                list_dragged_images.append(t)
                print("appended to list_dragged_images: ", t.get_filename(), " selected: ", str(t.is_selected())) if self.debug else True
            else:
                print("Dragged image: ", img.get_filename(), " skipped because it already exists") if self.debug else True
            self.single_image_to_copy = None # reset because update_target_canvas checks if None

        if list_dragged_images:# true when not empty
            
            dragpos = dragposition.BEFORE
            set_dragged_filenames = set() # create an empty set
            no_target_image = False
            if event is not None: # event from mouse release
                # get id, distances of image under drop event
                img_closest_id, dist_event_left, dist_event_right = self.find_closest_item(event, target_rect, self.target_canvas, self.dict_target_images)
                if img_closest_id > 0:
                    img_closest = self.dict_target_images[img_closest_id]
                    file_at_dragposition = img_closest.get_filename()
                    if dist_event_left > dist_event_right:
                        dragpos = dragposition.BEHIND # insert BEHIND hit image
                    print("closest Target Image has ID: ", img_closest_id, " Filename: " + file_at_dragposition, \
                    " dist left: ", str(dist_event_left), " dist right: ", str(dist_event_right), " dragposition: ", str(dragpos)) if self.debug else True
                else: # no closest image, append dragged images to existing list
                    print("No closest Target") if self.debug else True
                    no_target_image = True
                    dragpos = dragposition.BEHIND
            else: # no event, call is from copy_selected_source_images(Button copy selected) or ...HEAD
                file_at_dragposition = self.file_at_dragposition
                if file_at_dragposition == "": # no target image selected, append
                    no_target_image = True
                dragpos = dragposition.BEHIND

            # now insert list of dragged images in target list, before or behind file_at_dragposition
            for i in self.list_target_images:
                print("Before Target Image: ", i.get_filename(), " In list_dragged_images: ", str(i in list_dragged_images), " selected: ", str(i.is_selected())) if self.debug else True
            list_dragged_images.sort(key=lambda a: int(a.selected))
            #print("list dragged images: " + str(list_dragged_images)) if self.debug else True
            # we need a SET of dragged filenames
            set_dragged_filenames.clear()
            for i in list_dragged_images:
                set_dragged_filenames.add(i.get_filename())
            # insert dragged images into list_target_images
            # we iterate over list_target_images
            #   if filename in list_dragged_images: next(we don't want it twice)
            #   else if filename = file_at_dragposition
            #     if dragpos = BEFORE, insert list_dragged_images, insert filename
            #     else: insert filename, insert list_dragged_images
            #   else insert filename
            if self.list_target_images == []: #initial drag from source
                for i in list_dragged_images:
                    self.list_target_images.append(i)
            elif no_target_image: # no target image selected, copy HEAD or TAIL
                list_temp = []
                if proctype == pt.COPY_SELECTED_TAIL: # existing target images followed by copied images
                    for i in self.list_target_images:
                        thisfile = i.get_filename()
                        if thisfile not in set_dragged_filenames:
                            list_temp.append(i)
                    for j in list_dragged_images:
                        list_temp.append(j)
                elif proctype == pt.COPY_SELECTED_HEAD: # copied images followed by target images
                    for i in list_dragged_images:
                        thisfile = i.get_filename()
                        if thisfile not in self.list_target_images:
                            list_temp.append(i)
                    for i in self.list_target_images:
                        list_temp.append(i) # works because existing target files have not been inserted in result
                else: # same as COPY TAIL
                    for i in self.list_target_images:
                        thisfile = i.get_filename()
                        if thisfile not in set_dragged_filenames:
                            list_temp.append(i)
                    for j in list_dragged_images:
                        list_temp.append(j)
                self.list_target_images = list_temp    
            else: # we have target image of which at least one is selected
                list_temp = []
                for i in self.list_target_images:
                    thisfile = i.get_filename()
                    if thisfile ==  file_at_dragposition:
                        if dragpos == dragposition.BEFORE:
                            for j in list_dragged_images:
                                list_temp.append(j)
                            if thisfile not in set_dragged_filenames:
                                list_temp.append(i)
                        else: # dragposition.BEHIND
                            if thisfile not in set_dragged_filenames:
                                list_temp.append(i)
                            for j in list_dragged_images:
                                list_temp.append(j)
                    elif thisfile not in set_dragged_filenames: # skip if in set_dragged_filenames
                        list_temp.append(i)
                
                self.list_target_images = list_temp
            #print("list_target_images: ", str(self.list_target_images)) if self.debug else True
            # rebuild target canvas, refresh dicts
            for i in self.list_target_images:
                new_list_target_filenames.append(i.get_filename()) 
            changed = self.lists_equal(new_list_target_filenames, old_list_target_filenames)
            if changed:
                self.dict_target_images = self.display_image_objects(self.list_target_images, self.target_canvas, self.Label_target_ctr)
                #for t in self.dict_target_images:
                #    print("dict_target_images id: ", t, " Filename: ", self.dict_target_images[t].get_filename()) if self.debug else True
                # now select all dragged images
                ii = 0
                for i in self.list_target_images:
                    # for convenience we select all dragged images and unselect all others
                    thisfile = i.get_filename()
                    print("After Target Image: ", thisfile, " In list_dragged_images: ", str(i in list_dragged_images), " sected: ", str(i.is_selected())) if self.debug else True
                    if thisfile in set_dragged_filenames: # select
                        self.select_image(i, self.target_canvas)
                        print("thisfile: ", thisfile, " sected: ", str(i.is_selected()), " select_ctr: ", str(self.target_canvas.select_ctr)) if self.debug else True
                    else:
                        self.unselect_image(i, self.target_canvas)
                    ii += 1
            else:
                print ("list target images has not changed") if self.debug else True
                #print("list old: ", str(old_list_target_filenames)) if self.debug else True
                #print("list new: ", str(new_list_target_filenames)) if self.debug else True
        self.file_at_dragposition = ""
        if len(self.list_target_images) > 0: # anz target images > 0    
            self.button_exec.config(state = tk.NORMAL)        
        return changed # o historization if false

    def delete_target_canvas(self, dict_images, proctype):
        # delete 1 single or all selected Images from target_canvas
        self.list_target_images = [] 
        list_FSImages_to_delete = []
        for i in dict_images:
            img = dict_images[i]
            if proctype == pt.DELETE_SELECTED: # we insert all images which are not selected (because we wish to delete all which are selected)
                if not img.is_selected():
                    self.list_target_images.append(img)
                else: # we keep track of images to delete, for those we will later FSImage (if existing)
                    list_FSImages_to_delete.append(img.get_filename())
            elif proctype == pt.DELETE_SINGLE: # we insert all images which are not image_to_delete (because we wish to delete all which are selected)
                if self.single_image_to_delete is None:
                    messagebox.showerror(str(proctype), "Internal error single image to delete is None.", parent = self.root)
                    return
                if img.get_filename() != self.single_image_to_delete.get_filename():
                    self.list_target_images.append(img)
                else: # we keep track of images to delete, for those we will later FSImage (if existing)
                    list_FSImages_to_delete.append(img.get_filename())
        # rebuild target canvas, refresh dicts
        self.dict_target_images = self.display_image_objects(self.list_target_images, self.target_canvas, self.Label_target_ctr)
        # now select / unselect, remember: display image objects always shows selecttion frame because it is drawn last!
        for i in self.list_target_images:
            # we selected all images which were selected before the delete action and unselect the others
            if i.is_selected(): # select
                self.select_image(i, self.target_canvas)
            else:
                self.unselect_image(i, self.target_canvas)
                
        # now delete FSImages if existing
        print(str(self.dict_file_FSImage_target)) if self.debug else True
        print(str(list_FSImages_to_delete)) if self.debug else True
        for filename in list_FSImages_to_delete:
            if filename in self.dict_file_FSImage_target:
                self.dict_file_FSImage_target[filename].thumbnail.fs_close = None # otherwise fs_close would historize close for each FSImage, which is only necessary if user closes the window 
                Globals.eventManager.generate(
                    "ClosingEvent",
                    ClosingEvent("", self) # file, self, see tools
                )
                self.dict_file_FSImage_target.pop(filename)
        
        # reset to none
        self.single_image_to_delete = None

    def lists_equal(self, l1, l2):
        changed = False
        if len(l1) != len(l2):
            changed = True
        else:
            length = len(l1)
            for i in range(length):
                if l1[i] != l2[i]:
                    changed = True
                    break
        return changed

    def find_closest_item(self, event, rect_canvas, canvas, dict_images):
        # this is necessary because tkinter find_closest does not work for drop event, reason unknown
        id = 0
        event_x_pos_in_canvas = event.x_root - rect_canvas[0]
        event_y_pos_in_canvas = event.y_root - rect_canvas[1]
        #print ("event_x_pos_in_canvas is: ", str(event_x_pos_in_canvas), '/', str(event_y_pos_in_canvas)) if self.debug else True
        if canvas.bbox("all") is not None:
            canvas_width  = canvas.bbox("all")[2] - canvas.bbox("all")[0]
            canvas_height = canvas.bbox("all")[3] - canvas.bbox("all")[1]
        else:
            canvas_width  = 0
            canvas_height = 0
        current_scroll_x = canvas.xview()[0] * canvas_width
        current_scroll_y = canvas.yview()[0] * canvas_height
        print("Scroll position x is: ", str(canvas.xview()), " width is: ", str(canvas_width), " xpos: ", str(current_scroll_x)) if self.debug else True
        print("Scroll position y is: ", str(canvas.yview()), " height is: ", str(canvas_height), " ypos: ", str(current_scroll_y)) if self.debug else True
        hit = False
        dist_event_left = 0
        dist_event_right = 0
        for id in dict_images:
            #print("Dict Id: ", id, " BBOX: ", str(canvas.bbox(id))) if self.debug else True
            pos_border_left   = canvas.bbox(id)[0] - current_scroll_x
            pos_border_right  = canvas.bbox(id)[2] - current_scroll_x
            pos_border_top    = canvas.bbox(id)[1] - current_scroll_y
            pos_border_bottom = canvas.bbox(id)[3] - current_scroll_y
            if pos_border_left <= event_x_pos_in_canvas <= pos_border_right and pos_border_top <= event_y_pos_in_canvas <= pos_border_bottom:
                #print("Hit!") if self.debug else True
                hit = True
                # distance to left / right border of image:
                dist_event_left  = event_x_pos_in_canvas - pos_border_left
                dist_event_right = pos_border_right - event_x_pos_in_canvas
                break
        if not hit:
            id = 0
        
        return id, dist_event_left, dist_event_right

    def select_all_source_images(self):
        print("select_all_source_images Pressed") if self.debug else True
        changed = self.select_all(self.list_source_images, self.source_canvas)
        if changed:
            self.historize_process("select all source images")

    def delete_selected(self):
        #print("Delete Selected Pressed") if self.debug else True
        self.delete_selected_target_images()

    def unselect_all(self, dict_images, canvas):
        changed = False
        for i in dict_images:
            image = dict_images[i]
            #print("Unselect: ", str(image.get_filename())) if self.debug else True
            c = image.unselect(canvas)
            changed = self.check_changed(changed, c)
        #reset counter
        canvas.select_ctr = 0
        return changed
    
    def select_all(self, list_images, canvas):
        changed = False
        for i in list_images:
            if not i.is_selected():
                canvas.select_ctr += 1
                c = i.select(canvas, canvas.select_ctr)
                changed = self.check_changed(changed, c)
        return changed

    def select_image(self, image, canvas):
        changed = False
        if not image.is_selected():
            canvas.select_ctr += 1
            print ("--- SELECT CALL") if self.debug else True
            changed = image.select(canvas, canvas.select_ctr)
        return changed

    def toggle_selection(self, image, canvas):
        if image.is_selected():
            image.unselect(canvas)
        else: 
            canvas.select_ctr += 1
            image.select(canvas, canvas.select_ctr)

    def unselect_image(self, image, canvas):
        changed = False
        changed = image.unselect(canvas)
        return changed

    def get_num_selected(self, list_images):
        num_selected = 0
        for i in list_images:
            if i.is_selected():
                num_selected += 1
        return num_selected
        
    def get_root_coordinates_for_widget(self, widget):
        # return rect of widget-coordinates relative to root window
        x1 = widget.winfo_rootx() 
        x2 = x1 + widget.winfo_width()
        y1 = widget.winfo_rooty()
        y2 = y1 + widget.winfo_height()
        return [x1, y1, x2, y2]

    def check_event_in_rect(self, event, rect): # rect has to be qualified relative to root!
        # check if event is within rect
        if (event.x_root >= rect[0] and event.x_root <= rect[2] and event.y_root >= rect[1] and event.y_root <= rect[3]):
            return True
        else:
            return False

    def display_image_objects(self, list_obj, canvas, label_ctr): # display list of images on canvas, use already converted photos in objects, better performance
        xpos = 0
        ypos = 0
        row  = 0
        col  = 0
        ctr  = 0
        canvas.delete("all")
        dict_images = {}
        for i in list_obj:
            filename = i.get_filename()
            #print("try to show image: " , filename) if self.debug else True
            photo = i.get_image()
            img_id = canvas.create_image(xpos, ypos, anchor='nw', image = photo, tags = 'images')
            display_width, display_height = photo.width(), photo.height()
            # draw rect consisting of 4 dotted lines because create rectagle does not support dotted lines
            north_west = (xpos + self.dist_frame, ypos + self.dist_frame)
            north_east = (xpos + display_width - self.dist_frame, ypos + self.dist_frame)
            south_west = (xpos + self.dist_frame, ypos + display_height - self.dist_frame)
            south_east = (xpos + display_width - self.dist_frame, ypos + display_height - self.dist_frame)
            line_north = canvas.create_line(north_west, north_east, dash=(1, 1), fill = Diatisch.line_color, width = Diatisch.line_width, tags=i.get_tag())
            line_east  = canvas.create_line(north_east, south_east, dash=(1, 1), fill = Diatisch.line_color, width = Diatisch.line_width, tags=i.get_tag())
            line_south = canvas.create_line(south_west, south_east, dash=(1, 1), fill = Diatisch.line_color, width = Diatisch.line_width, tags=i.get_tag())
            line_west  = canvas.create_line(north_west, south_west, dash=(1, 1), fill = Diatisch.line_color, width = Diatisch.line_width, tags=i.get_tag())
            dict_images[img_id] = i
            #print("   Insert into dict key: ", str(img_id), " filename: " , obj.get_filename()) if self.debug else True
            ctr += 1
            xpos += display_width
            col += 1
            if col >= self.n:
                col = 0
                row += 1
                xpos = 0
                ypos += self.row_height
        canvas.update()
        canvas.configure(scrollregion=canvas.bbox("all"))
        #for t in dict_images:
        #    f = dict_images[t].get_filename() 
        #    print("    dict_images id: ", str(t), " filename: " , f) if self.debug else True
        labeltext = label_ctr.cget('text')
        labeltext = re.sub(r"\d+$", f"{str(ctr)}", labeltext)
        label_ctr.config(text = labeltext)
        self.ctr_targetfiles = ctr
        self.endis_menu_items()
        return dict_images

    # ----------------------------------------------------------------------
    # 20261112: event handler for closing event
    # ----------------------------------------------------------------------
    def on_closing(self, event): #if a FS exists in dict_file_FSImage_* delete entry
        # the FSImage may show another file than the key (companion JPEG), so we look for the object
        for d in (self.dict_file_FSImage_source, self.dict_file_FSImage_target):
            for k in [k for k, v in d.items() if v is event.obj]: # has been created by us, not by someone else
                del d[k]

    # Undo /Redo functions
    def process_undo(self, event):
        print("ctrl_z pressed.") if self.debug else True
        rc, p_now, p_before = self.UR.process_undo()
        if not rc: # undo was not possible
            messagebox.showinfo("UNDO", "no further processes which can be undone", parent = self.root)
        else:
            self.apply_process_id(p_now, p_before)
            self.endis_buttons()
            # show list/ stack after undo redo if open
            self.win_processlist.update_listbox_process_list(self.dict_processid_histobj, self.UR.list_processids) if self.win_processlist else True
            self.win_processlist.update_listbox_process_undo(self.dict_processid_histobj, self.UR.stack_processids) if self.win_processlist else True

    def process_redo(self, event):
        print("ctrl_y pressed.") if self.debug else True
        rc, p_now, p_before = self.UR.process_redo()
        if not rc:
            messagebox.showinfo("REDO", "no further processes which can be redone", parent = self.root)
        else:
            self.apply_process_id(p_now, p_before)
            self.endis_buttons()
            # show list/ stack after undo redo if open
            self.win_processlist.update_listbox_process_list(self.dict_processid_histobj, self.UR.list_processids) if self.win_processlist else True
            self.win_processlist.update_listbox_process_undo(self.dict_processid_histobj, self.UR.stack_processids) if self.win_processlist else True

    def button_undo_h(self, event = None):
        print("Button Undo pressed") if self.debug else True
        self.process_undo(event)
        
    def button_redo_h(self, event = None):
        print("Button Redo pressed") if self.debug else True
        self.process_redo(event)

    def endis_buttons(self): # disable / enable buttons depending on processids
        rc_undo, rc_redo = self.UR.endis_buttons()
        if rc_undo:
            self.button_undo.config(state = NORMAL)
        else:
            self.button_undo.config(state = DISABLED)
        if rc_redo:
            self.button_redo.config(state = NORMAL)
        else:
            self.button_redo.config(state = DISABLED)


    def apply_process_id(self, process_id, processid_predecessor):
        print("apply process_id, id to apply is: ", str(process_id), " processid was: ", str(processid_predecessor)) if self.debug_p else True
        
        h = self.dict_processid_histobj[process_id]
        Diatisch.idx_akt = h.idx_akt            
        list_obj_source = h.list_source_images
        list_obj_target = h.list_target_images
        source_new = False
        target_new = False
        if h.str_hashsum_source_filenames != self.dict_processid_histobj[processid_predecessor].str_hashsum_source_filenames:
            # rebuild list of source images
            self.list_source_images = []
            self.dict_source_images = {}
            for i in list_obj_source:
                self.list_source_images.append(i)
            self.dict_source_images = self.display_image_objects(self.list_source_images, self.source_canvas, self.Label_source_ctr)
            source_new = True
 
        if h.str_hashsum_target_filenames != self.dict_processid_histobj[processid_predecessor].str_hashsum_target_filenames:
            # rebuild list of target images
            self.list_target_images = []
            self.dict_target_images = {}
            for i in list_obj_target:
                self.list_target_images.append(i)
            self.dict_target_images = self.display_image_objects(self.list_target_images, self.target_canvas, self.Label_target_ctr)
            target_new = True

        # restore the select counters for sequence of selection
        self.source_canvas.select_ctr = h.source_select_ctr
        self.target_canvas.select_ctr = h.target_select_ctr
        # apply selection if canvas has changed or hashsums for selection are not equal
        if source_new or h.str_hashsum_source_selection != self.dict_processid_histobj[processid_predecessor].str_hashsum_source_selection:
            # list_obj and self.list_source_images have same structure, so we can use an index to access the elements of self.list_source_images
            ii = 0
            for i in list_obj_source:
                # print("* H SOURCE Filename / select_ctr / selected / tag: ", i.filename, ' / ' , i.selected, ' / ', str(i.is_selected()), ' / ', i.tag) if self.debug else True
                if i.is_selected():
                    self.list_source_images[ii].select(self.source_canvas, i.get_ctr())
                else:
                    self.list_source_images[ii].unselect(self.source_canvas)
                ii += 1
        if target_new or h.str_hashsum_target_selection != self.dict_processid_histobj[processid_predecessor].str_hashsum_target_selection:
            # list_obj and self.list_target_images have same structure, so we can use an index to access the elements of self.list_source_images
            ii = 0
            for i in list_obj_target:
                #print("* H TARGET Filename / select_ctr / selected / tag: ", i.filename, ' / ' , i.selected, ' / ', str(i.is_selected()), ' / ', i.tag) if self.debug else True
                if i.is_selected():
                    self.list_target_images[ii].select(self.target_canvas, i.get_ctr())
                else:
                    self.list_target_images[ii].unselect(self.target_canvas)
                ii += 1
        labeltext = self.Label_process_id.cget('text')
        labeltext = re.sub(r"\d+$", f"{str(process_id)}", labeltext) # replace num by processid
        self.Label_process_id.config(text = labeltext)
        if h.str_hashsum_file_thumbnail_source != self.dict_processid_histobj[processid_predecessor].str_hashsum_file_thumbnail_source: # rebuild FSImages Source
            print("restore FSImages") if self.debug else True
            # delete all FSImages currently open
            for i in self.dict_file_FSImage_source:
                fsimage = self.dict_file_FSImage_source[i]
                fsimage.thumbnail.fs_close = None # otherwise fs_close would historize close for each FSImage, which is only necessary if user closes the window 
                # 20261112 generate closing event, FS-Childs will close themselves
                Globals.eventManager.generate(
                    "Closing",
                    ClosingEvent("", self) # file, self, see tools
                )
            self.dict_file_FSImage_source = {}
            # create FSImage and insert into dict
            for i in h.dict_file_thumbnail_source:
                img = h.dict_file_thumbnail_source[i].image
                fs_image = self.create_fsimage("Source", img, i)
                self.dict_file_FSImage_source[i] = fs_image
        if h.str_hashsum_file_thumbnail_target != self.dict_processid_histobj[processid_predecessor].str_hashsum_file_thumbnail_target: # rebuild FSImages target
            print("restore FSImages") if self.debug else True
            # delete all FSImages currently open
            for i in self.dict_file_FSImage_target:
                fsimage = self.dict_file_FSImage_target[i]
                fsimage.thumbnail.fs_close = None # otherwise fs_close would historize close for each FSImage, which is only necessary if user closes the window 
                # 20261112 generate closing event, FS-Childs will close themselves
                Globals.eventManager.generate(
                    "Closing",
                    ClosingEvent("", self) # file, self, see tools
                )
            self.dict_file_FSImage_target = {}
            # create FSImage and insert into dict
            for i in h.dict_file_thumbnail_target:
                img = h.dict_file_thumbnail_target[i].image
                fs_image = self.create_fsimage("Target", img, i)
                self.dict_file_FSImage_target[i] = fs_image
                        
        
    def historize_process(self, text = None):
        h = HistObj()
        # for quick compare if lists of two historized states is equal we need the checksums
        hashsum_source_filenames = hashlib.md5()
        hashsum_target_filenames = hashlib.md5()
        hashsum_source_selection = hashlib.md5()
        hashsum_target_selection = hashlib.md5()
        str_source_selection = ""
        str_target_selection = ""
        # FSImages
        hashsum_file_FSImage_source = hashlib.md5()
        hashsum_file_FSImage_target = hashlib.md5()

        for i in self.list_source_images:
            #print("* H Filename / select_ctr / selected / tag: ", i.filename, ' / ' , i.selected, ' / ', str(i.is_selected()), ' / ', i.tag) if self.debug else True
            newcopy = MyImage(i.get_filename(), i.get_mts(), i.canvas, i.tag) # make a copy of the original source image because we need some independent attributes like selected 
            newcopy.selected = i.selected
            h.list_source_images.append(newcopy)
            hashsum_source_filenames.update(i.filename.encode(encoding = 'UTF-8', errors = 'strict'))
            str_source_selection += str(i.selected)
        for i in self.list_target_images:
            newcopy = MyImage(i.get_filename(), i.get_mts(), i.canvas, i.tag) # make a copy of the original source image because we need some independent attributes like selected 
            newcopy.selected = i.selected
            h.list_target_images.append(newcopy)
            hashsum_target_filenames.update(i.filename.encode(encoding = 'UTF-8', errors = 'strict'))
            str_target_selection += str(i.selected)
        #FSImages
        for i in self.dict_file_FSImage_source: # save copy
            img = self.dict_file_FSImage_source[i].thumbnail.image
            thumbnail = Thumbnail(img, i, None, self.source_canvas, self.debug, "Source", self.fs_close, self.fs_button)
            h.dict_file_thumbnail_source[i] = thumbnail
            hashsum_file_FSImage_source.update(i.encode(encoding = 'UTF-8', errors = 'strict'))
        for i in self.dict_file_FSImage_target: # save copy
            img = self.dict_file_FSImage_target[i].thumbnail.image
            thumbnail = Thumbnail(img, i, None, self.target_canvas, self.debug, "Target", self.fs_close, self.fs_button)
            h.dict_file_thumbnail_target[i] = thumbnail
            hashsum_file_FSImage_target.update(i.encode(encoding = 'UTF-8', errors = 'strict'))
        
        h.source_select_ctr = self.source_canvas.select_ctr
        h.target_select_ctr = self.target_canvas.select_ctr
        
        # historize hashsums
        h.str_hashsum_source_filenames = hashsum_source_filenames.hexdigest()
        h.str_hashsum_target_filenames = hashsum_target_filenames.hexdigest()
        # FSImage
        h.str_hashsum_file_thumbnail_source = hashsum_file_FSImage_source.hexdigest()
        h.str_hashsum_file_thumbnail_target = hashsum_file_FSImage_target.hexdigest()

        hashsum_source_selection.update(str_source_selection.encode(encoding = 'UTF-8', errors = 'strict'))
        h.str_hashsum_source_selection = hashsum_source_selection.hexdigest()
        hashsum_target_selection.update(str_target_selection.encode(encoding = 'UTF-8', errors = 'strict'))
        h.str_hashsum_target_selection = hashsum_target_selection.hexdigest()
        #print("Hashsum source Filenames is: ", h.str_hashsum_source_filenames, " Hashsum target Filenames is: ", h.str_hashsum_target_filenames) if self.debug else True
        #print("Hashsum source Selection is: ", h.str_hashsum_source_selection, "(", str_source_selection, ")", " Hashsum target Selection is: ", h.str_hashsum_target_selection, "(", str_target_selection, ")") if self.debug else True
        h.idx_akt = Diatisch.idx_akt
        
        self.UR.historize_process(text)
        self.dict_processid_histobj[self.UR.get_processid_akt()] = h
        self.endis_buttons()
        labeltext = self.Label_process_id.cget('text')
        labeltext = re.sub(r"\d+$", f"{str(self.UR.get_processid_akt())}", labeltext) # replace num by processid
        self.Label_process_id.config(text = labeltext)
        
        if text:
            h.text = text

        # update process window if open           
        self.win_processlist.update_listbox_process_hist(self.dict_processid_histobj) if self.win_processlist else True
        self.win_processlist.update_listbox_process_list(self.dict_processid_histobj, self.UR.list_processids) if self.win_processlist else True

    # Ende undo /redo-Funktionen


    def close_handler(self): #calles when window is closing
        print("Diatisch: call callback when window is closed") if self.debug else True
        if self.callback:
            for i in self.list_target_images:
                #print(i) if self.debug else True
                self.list_result.append(i.get_filename())
            self.callback()

        Globals.eventManager.unbind("PrintRequestEvent", self.handle_print_request)
        Globals.eventManager.unbind("CameraChangedEvent", self.handle_camera_changed)

        self.close_child_windows()
        self.root.destroy()

    def donothing(self):
        print("Menuitem not yet implemented") if self.debug else True
    def open_config(self):
        # get config_files for source / target images
        
        endung = 'xml'
        self.config_file = fd.askopenfilename(initialdir = os.path.join(self.datadir, self.config_files_subdir), filetypes=[("config files", endung)])
        self.configmenu.entryconfig(CFG_SAVE_CONFIG, state=NORMAL)
        self.root.title(self.title + ' ' + self.config_file)
        self.configmenu.entryconfig(CFG_SAVE_CONFIG_AS, state=NORMAL)

    def open_apply_config(self):
        # get config_files for source / target images
        
        endung = 'xml'
        self.config_file = fd.askopenfilename(initialdir = os.path.join(self.datadir, self.config_files_subdir), filetypes=[("config files", endung)])
        self.configmenu.entryconfig(CFG_SAVE_CONFIG, state=NORMAL)
        self.root.title(self.title + ' ' + self.config_file)
        self.configmenu.entryconfig(CFG_SAVE_CONFIG_AS, state=NORMAL)

    def save_config(self): # Config-xml speichern
        print("Config File is: " + self.config_file)
        if self.config_file != "":
            self.write_config(self.config_file)
            # update config-file-entry in xml. will automatically create new entry if type or infile does not exist
            #self.update_config_xml(self.config_file)
        else:
            self.saveas_config()

    def saveas_config(self): # Config-xml unter neuem Namen sichern
        endung = 'xml'
        self.config_file = fd.asksaveasfilename(initialdir = os.path.join(self.datadir, self.config_files_subdir), filetypes=[("config files", endung)])
        if (len(self.config_file) > 0):
            match = re.search(rf".*?{endung}$", self.config_file)
            if match:
                filename = self.config_file
            else:
                filename = self.config_file + '.' + endung
                self.config_file = filename
            self.write_config(filename)
            # update config-file-entry in xml. will automatically create new entry if type or infile does not exist
            #self.update_config_xml(self.config_file)
            
            self.root.title(self.title + ' ' + self.config_file)
            self.configmenu.entryconfig(CFG_SAVE_CONFIG, state=NORMAL) # Save
            self.configmenu.entryconfig(CFG_SAVE_CONFIG_AS, state=NORMAL) # Save As
            self.configmenu.entryconfig(CFG_OPEN_APPLY_CONFIG, state=NORMAL) # Apply config

    def write_config(self, filename): # Config-xml unter neuem Namen sichern
        file1 = open(filename, "w")
        ts = strftime("%Y%m%d-%H:%M:%S", time.localtime())
        ctr_source = 0
        ctr_target = 0
        
        s = '<?xml version="1.0" encoding="iso-8859-1"?>' + "\n"
        file1.write(s)
        
        # write node sourcefiles
        s = '<images time="' + ts + '">' + "\n"
        file1.write(s)
        s = '    <sourcefiles time="' + ts + '">' + "\n"
        file1.write(s)
        for i in self.list_source_images:
            name = re.sub(r"\\", "/", i.get_filename()) # replace single backslash by slash
            s = "        <sourcefile name=\"" + name + "\">\n"
            file1.write(s)
            s = "        </sourcefile>\n"
            file1.write(s)
            ctr_source += 1
        s = '    </sourcefiles>' + "\n"
        file1.write(s)
        
        # write node targetfiles
        s = '    <targetfiles time="' + ts + '">' + "\n"
        file1.write(s)
        for i in self.list_target_images:
            name = re.sub(r"\\", "/", i.get_filename()) # replace single backslash by slash
            s = "        <targetfile name=\"" + name + "\">\n"
            file1.write(s)
            s = "        </targetfile>\n"
            file1.write(s)
            ctr_target += 1
        s = '    </targetfiles>' + "\n"
        file1.write(s)

        s = '</images>' + "\n"
        file1.write(s)

        # Closing file
        file1.close()

        # delete cfgfile-entries from xml if number gt than max from ini, oldest and not existing first. we have to supply the necessary xml-information
        self.new_item_in_xml(self.max_configfiles, filename, ts, "config_files", "configfile", "filename")
        # create new xml-entry for file
        DX.new_cfgfile_diatisch(self.config_files_xml, filename, ts, ctr_source, ctr_target)
        # update listbox
        self.update_listbox_cfg()
        # the file was just written by us: cache knows it exists
        self.dirchk.cache[filename] = True

    def new_indir(self):
        # get dir from dir dialog, insert in xml, update listbox-indirs
        directory = fd.askdirectory()
        if not directory: # something went wrong
            messagebox.showerror("Open", "unable to open: " + directory, parent = self.root)
            return False

        ts = strftime("%Y%m%d-%H:%M:%S", time.localtime())
        this_i = re.sub(r'\\', '/', directory).lower()
        # delete indir-entries from xml if number gt than max from ini, oldest and not existing first. we have to supply the necessary xml-information
        self.new_item_in_xml(self.max_indirs, this_i, ts, "indirs", "indir", "name")
        # now create new indir
        DX.new_dir_diatisch(self.config_files_xml, "indirs", "indir", "name", this_i, ts)
        self.update_listbox_indir()    
        
    def new_outdir(self):
        # get dir from dir dialog, insert in xml, update listbox-outdirs
        directory = fd.askdirectory()
        if not directory: # something went wrong
            messagebox.showerror("Open", "unable to open: " + directory, parent = self.root)
            return False

        ts = strftime("%Y%m%d-%H:%M:%S", time.localtime())
        this_i = re.sub(r'\\', '/', directory).lower()
        # delete outdir-entries from xml if number gt than max from ini, oldest and not existing first. we have to supply the necessary xml-information
        self.new_item_in_xml(self.max_outdirs, this_i, ts, "outdirs", "outdir", "name")
        # now create new outdir
        DX.new_dir_diatisch(self.config_files_xml, "outdirs", "outdir", "name", this_i, ts)
        self.update_listbox_outdir()    
    
    
    def donothing(self):
        print("Menuitem not yet implemented") if self.debug else True

    def apply_config(self):
        print("Menuitem not yet implemented") if self.debug else True

    def endis_menu_items(self):
        self.configmenu.entryconfig(CFG_NEW,               state=DISABLED)
        self.configmenu.entryconfig(CFG_OPEN_CONFIG,       state=NORMAL)
        self.configmenu.entryconfig(CFG_OPEN_APPLY_CONFIG, state=NORMAL)
        self.configmenu.entryconfig(CFG_SAVE_CONFIG,       state=DISABLED)
        self.configmenu.entryconfig(CFG_SAVE_CONFIG_AS,    state=DISABLED)
        self.configmenu.entryconfig(CFG_APPLY_CONFIG,      state=DISABLED)
        self.configmenu.entryconfig(CFG_OPEN_RECENT,       state=NORMAL)
        
        if self.config_file != "": # a config file has been opened
            self.configmenu.entryconfig(CFG_APPLY_CONFIG,      state=NORMAL)
        if self.ctr_targetfiles > 0:    
            self.configmenu.entryconfig(CFG_SAVE_CONFIG,       state=NORMAL)
            self.configmenu.entryconfig(CFG_SAVE_CONFIG_AS,    state=NORMAL)
        
    def button_exec_pressed(self):
        # gen cmd files and write to dir            
        # get outdir from listbox
        selected_indices = self.listbox_outdir.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Listbox Outdir: nothing selected", parent = self.Frame_outdir)
        else:
            outdir = ",".join([self.listbox_outdir.get(i) for i in selected_indices]) # because listbox has single selection
            print("outdir selected is: " + outdir) if self.debug else True
            self.outdir = outdir

            self.write_cmdfile(self.outdir)
            # show exec window
            if self.win_exec is not None: # stop MyExecWindow-Objekt
                self.win_exec.close_handler()
                self.win_exec = None
            self.win_exec = DM.MyExecWindow(self, self.datadir, self.cmd_files_subdir, self.imagetype, self.dict_gen_filenames["COPY"], self.dict_gen_filenames["DELETE"], None) 

    def button_processlist_pressed(self):
        # show process window            
        if self.win_processlist is not None: # stop Window-Objekt
            self.win_processlist.close_handler()
            self.win_processlist = None
        self.win_processlist = DP.MyProcesslistWindow(self.processlist_close, self.processlist_display, self.dict_processid_histobj, self.debug, self.debug_p)
        self.win_processlist.update_listbox_process_hist(self.dict_processid_histobj)
        self.win_processlist.update_listbox_process_list(self.dict_processid_histobj, self.UR.list_processids) if self.win_processlist else True
        self.win_processlist.update_listbox_process_undo(self.dict_processid_histobj, self.UR.stack_processids) if self.win_processlist else True
        
    def processlist_close(self):
        self.win_processlist = None

    def processlist_display(self, process_id, infotext):
        print("called by processlist window, action: {:s} processid selected is: {:d}, actual processid is: {:d}".format(infotext, process_id, self.UR.get_processid_akt())) if self.debug_p else True
        if process_id != self.processid_displayed:
            self.apply_process_id(process_id, self.processid_displayed)
            self.processid_displayed = process_id

    def write_cmdfile(self, outdir):
        ts = strftime("%Y%m%d-%H:%M:%S", time.localtime())
        header = self.uncomment + ' generated by diatisch / dateimeister ' + ts + '\n'

        # process only files contained in list_target_images
        for ii in self.dict_templates:
            template    = self.dict_templates[ii]
            cmd_file_full = self.dict_gen_filenames[ii] # uses same key as both are filled in init
            thiscmdfile = open(cmd_file_full, 'w')
            thiscmdfile.write(header) 
            seqno = 0
            for jj in self.list_target_images:
                seqno += 1
                str_seqno = "{:04d}_".format(seqno)
                
                targetfile = jj.get_filename()
                sourcefile = targetfile
                filename   = str_seqno + os.path.basename(targetfile)
                targetfile = os.path.join(outdir, os.path.basename(filename))
                if self.platform == "WINDOWS":
                    sourcefile = re.sub(r'/', '\\\\', sourcefile) # replace / by \
                    targetfile = re.sub(r'/', '\\\\', targetfile) # replace / by \
                elif self.platform == "UNIX":
                    sourcefile = re.sub(r'\\', '/', sourcefile) # replace \ by /
                    targetfile = re.sub(r'\\', '/', targetfile) # replace \ by /
                print ("Sourcefile: {:s}, Targetfile: {:s}".format(sourcefile, targetfile)) if self.debug else True
                comment = ""
                str_ret = template
                str_ret = str_ret.replace('<source>', sourcefile)
                str_ret = str_ret.replace('<seqno>',  str_seqno)
                str_ret = str_ret.replace('<target>', targetfile)
                str_ret = re.sub(r'<<<NL>>>', '\n', str_ret) # reconstruct newline in template
                thiscmdfile.write(comment + str_ret + '\n')
            thiscmdfile.close()

    def rb_sort(self, event = None):
        # radiobuttons name / date asc / desc
        self.sort_source_images()

    def rb_g(self, event = None):
        # radiobuttons 'sort within type' (rbg == "1") / 'sort all' (rbg == "2")
        self.sort_source_images()

    def sort_source_images(self):
        # rbvalue: 1 name asc, 2 name desc, 3 mod. date asc, 4 mod. date desc
        # rbg "1" (sort within type): one block per type in the order of the camera types, inside each block by rbvalue
        # rbg "2" (sort all): sort over all types
        method = int(self.rbvalue.get())
        mtime_cache = {}
        def mtime(path):
            if path not in mtime_cache:
                try:
                    mtime_cache[path] = os.stat(path).st_mtime
                except OSError:
                    mtime_cache[path] = 0.0
            return mtime_cache[path]
        if method in (1, 2):
            key = lambda x: x.get_filename()
        else:
            key = lambda x: mtime(x.get_filename())
        lst = sorted(self.list_source_images, key = key, reverse = method in (2, 4))
        if self.rbg.get() == "1":
            type_order = {t: n for n, t in enumerate(self.dict_cameras)}
            lst.sort(key = lambda x: type_order.get(x.imgtype, 999)) # stable: keeps the order inside the type
        self.list_source_images = lst
        self.dict_source_images = self.display_image_objects(self.list_source_images, self.source_canvas, self.Label_source_ctr)
        self.apply_selections(self.list_source_images, self.source_canvas)

    def order_name_asc(self): # order images on source canvas by name asc
        self.list_source_images = sorted(self.list_source_images, key=lambda x: x.get_filename(), reverse=False)
        self.dict_source_images = self.display_image_objects(self.list_source_images, self.source_canvas, self.Label_source_ctr)
        self.apply_selections(self.list_source_images, self.source_canvas)
    def order_name_desc(self): # order images on source canvas by name desc
        self.list_source_images = sorted(self.list_source_images, key=lambda x: x.get_filename(), reverse=True)
        self.dict_source_images = self.display_image_objects(self.list_source_images, self.source_canvas, self.Label_source_ctr)
        self.apply_selections(self.list_source_images, self.source_canvas)
    def order_date_asc(self): # order images on source canvas by date asc
        self.list_source_images = sorted(self.list_source_images, key=lambda x: os.path.getmtime(x.get_filename()), reverse=False)
        self.dict_source_images = self.display_image_objects(self.list_source_images, self.source_canvas, self.Label_source_ctr)
        self.apply_selections(self.list_source_images, self.source_canvas)
    def order_date_desc(self): # order images on source canvas by date desc
        self.list_source_images = sorted(self.list_source_images, key=lambda x: os.path.getmtime(x.get_filename()), reverse=True)
        self.dict_source_images = self.display_image_objects(self.list_source_images, self.source_canvas, self.Label_source_ctr)
        self.apply_selections(self.list_source_images, self.source_canvas)

    def apply_selections(self, list_images, canvas):
        # now select / unselect, remember: display image objects always shows selecttion frame because it is drawn last!
        for i in list_images:
            # we selected all images which were selected before the delete action and unselect the others
            if i.is_selected(): # select
                self.select_image(i, canvas)
            else:
                self.unselect_image(i, canvas)


class HistObj:
    def __init__(self):

        # dict and list of source / target images, to be historized
        self.dict_source_images = {}
        self.dict_target_images = {}
        self.list_source_images = []
        self.list_target_images = []
        self.source_select_ctr = 0
        self.target_select_ctr = 0

        self.str_hashsum_source_filenames = ""
        self.str_hashsum_target_filenames = ""
        self.str_hashsum_source_selection = ""
        self.str_hashsum_target_selection = ""
        idx_akt = 0 # Index into Diatisch.dict
        #FsImages
        self.dict_file_thumbnail_source = {}
        self.dict_file_thumbnail_target = {}
        self.str_hashsum_file_thumbnail_source = ""
        self.str_hashsum_file_thumbnail_target = ""
        
        self.text = ""

if __name__ == "__main__":
    # MUSS die aller erste Aktion sein, bevor irgendein Tk-Fenster erzeugt wird!
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()  # Fallback für alte Windows-Versionen
            except Exception:
                pass
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-d", "--debug", help="Debug Mode")
    args = argParser.parse_args()
    print("args=%s" % args)
    print("args.debug=%s" % args.debug)
    debug = 'N'
    if args.debug:
        debug = args.debug.upper()

    root = tk.Tk()
    app = Diatisch(debug, root, False, False, False)  # when run as main we have no list of image files and no result list, no callback
    root.mainloop()