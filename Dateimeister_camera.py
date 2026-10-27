#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

import os
import re
import shutil
import time
from time import strftime

import tkinter as tk
import tkinter.ttk as ttk
from tkinter.constants import *
from tkinter import messagebox
from tkinter import Menu
from tkinter.font import Font

import dateimeister_config_xml as DX
import Undo_Redo as UR

import tools
from tools import Globals

class MyCameraTreeview:

    # The class "constructor" - It's actually an initializer
    def __init__(self, pmain: object = None, proctypes:str = None, debug:bool = False, cameraname=None):
        self.main = pmain
        self.cameraname = cameraname
        self.root = tk.Toplevel()
        self.root.protocol("WM_DELETE_WINDOW", self.close_handler)
        self.debug = debug

        if cameraname is not None:
            self.root.title(cameraname)
        else:
            self.root.title("Cameras")
        width, height = Globals.screen_width, Globals.screen_height
        v_dim = str(int(width * .75)) + 'x' + str(int(height * .75))
        self.root.geometry(v_dim)
        self.root.resizable(True, True)

        self.text_font = Font(family="Helvetica", size=6)

        # Frame and treeview
        self.Frame_treeview = tk.Frame(self.root)
        self.Frame_treeview.place(relx=0.015, rely=0.012, relheight=0.8, relwidth=0.985)
        self.Frame_treeview.configure(relief='flat')
        self.Frame_treeview.configure(background=tools._bgcolor_dbg) if self.debug else True

        style = ttk.Style()
        style.configure("Treeview", font=self.text_font)
        style.configure("Treeview.Heading", font=self.text_font)

        # ------------------------------------------------------------------
        # Treeview layout
        # #0 is the tree column (camera / type / suffix names). Three named
        # data columns:
        #   col_modified    : last modification date
        #   col_subdir      : subdir, only on type rows
        #   col_process     : process_image, only on suffix rows
        # ------------------------------------------------------------------
        self.tv = tools.ScrolledTreeView(self.Frame_treeview)
        self.tv.place(relx=0.015, rely=0.026, relheight=0.865, relwidth=0.975)
        self.tv.configure(
            columns=("col_modified", "col_subdir", "col_process"),
            show="tree headings",
            selectmode=tk.BROWSE,
        )

        self.tv.heading("#0",              text="Camera / Type / Suffix", anchor="w")
        self.tv.heading("col_modified",    text="Last modification",       anchor="w")
        self.tv.heading("col_subdir",      text="Type Subdir",             anchor="w")
        self.tv.heading("col_process",     text="Suffix Process",          anchor="w")

        self.tv.column("#0",             width=200, minwidth=100, stretch=True,  anchor="w")
        self.tv.column("col_modified",   width=140, minwidth=100, stretch=False, anchor="w")
        self.tv.column("col_subdir",     width=110, minwidth=80,  stretch=False, anchor="w")
        self.tv.column("col_process",    width=110, minwidth=80,  stretch=True,  anchor="w")

        # bind select events
        self.tv.tag_bind("camera", "<<TreeviewSelect>>", self.item_selected_camera)
        self.tv.tag_bind("type",   "<<TreeviewSelect>>", self.item_selected_type)
        self.tv.tag_bind("suffix", "<<TreeviewSelect>>", self.item_selected_suffix)

        # ------------------------------------------------------------------
        # Frame for entries and buttons for camera / type / suffix properties
        # ------------------------------------------------------------------
        self.frame_camera_properties = tk.Frame(self.root)
        self.frame_camera_properties.place(relx=0.01, rely=.82, relheight=0.07, relwidth=0.98)
        self.frame_camera_properties.configure(relief='flat')
        self.frame_camera_properties.configure(background=tools._bgcolor_dbg) if self.debug else True
        self.frame_camera_properties.update()

        relw_button = 0.9
        relh_button = 0.8
        relw_entry = 0.8
        relh_entry = 0.8
        offset_entry = .01

        # Widgets managed via create_widgets_from_dict.
        # process_image is a ttk.Combobox with a fixed set of values,
        # so it gets a "VALUES" entry in the dict.
        dict_widgets = {}
        
        l_proctypes = [x.strip().upper() for x in proctypes.split(",")]
 
        dict_widgets["1"] = {
          "WIDGET":tk.Button,"VAR":"button_camera_new","OFFSET":0.00,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"CENTER",
          "CALLBACK":self.camera_new,"TEXT":"New camera","STATE":None,"TT":"create a new camera","FONT":self.text_font}
        dict_widgets["2"] = {
          "WIDGET":tk.Entry,"VAR":"entry_camera","OFFSET":offset_entry,"RELH":relh_entry,"RELW":relw_entry,"ANCHOR":"END",
          "CALLBACK":None,"TEXT":None,"STATE":tk.DISABLED,"TT":"Enter new Cameraname","FONT":self.text_font, "TITLE":"'Camera', .3, END"}
        dict_widgets["3"] = {
          "WIDGET":tk.Entry,"VAR":"entry_type","OFFSET":offset_entry,"RELH":relh_entry,"RELW":relw_entry,"ANCHOR":"END",
          "CALLBACK":None,"TEXT":None,"STATE":tk.DISABLED,"TT":"Enter new type","FONT":self.text_font, "TITLE":"'Type', .3, END"}
        dict_widgets["4"] = {
          "WIDGET":tk.Entry,"VAR":"entry_suffix","OFFSET":offset_entry,"RELH":relh_entry,"RELW":relw_entry,"ANCHOR":"END",
          "CALLBACK":None,"TEXT":None,"STATE":tk.DISABLED,"TT":"Enter new image file suffix","FONT":self.text_font, "TITLE":"'Suffix', .3, END"}
        dict_widgets["5"] = {
          "WIDGET":tk.Entry,"VAR":"entry_subdir","OFFSET":offset_entry,"RELH":relh_entry,"RELW":relw_entry,"ANCHOR":"END",
          "CALLBACK":None,"TEXT":None,"STATE":tk.DISABLED,"TT":"Enter subdir for type","FONT":self.text_font, "TITLE":"'Subdir', .3, END"}
        dict_widgets["5a"] = {
          "WIDGET":ttk.Combobox,"VAR":"entry_process_image","OFFSET":offset_entry,"RELH":relh_entry,"RELW":relw_entry,"ANCHOR":"END",
          "CALLBACK":None,"TEXT":None,"STATE":"disabled","TT":"Select process_image","FONT":self.text_font,
          "TITLE":"'Process Image', .3, END", "VALUES":l_proctypes}
        dict_widgets["6"] = {
          "WIDGET":tk.Button,"VAR":"button_apply","OFFSET":0.01,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"CENTER",
          "CALLBACK":self.apply_new,"TEXT":"Apply","STATE":tk.ACTIVE,"TT":"apply changes","FONT":self.text_font}
        dict_widgets["7"] = {
          "WIDGET":tk.Button,"VAR":"button_cancel","OFFSET":0.01,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"CENTER",
          "CALLBACK":self.cancel_new,"TEXT":"Cancel","STATE":tk.ACTIVE,"TT":"cancel changes","FONT":self.text_font}
        tools.create_widgets_from_dict(dict_widgets, self.frame_camera_properties, "HORIZONTAL",
                                       font=self.text_font, bgcolor=tools._bgcolor)

        # ------------------------------------------------------------------
        # Frame for undo / redo
        # ------------------------------------------------------------------
        self.root.update()
        self.frame_buttons = tk.Frame(self.root)
        self.frame_buttons.place(relx=.01, rely=.9, relheight=0.07, relwidth=.2)
        self.frame_buttons.configure(relief='flat')
        self.frame_buttons.configure(background=tools._bgcolor_dbg) if self.debug else True
        self.frame_buttons.update()

        dict_widgets = {}
        dict_widgets["1"] = {
          "WIDGET":tk.Button,"VAR":"button_undo","OFFSET":0.00,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"CENTER",
          "CALLBACK":self.button_undo_h,"TEXT":"Undo","STATE":None,"TT":"undo action","FONT":self.text_font}
        dict_widgets["2"] = {
          "WIDGET":tk.Button,"VAR":"button_redo","OFFSET":0.01,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"CENTER",
          "CALLBACK":self.button_redo_h,"TEXT":"Redo","STATE":None,"TT":"redo action","FONT":self.text_font}
        tools.create_widgets_from_dict(dict_widgets, self.frame_buttons, "HORIZONTAL",
                                       font=self.text_font, bgcolor=tools._bgcolor)

        self.root.bind('<Return>', self.apply_new)
        self.root.bind('<Control-z>', lambda event: self.process_undo(event))
        self.root.bind('<Control-y>', lambda event: self.process_redo(event))

        # ------------------------------------------------------------------
        # Context menu
        # ------------------------------------------------------------------
        self.context_menu = tk.Menu(self.tv, tearoff=0)
        self.context_menu.add_command(label="change", command=self.type_change)
        self.context_menu.add_command(label="delete", command=self.type_delete)
        self.tv.bind("<Button-3>", self.set_selection_by_button3)

        # ------------------------------------------------------------------
        # Instance variables
        # ------------------------------------------------------------------
        self.item = ""
        self.tag = ""
        self.text = ""
        self.event = None
        self.context_menu_required = False
        self.newitem = ""
        self.camera = ""
        self.ctype = ""
        self.suffix = ""
        self.subdir = ""
        self.process_image = ""
        self.dict_camera_iid = {}
        self.dict_subdirs = {}          # {camera: {type: subdir}}
        self.dict_process_image = {}    # {camera: {type: {suffix: process}}}
        self.locked = False

        # initial disabled state
        self.entry_subdir.config(state=DISABLED)
        self.entry_process_image.config(state=DISABLED)

        # Undo / Redo
        self.UR = UR.Undo_Redo_Camera(self.main.debug_p)
        self.dict_processid_xmlfile = {}
        self.historize_process()

        self.lock_treeview(False)
        # populate treeview from xml
        self.treeview_from_xml(Globals.config_files_xml)

    # ----------------------------------------------------------------------
    # Generic widget helper: works with Entry and ttk.Combobox
    # ----------------------------------------------------------------------
    def new_text(self, o, text):
        """Set the display value of an Entry or ttk.Combobox."""
        if isinstance(o, ttk.Combobox):
            o.set(text)
        else:
            o.delete(0, 'end')
            o.insert('end', text)

    def treeview_clear(self):
        """Remove all nodes from the treeview."""
        for i in self.tv.get_children():
            self.tv.delete(i)
        self.root.update()

    def lock_treeview(self, block):
        """Enable/disable the treeview (grey it out) while an edit is in
        progress, and enable/disable the 'New camera' button accordingly."""
        if block == False:
            self.locked = False
            ttk.Style().configure("Treeview", background="white", foreground="black", fieldbackground="white")
            self.button_camera_new.config(state=NORMAL)
        else:
            self.locked = True
            ttk.Style().configure("Treeview", background="lightgrey", foreground="black", fieldbackground="lightgrey")
            self.button_camera_new.config(state=DISABLED)

    # ----------------------------------------------------------------------
    # Populate treeview from xml
    # ----------------------------------------------------------------------
    def treeview_from_xml(self, xml):
        """
        Rebuild the whole camera tree from the given xml file.

        Reads two per-camera dictionaries from the xml:
            dict_subdirs       : {camera: {type: subdir}}
            dict_process_image : {camera: {type: {suffix: process}}}

        For each missing value in the tree a "forced dialog" is scheduled:
        the first missing entry triggers a messagebox, after the user applies
        the value apply_new() refreshes the treeview, and the next missing
        entry is prompted. Only one prompt is shown at a time (see the
        'return' inside each loop below).
        """
        self.dict_subdirs = DX.get_subdirs_per_camera(xml)
        self.dict_process_image = DX.get_process_image_per_camera(xml)

        self.treeview_clear()
        self.dict_camera_iid = {}
        dict_cameras_usedate = DX.get_cameras_usedate(xml)
        dict_cameras = DX.get_cameras_types_suffixes(xml)

        # buckets collecting missing entries, keyed by camera (and type/suffix)
        dict_type_without_suffix    = {}
        dict_type_without_subdir    = {}
        dict_suffix_without_process = {}

        last_camera = None
        ctype_num = 0
        for camera in dict_cameras:
            last_camera = camera
            cam_key = camera.upper()
            ctype_num = 0
            usedate = dict_cameras_usedate[camera]
            cid = self.tv.insert("", tk.END, text=camera,
                                 values=(usedate, "", ""), tag=("camera",))
            self.dict_camera_iid[camera] = cid
            dict_type_without_suffix[camera] = {}
            dict_type_without_subdir[camera] = {}
            dict_suffix_without_process[camera] = {}

            for ctype in dict_cameras[camera]:
                ctype_num += 1
                ctype_key = ctype.upper()
                subdir = self.dict_subdirs.get(cam_key, {}).get(ctype_key, "!")

                tid = self.tv.insert(cid, tk.END, text=ctype,
                                     values=("", subdir, ""),
                                     tag=("type",))
                if subdir == "!":
                    dict_type_without_subdir[camera][ctype] = tid

                csuffix_num = 0
                for csuffix in dict_cameras[camera][ctype]:
                    csuffix_num += 1
                    csuffix_key = csuffix.upper()
                    process_image = (self.dict_process_image
                                     .get(cam_key, {})
                                     .get(ctype_key, {})
                                     .get(csuffix_key, "!"))
                    sid = self.tv.insert(tid, tk.END, text=csuffix,
                                         values=("", "", process_image),
                                         tag=("suffix",))

                    if process_image == "!":
                        dict_suffix_without_process[camera].setdefault(ctype, {})[sid] = csuffix
                if csuffix_num == 0:
                    dict_type_without_suffix[camera][ctype] = tid

        if ctype_num == 0 and last_camera is not None:
            messagebox.showinfo("INIT",
                                "Camera " + last_camera +
                                " no type defined. At least 1 is needed",
                                parent=self.root)

        # Prompt only the first missing entry per run; apply_new() will
        # refresh the treeview and re-enter this method for the next one.
        for camera in dict_type_without_suffix:
            for ctype in dict_type_without_suffix[camera]:
                self.prompt_missing(camera, ctype,
                                    dict_type_without_suffix[camera][ctype],
                                    "no suffix defined. At least 1 is needed",
                                    self.type_new_suffix)
                return
        for camera in dict_type_without_subdir:
            for ctype in dict_type_without_subdir[camera]:
                self.prompt_missing(camera, ctype,
                                    dict_type_without_subdir[camera][ctype],
                                    "no subdir defined. Please enter a subdir",
                                    self.type_subdir)
                return
        for camera in dict_suffix_without_process:
            for ctype in dict_suffix_without_process[camera]:
                for sid, suffix in dict_suffix_without_process[camera][ctype].items():
                    self.prompt_missing_suffix(camera, ctype, suffix, sid,
                                               "no process_image defined. Please select one",
                                               self.suffix_process_image)
                    return

    def prompt_missing(self, camera, ctype, tid, msg, action):
        """
        Focus a type node that lacks a required property (suffix or subdir)
        and invoke the given action (e.g. self.type_subdir) so the user
        can fill in the missing value.
        """
        self.open_camera(camera)
        messagebox.showinfo("MyCameraTreeview",
                            "Camera " + camera + " type " + ctype + " " + msg,
                            parent=self.root)
        self.tv.focus(tid)
        self.tv.selection_set(tid)
        self.item = tid
        self.text = ctype
        self.tag = "type"
        self.context_menu_required = False
        action()

    def prompt_missing_suffix(self, camera, ctype, suffix, sid, msg, action):
        """
        Focus a suffix node that lacks a required process_image and invoke
        the given action (self.suffix_process_image) so the user can select
        the missing value.
        """
        self.open_camera(camera)
        messagebox.showinfo("MyCameraTreeview",
                            "Camera " + camera + " type " + ctype +
                            " suffix " + suffix + " " + msg,
                            parent=self.root)
        self.tv.focus(sid)
        self.tv.selection_set(sid)
        self.item = sid
        self.text = suffix
        self.tag = "suffix"
        self.context_menu_required = False
        action()

    # ----------------------------------------------------------------------
    # Treeview select callbacks
    # ----------------------------------------------------------------------
    def item_selected_camera(self, event):
        """<<TreeviewSelect>> handler bound to camera nodes."""
        self.retrieve_item(event)

    def item_selected_type(self, event):
        """<<TreeviewSelect>> handler bound to type nodes."""
        self.retrieve_item(event)

    def item_selected_suffix(self, event):
        """<<TreeviewSelect>> handler bound to suffix nodes."""
        self.retrieve_item(event)

    def retrieve_item(self, event):
        """
        Remember the currently selected treeview item (self.item, self.text,
        self.tag) and, if requested, show the context menu for it.
        Called by item_selected_* (ordinary selection) and by
        set_selection_by_button3 (right-click).
        """
        if self.locked:
            print("retrieve_item is locked")
            return
        try:
            self.item = self.tv.selection()[0]
            print("Item selected: ", str(self.tv.selection()))
        except IndexError:
            messagebox.showwarning(message="Nothin selected",
                                   title="Treeview Selection",
                                   parent=self.root)
            return

        self.text = self.tv.item(self.item, option="text")
        self.tag = self.tv.item(self.item, option="tag")[0]

        if self.context_menu_required:
            if self.tag.upper() == "CAMERA":
                self.context_menu.delete(0, 10)
                self.context_menu.insert_command(0, label=self.text + " new type...", command=self.camera_new_type)
                self.context_menu.insert_command(1, label=self.text + " change...", command=self.camera_change)
                self.context_menu.insert_command(2, label=self.text + " delete", command=self.camera_delete)
            elif self.tag.upper() == "TYPE":
                self.context_menu.delete(0, 10)
                self.context_menu.insert_command(0, label=self.text + " new suffix...", command=self.type_new_suffix)
                self.context_menu.insert_command(1, label=self.text + " change...", command=self.type_change)
                self.context_menu.insert_command(2, label=self.text + " delete", command=self.type_delete)
                self.context_menu.insert_command(3, label=self.text + " subdir...", command=self.type_subdir)
            elif self.tag.upper() == "SUFFIX":
                self.context_menu.delete(0, 10)
                self.context_menu.insert_command(0, label=self.text + " change...", command=self.suffix_change)
                self.context_menu.insert_command(1, label=self.text + " delete", command=self.suffix_delete)
                self.context_menu.insert_command(2, label=self.text + " process_image...", command=self.suffix_process_image)
            if self.event is not None and hasattr(self.event, "x_root"):
                self.context_menu.post(self.event.x_root, self.event.y_root)
        self.context_menu_required = False

    def set_selection_by_button3(self, event):
        """
        Right-click handler for the treeview: select the item under the
        mouse, remember the event and then call retrieve_item() directly.

        Previously this method only set context_menu_required = True and
        relied on the <<TreeviewSelect>> event to trigger retrieve_item().
        That event is not reliably fired for a programmatic selection_set,
        so the context menu could silently not appear. Calling retrieve_item
        here is the robust fix.
        """
        iid = self.tv.identify('item', event.x, event.y)
        self.event = event
        print("button 3 clicked, iid is: " + str(iid))
        if iid:
            self.tv.focus(iid)
            self.tv.selection_set(iid)
            self.context_menu_required = True
            print(" iid is: " + str(iid))
            self.retrieve_item(event)

    # ----------------------------------------------------------------------
    # Context menu command handlers
    # ----------------------------------------------------------------------
    def camera_new(self):
        """Toolbar button 'New camera': ask for a new camera + type + suffix."""
        print(self.text + " camera new selected by button")
        self.newitem = "CAMERA_NEW"
        self.enable_processing(True, True, True, False, True, False,
                               "", "", "", "", "JPEG")

    def camera_change(self):
        """Context menu (on camera node): rename the selected camera."""
        print(self.text + " camera change selected from context menu")
        camera, iid = self.get_camera(self.item)
        self.newitem = "CAMERA_RENAME"
        self.camera = camera
        self.enable_processing(True, False, False, False, True, False,
                               self.camera, "", "", "", "")

    def camera_delete(self):
        """Context menu (on camera node): delete the camera and its children."""
        print(self.text + " camera delete selected from context menu")
        camera, iid = self.get_camera(self.item)
        self.newitem = "CAMERA_DELETE"
        self.camera = camera
        self.enable_processing(False, False, False, False, False, False,
                               "", "", "", "", "")
        self.apply_new()

    def camera_new_type(self):
        """Context menu (on camera node): add a new type with a first suffix."""
        print(self.text + " camera new type selected from context menu")
        camera, iid = self.get_camera(self.item)
        self.newitem = "TYPE_NEW"
        self.camera = camera
        self.enable_processing(False, True, True, False, True, False,
                               self.camera, "", "", "", "JPEG")

    def type_change(self):
        """Context menu (on type node): rename the selected type."""
        print(self.text + " type change selected from context menu")
        camera, ctype, iid = self.get_camera_type(self.item)
        self.entry_camera.delete(0, 'end')
        self.entry_camera.focus_set()
        self.newitem = "TYPE_RENAME"
        self.camera = camera
        self.ctype = ctype
        self.enable_processing(False, True, False, False, True, False,
                               self.camera, self.ctype, "", "", "")

    def type_delete(self):
        """Context menu (on type node): delete the selected type."""
        print(self.text + " type delete selected from context menu")
        camera, ctype, iid = self.get_camera_type(self.item)
        self.newitem = "TYPE_DELETE"
        self.camera = camera
        self.ctype = ctype
        self.enable_processing(False, False, False, False, False, False,
                               "", "", "", "", "")
        self.apply_new()

    def type_new_suffix(self):
        """Context menu (on type node): add a new suffix to the type."""
        print(self.text + " type new suffix selected from context menu")
        camera, ctype, iid = self.get_camera_type(self.item)
        self.entry_camera.delete(0, 'end')
        self.entry_camera.focus_set()
        self.newitem = "SUFFIX_NEW"
        self.camera = camera
        self.ctype = ctype
        self.suffix = self.text
        self.enable_processing(False, False, True, False, True, False,
                               self.camera, self.ctype, "", "", "")

    def type_subdir(self):
        """Context menu (on type node): set the subdir for this camera/type."""
        print(self.text + " type subdir selected from context menu")
        camera, ctype, iid = self.get_camera_type(self.item)
        self.entry_camera.delete(0, 'end')
        self.entry_camera.focus_set()
        self.newitem = "TYPE_SUBDIR"
        self.camera = camera
        self.ctype = ctype
        self.enable_processing(False, False, False, True, True, False,
                               self.camera, self.ctype, "", "", "")

    def suffix_change(self):
        """Context menu (on suffix node): rename the selected suffix."""
        print(self.text + " suffix change selected from context menu")
        camera, ctype, suffix, iid = self.get_camera_type_suffix(self.item)
        self.entry_camera.delete(0, 'end')
        self.entry_camera.focus_set()
        self.newitem = "SUFFIX_RENAME"
        self.camera = camera
        self.ctype = ctype
        self.suffix = self.text
        self.enable_processing(False, False, True, False, True, False,
                               self.camera, self.ctype, "", "", "")

    def suffix_delete(self):
        """Context menu (on suffix node): delete the selected suffix."""
        print(self.text + " suffix delete selected from context menu")
        camera, ctype, suffix, iid = self.get_camera_type_suffix(self.item)
        self.newitem = "SUFFIX_DELETE"
        self.camera = camera
        self.ctype = ctype
        self.suffix = self.text
        self.enable_processing(False, False, False, False, False, False,
                               "", "", "", "", "")
        self.apply_new()

    def suffix_process_image(self):
        """Context menu (on suffix node): set process_image for this suffix."""
        print(self.text + " suffix process_image selected from context menu")
        camera, ctype, suffix, iid = self.get_camera_type_suffix(self.item)
        self.newitem = "PROCESS_IMAGE"
        self.camera = camera
        self.ctype = ctype
        self.suffix = suffix
        self.enable_processing(False, False, False, False, True, True,
                               self.camera, self.ctype, self.suffix, "", "JPEG")

    # ----------------------------------------------------------------------
    # Central enable / disable of the property widgets
    # ----------------------------------------------------------------------
    def enable_processing(self, b_camera, b_type, b_suffix, b_subdir,
                          b_buttons, b_process_image,
                          text_camera, text_ctype, text_suffix,
                          text_subdir, text_process_image):
        """
        Prefill the property widgets from the given text arguments, then
        enable only those widgets whose b_* flag is True. All other widgets
        and the treeview stay disabled until Apply/Cancel.

        Arguments:
            b_camera        enable entry_camera
            b_type          enable entry_type
            b_suffix        enable entry_suffix
            b_subdir        enable entry_subdir
            b_buttons       enable Apply / Cancel and bind Return
            b_process_image enable entry_process_image (readonly Combobox)
            text_camera / text_ctype / text_suffix
            text_subdir / text_process_image
        """
        # enable everything briefly so .set()/.insert() work
        self.entry_camera.config(state=NORMAL)
        self.entry_type.config(state=NORMAL)
        self.entry_suffix.config(state=NORMAL)
        self.entry_subdir.config(state=NORMAL)
        self.entry_process_image.config(state=NORMAL)

        self.new_text(self.entry_camera, text_camera)
        self.new_text(self.entry_type,   text_ctype)
        self.new_text(self.entry_suffix, text_suffix)

        cam_key  = (text_camera  or self.camera  or "").upper()
        type_key = (text_ctype   or self.ctype   or "").upper()
        suf_key  = (text_suffix  or self.suffix  or "").upper()

        subdir = self.dict_subdirs.get(cam_key, {}).get(type_key, "")
        if subdir and subdir != "!":
            self.new_text(self.entry_subdir, subdir)
        else:
            self.new_text(self.entry_subdir, text_subdir or "")

        process_image = ""
        if suf_key:
            process_image = (self.dict_process_image
                             .get(cam_key, {})
                             .get(type_key, {})
                             .get(suf_key, ""))
        if process_image and process_image != "!":
            self.new_text(self.entry_process_image, process_image)
        else:
            self.new_text(self.entry_process_image, text_process_image or "JPEG")

        # disable everything, then enable the requested fields
        self.root.unbind('<Return>')
        self.button_apply.config(state=DISABLED)
        self.button_cancel.config(state=DISABLED)
        self.entry_camera.config(state=DISABLED)
        self.entry_type.config(state=DISABLED)
        self.entry_suffix.config(state=DISABLED)
        self.entry_subdir.config(state=DISABLED)
        self.entry_process_image.config(state=DISABLED)

        focus = False
        if b_camera:
            self.entry_camera.config(state=NORMAL, background='yellow')
            self.entry_camera.focus_set()
            focus = True
        if b_type:
            self.entry_type.config(state=NORMAL, background='yellow')
            if not focus:
                self.entry_type.focus_set()
                focus = True
        if b_suffix:
            self.entry_suffix.config(state=NORMAL, background='yellow')
            if not focus:
                self.entry_suffix.focus_set()
                focus = True
        if b_subdir:
            self.entry_subdir.config(state=NORMAL, background='yellow')
            if not focus:
                self.entry_subdir.focus_set()
                focus = True
        if b_process_image:
            self.entry_process_image.config(state="readonly", background='yellow')
            if not focus:
                self.entry_process_image.focus_set()
                focus = True

        if b_buttons:
            self.button_apply.config(state=NORMAL)
            self.button_cancel.config(state=NORMAL)
            self.root.bind('<Return>', self.apply_new)

        self.lock_treeview(True)

    # ----------------------------------------------------------------------
    # Helpers to walk the treeview hierarchy
    # ----------------------------------------------------------------------
    def get_camera_type_suffix(self, iid):
        """
        Called when the selected treeview item (self.item) is a SUFFIX node.
        Walks the tree upwards: suffix -> type -> camera.
        Reads the *original* (case-preserving) names from the treeview
        nodes, so the case matches the xml exactly.
        Returns (camera, ctype, suffix, iid_of_camera).
        """
        iid = self.item        
        suffix = self.tv.item(iid, option="text")
        iid = self.tv.parent(iid)
        ctype = self.tv.item(iid, option="text")
        iid = self.tv.parent(iid)
        camera = self.tv.item(iid, option="text")
        return camera, ctype, suffix, iid

    def get_camera_type(self, iid):
        """
        Called when the selected treeview item (self.item / self.text) is a
        TYPE node. Walks the tree upwards: type -> camera.
        Returns (camera, ctype, iid_of_camera).
        """
        iid = self.item
        ctype = self.text
        iid = self.tv.parent(iid)
        camera = self.tv.item(iid, option="text")
        return camera, ctype, iid

    def get_camera(self, iid):
        """
        Called when the selected treeview item (self.item / self.text) is a
        CAMERA node. No walk needed.
        Returns (camera, iid_of_camera).
        """
        iid = self.item
        camera = self.tv.item(iid, option="text")
        return camera, iid

    # ----------------------------------------------------------------------
    # Apply / Cancel
    # ----------------------------------------------------------------------
    def apply_new(self, event=None):
        """
        React to Apply or <Return>: dispatch on self.newitem to perform the
        requested change (write to xml via DX.*), then refresh the treeview
        and main window data.

        self.newitem values handled here:
            CAMERA_NEW, CAMERA_RENAME, CAMERA_DELETE
            TYPE_NEW, TYPE_RENAME, TYPE_DELETE
            SUFFIX_NEW, SUFFIX_RENAME, SUFFIX_DELETE
            TYPE_SUBDIR
            PROCESS_IMAGE
        """
        ts = strftime("%Y%m%d-%H:%M:%S", time.localtime())

        if self.newitem == "SUFFIX_NEW":
            suffix = self.entry_suffix.get().upper()
            if suffix is not None and suffix != "":
                rc = DX.new_camera_type_suffix(Globals.config_files_xml,
                                               self.camera, self.ctype, suffix, ts)
            else:
                messagebox.showinfo("MyCameraTreeview",
                                    "Camera " + self.camera + " type " + self.ctype +
                                    " no suffix defined. At least 1 is needed or press cancel",
                                    parent=self.root)
                self.entry_suffix.focus_set()
                return

        elif self.newitem == "SUFFIX_RENAME":
            suffix_new = self.entry_suffix.get().upper()
            rc = DX.update_camera_type_suffix(Globals.config_files_xml,
                                              self.camera, self.ctype, self.suffix,
                                              suffix_new, ts)
            self.suffix = suffix_new

        elif self.newitem == "SUFFIX_DELETE":
            suffix = self.suffix
            rc = DX.update_camera_type_suffix(Globals.config_files_xml,
                                              self.camera, self.ctype, suffix, "", ts)
            print("delete suffix rc: " + str(rc))

        elif self.newitem == "TYPE_NEW":
            ctype = self.entry_type.get().upper()
            if ctype is not None and ctype != "":
                suffix = self.entry_suffix.get().upper()
                if suffix is None or suffix == "":
                    messagebox.showinfo("MyCameraTreeview",
                                        "Camera " + self.camera + " type " + ctype +
                                        " no suffix defined. At least 1 is needed or press cancel",
                                        parent=self.root)
                    self.entry_suffix.focus_set()
                    return
                else:
                    rc = DX.new_camera_type_suffix(Globals.config_files_xml,
                                                   self.camera, ctype, suffix, ts)
            else:
                messagebox.showinfo("MyCameraTreeview",
                                    "Camera " + self.camera +
                                    " no type defined. Please enter type or press cancel",
                                    parent=self.root)
                self.entry_type.focus_set()
                return

        elif self.newitem == "TYPE_RENAME":
            type_new = self.entry_type.get().upper()
            rc = DX.update_camera_type(Globals.config_files_xml,
                                       self.camera, self.ctype, type_new, ts)
            self.ctype = type_new

        elif self.newitem == "TYPE_DELETE":
            rc = DX.update_camera_type(Globals.config_files_xml,
                                       self.camera, self.ctype, "", ts)

        elif self.newitem == "TYPE_SUBDIR":
            subdir = self.entry_subdir.get()
            rc = DX.new_subdir_camera(Globals.config_files_xml,
                                      self.camera, self.ctype, subdir)
            if rc == 0:
                print("subdir created for camera " + self.camera + " type " + self.ctype)
            elif rc == 1:
                print("subdir updated for camera " + self.camera + " type " + self.ctype)
            else:
                print("subdir: camera/type not found: " + self.camera + "/" + self.ctype)

        elif self.newitem == "PROCESS_IMAGE":
            process_image = self.entry_process_image.get().upper()
            if not process_image:
                messagebox.showinfo("MyCameraTreeview",
                                    "Please select a process_image for suffix " + self.suffix,
                                    parent=self.root)
                self.entry_process_image.focus_set()
                return
            rc = DX.new_process_image_camera(Globals.config_files_xml,
                                             self.camera, self.ctype, self.suffix,
                                             process_image)
            if rc == 0:
                print("process_image set for " + self.camera + "/" + self.ctype + "/" + self.suffix)
            elif rc == 1:
                print("process_image updated for " + self.camera + "/" + self.ctype + "/" + self.suffix)
            else:
                print("process_image: camera/type/suffix not found")

        elif self.newitem == "CAMERA_NEW":
            camera = self.entry_camera.get().upper()
            if camera is not None and camera != "":
                ctype = self.entry_type.get().upper()
                if ctype is None or ctype == "":
                    messagebox.showinfo("MyCameraTreeview",
                                        "Camera " + self.camera +
                                        " no type defined. At least 1 is needed or press cancel",
                                        parent=self.root)
                    self.entry_type.focus_set()
                    return
                else:
                    self.camera = camera
                    suffix = self.entry_suffix.get().upper()
                    if suffix is None or suffix == "":
                        messagebox.showinfo("MyCameraTreeview",
                                            "Camera " + self.camera + " type " + ctype +
                                            " no suffix defined. At least 1 is needed or press cancel",
                                            parent=self.root)
                        self.entry_suffix.focus_set()
                        return
                    else:
                        rc = DX.new_camera_type_suffix(Globals.config_files_xml,
                                                       camera, ctype, suffix, ts)
            else:
                messagebox.showinfo("MyCameraTreeview",
                                    "Camera " + self.camera +
                                    " no camera defined. Please enter camera or press cancel",
                                    parent=self.root)
                self.entry_camera.focus_set()
                return

        elif self.newitem == "CAMERA_RENAME":
            print(" rename requested for: " + self.camera)
            camera_new = self.entry_camera.get().upper()
            rc = DX.update_camera(Globals.config_files_xml, self.camera, camera_new)
            self.camera = camera_new

        elif self.newitem == "CAMERA_DELETE":
            print(" delete requested for: " + self.camera)
            rc = DX.update_camera(Globals.config_files_xml, self.camera, "")

        # reset the dialog and unlock BEFORE refreshing the treeview, so that
        # treeview_from_xml can trigger the next forced dialog cleanly.
        self.enable_processing(False, False, False, False, False, False,
                               "", "", "", "", "")
        self.lock_treeview(False)
        self.treeview_from_xml(Globals.config_files_xml)
        if self.camera is not None and self.camera != "":
            self.open_camera(self.camera)
        self.update_main_window()
        self.historize_process()

    def cancel_new(self, event=None):
        """React to Cancel: restore the default (disabled) dialog state."""
        if self.camera is not None and self.camera != "":
            self.open_camera(self.camera)
        self.enable_processing(False, False, False, False, False, False,
                               "", "", "", "", "")
        self.lock_treeview(False)

    # ----------------------------------------------------------------------
    # Misc helpers
    # ----------------------------------------------------------------------
    def open_camera(self, camera):
        """Expand the given camera node and all its type children."""
        if camera in self.dict_camera_iid:
            iid = self.dict_camera_iid[camera]
            self.tv.item(iid, open=True)
            item_children = self.tv.get_children(iid)
            for iid_child in item_children:
                self.tv.item(iid_child, open=True)

    def update_main_window(self):
        """
        Push the freshly read per-camera data into the main window, restricted
        to the camera that is currently being edited.
        The main window keeps its flat dicts (dict_subdirs etc.); those are
        rebuilt for exactly this camera here.
        """
        camera = self.camera
        if camera is None or camera == "":
            try:
                camera = self.main.o_camera.get()
            except Exception:
                camera = ""
        self.main.dict_cameras, self.main.dict_subdirs, self.main.dict_process_image = \
            self.main.get_camera_xml(camera=camera)

    # ----------------------------------------------------------------------
    # Undo / Redo functions
    # ----------------------------------------------------------------------
    def process_undo(self, event):
        """Ctrl-Z handler: apply the previous historized xml state."""
        print("ctrl_z pressed.")
        rc, p_now, p_before = self.UR.process_undo()
        if not rc:
            messagebox.showinfo("UNDO", "no further processes which can be undone",
                                parent=self.root)
        else:
            self.apply_process_id(p_now, p_before)
            self.endis_buttons()

    def process_redo(self, event):
        """Ctrl-Y handler: re-apply the next historized xml state."""
        print("ctrl_y pressed.")
        rc, p_now, p_before = self.UR.process_redo()
        if not rc:
            messagebox.showinfo("REDO", "no further processes which can be redone",
                                parent=self.root)
        else:
            self.apply_process_id(p_now, p_before)
            self.endis_buttons()

    def button_undo_h(self, event=None):
        """Toolbar button handler for Undo."""
        print("Button Undo pressed")
        self.process_undo(event)

    def button_redo_h(self, event=None):
        """Toolbar button handler for Redo."""
        print("Button Redo pressed")
        self.process_redo(event)

    def endis_buttons(self):
        """Enable/disable Undo and Redo buttons according to the history."""
        rc_undo, rc_redo = self.UR.endis_buttons()
        if rc_undo:
            self.button_undo.config(state=NORMAL)
        else:
            self.button_undo.config(state=DISABLED)
        if rc_redo:
            self.button_redo.config(state=NORMAL)
        else:
            self.button_redo.config(state=DISABLED)

    def apply_process_id(self, process_id, processid_predecessor):
        """
        Restore a historized xml state: copy the xml file belonging to
        process_id over Globals.config_files_xml and refresh the treeview.
        """
        xml_filename = self.dict_processid_xmlfile[process_id]
        print("apply_process_id, xml to apply is: ", xml_filename)
        sourcefile = xml_filename
        targetfile = Globals.config_files_xml
        try:
            shutil.copy(sourcefile, targetfile)
        except shutil.FileNotFoundError:
            print("Source file " + sourcefile + " not found.")
        except shutil.SameFileError:
            print("Source and destination represents the same file.")
        except PermissionError:
            print("Permission denied.")
        except:
            print("Error occurred while copying file.")
        self.treeview_from_xml(Globals.config_files_xml)
        if self.camera is not None and self.camera != "":
            self.open_camera(self.camera)

    def historize_process(self):
        """
        Take a snapshot of the current xml file and store it under a
        process-id-specific filename, so Undo/Redo can restore it later.
        """
        self.UR.historize_process()
        processid_akt = self.UR.get_processid_akt()
        config_dir = os.path.join(Globals.datadir, Globals.config_files_subdir)
        xml_filename = Globals.config_files_xml
        # insert _<processid> before the file extension
        xml_filename = re.sub(r'\.([^\.]+)$', rf"_{processid_akt}.\1", xml_filename)
        self.dict_processid_xmlfile[processid_akt] = xml_filename
        print("historize_process, new xml is: ", xml_filename)
        sourcefile = Globals.config_files_xml
        targetfile = xml_filename
        try:
            shutil.copy(sourcefile, targetfile)
        except shutil.FileNotFoundError:
            print("Source file " + sourcefile + " not found.")
        except shutil.SameFileError:
            print("Source and destination represents the same file.")
        except PermissionError:
            print("Permission denied.")
        except:
            print("Error occurred while copying file.")

        self.endis_buttons()

    # Ende undo / redo-Funktionen

    def close_handler(self):
        """WM_DELETE_WINDOW handler: destroy the camera window."""
        self.root.destroy()

    def __del__(self):
        self.a = 1
        #print("*** Deleting Camera-Treeview-Objekt.")

