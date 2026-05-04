# variables used by more than 1 class
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
import argparse
import inspect
import tkinter.messagebox as mb

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
import Tooltip as TT

from time import gmtime, strftime

from datetime import datetime, timezone

INCLUDE = 1
EXCLUDE = 2

# some universal functions
def count_files_top(path):
    with os.scandir(path) as it:
        return sum(1 for entry in it if entry.is_file())

def count_files_recursive(path):
    total = 0
    for root, dirs, files in os.walk(path):
        total += len(files)
    return total


def create_widgets_from_dict(dict_widgets, parent, p_orientation, font): 
    """
    Create multiple widgets in a horizontal or vertical line inside a parent widget (usually a frame).

    Supported widget types include Button, Entry and Label. Other widget types may work but must be tested first.

    Because mixed widget types are now supported, the function always fills the entire parent area.

    Offsets and sizes are normalized so that their total always equals 1.

    RELH / RELW representsand the widget height when orientare the relative height / width of the widget

    If orientation is HORIZONTAL:
        - If widget height >= parent height, the widget height is clamped to the parent height.
        - If widget height < parent height, the widget is placed at the top (ANCHOR=START),
          bottom (ANCHOR=END), or vertically centered (ANCHOR=CENTER).

    If orientation is VERTICAL:
        - If widget width >= parent width, the widget width is clamped to the parent height.
        - If widget width < parent width, the widget is placed at the left (ANCHOR=START),
          right (ANCHOR=END), or horizontally centered (ANCHOR=CENTER).

    Title: we can define a title, e.g. for an Entry. The Syntax is:
        '<string>', <relsize>, <position>
        with: <string > = Text to be displayed, <relsize> = relative size within the space available for the widget, 
            <position> = one os START, END where START / END means Top / Bottom  if orientation = HORIZONTAL, left / right if orientation = VERTICAL

    For each widget, the following attributes are applied if provided:
        - VAR:variable name (assigned to the caller object)
        - OFFSET: space before Widget starts
        - RELW: relative width
        - RELH: relative height
        - ANCHOR: START / END /CENTER
        - TEXT:text
        - CALLBACK:callback
        - TT:tooltip
        - STATE:state
        - FONT:font
        - TITLE: string defining title (s.o.)
    we calculate throughout with relative values
    """
     
    # get stackframe of caller
    frame = inspect.currentframe().f_back
    # extract caller object (self)
    caller = frame.f_locals.get("self", None)
    debug = caller.debug

    num_widgets = 0
    sum_offsets = 0
    sum_widgets = 0
    if p_orientation.upper() == "HORIZONTAL":
        orientation = p_orientation.upper()
    elif p_orientation.upper() == "VERTICAL":
        orientation = p_orientation.upper()
    else:
        raise ValueError("{:s}.{:s}: {:s} {:s} ({:s})".format(__name__, inspect.currentframe().f_code.co_name, "wrong orientation", p_orientation,
          "represents a hidden bug, do not catch this"))

    for i in dict_widgets:
        sum_offsets = sum_offsets + dict_widgets[i]["OFFSET"]
        if orientation == "HORIZONTAL":
            sum_widgets = sum_widgets + dict_widgets[i]["RELW"]
        else:
            sum_widgets = sum_widgets + dict_widgets[i]["RELH"]
        num_widgets += 1
        factor = 1 / (sum_offsets + sum_widgets)
    nextpos = 0 # we always fill the whole parent area
    for i in dict_widgets:
        # construct the widget in parent
        b = dict_widgets[i]["WIDGET"](parent)
        # we have to find out if this widget is a radiobutton. if yes we need two special parameters: the variable associated with the group and the resp. value
        if dict_widgets[i]["WIDGET"] is tk.Radiobutton:
            if "RB_VAR" not in dict_widgets[i] or dict_widgets[i]["RB_VAR"] == "":
                raise ValueError("{:s}.{:s}: line {:s} {:s} {:s} ({:s})".format(__name__, inspect.currentframe().f_code.co_name, 
                  i, "parameter not specified for radio button", "RB_VAR",
                  "represents a hidden bug, do not catch this"))
            if "RB_VALUE" not in dict_widgets[i] or dict_widgets[i]["RB_VALUE"] == "":
                raise ValueError("{:s}.{:s}: line {:s} {:s} {:s} ({:s})".format(__name__, inspect.currentframe().f_code.co_name, 
                  i, "parameter not specified for radio button", "RB_VALUE",
                  "represents a hidden bug, do not catch this"))
            b.config(variable=dict_widgets[i]["RB_VAR"])
            b.config(value=dict_widgets[i]["RB_VALUE"], indicatoron = 0)
        t_text    = ""
        t_relsize = 0
        t_pos     = ""
        t_font = font # this is the default font if non i specified for the widget
        if "TITLE" in dict_widgets[i] and dict_widgets[i]["TITLE"] is not None:
            result = parse_title(dict_widgets[i]["TITLE"])
            if result is None:
                raise ValueError("{:s}.{:s}: line {:s} {:s} {:s} ({:s})".format(__name__, inspect.currentframe().f_code.co_name, 
                  i, "wrong expression", dict_widgets[i]["TITLE"],
                  "represents a hidden bug, do not catch this"))
            else:
                t_text, t_relsize, t_pos = result
                print("TITLE text:{:s}, relsize:{:f}, position:{:s}".format(t_text, t_relsize, t_pos)) if debug else True
            title_yn = 'y'
        else:
            title_yn = 'n'
        if "FONT" in dict_widgets[i] and dict_widgets[i]["FONT"] is not None: # if we have a font, we use it also for text-label 
            b.config(font=dict_widgets[i]["FONT"])
            t_font = dict_widgets[i]["FONT"]
            
        if orientation == "HORIZONTAL":
            offset = dict_widgets[i]["OFFSET"] * factor
            relh   = dict_widgets[i]["RELH"]
            relw   = dict_widgets[i]["RELW"] * factor
            size_available = relh # the size available
            if relh >= 1: 
                relh = 1
            if dict_widgets[i]["ANCHOR"] == "START":
                dist = 0
            elif dict_widgets[i]["ANCHOR"] == "END":
                dist = 1 - relh
            elif dict_widgets[i]["ANCHOR"] == "CENTER":
                dist = (1 - relh) / 2
            else:
                raise ValueError("{:s}.{:s}: line {:s} {:s} {:s} ({:s})".format(__name__, inspect.currentframe().f_code.co_name, 
                  i, "wrong ANCHOR", dict_widgets[i]["ANCHOR"],
                  "represents a hidden bug, do not catch this"))
            if title_yn == 'y': # create Label and correct some values
                # Example: relh = 0.8, t_relsize = 0.3, after correction relh = 0.56, t_relsize = 0.3 * 0.8 = 0.24. Sum is .56 + .24 = 0.8
                relh = relh * (1 - t_relsize) # relh (heihgt of widget) has to be shared with label
                t_relsize = t_relsize * size_available
                if t_pos.upper() == "START":
                    # create the label
                    l = tk.Label(parent, text = t_text, font = font, bg = parent["bg"])
                    l.place(relx = nextpos + offset, rely=dist, relheight=t_relsize, relwidth = relw)
                    # now adjust dist for placement of widget
                    dist += t_relsize
                elif t_pos.upper() == "END":
                    # create the label
                    l = tk.Label(parent, text = t_text, font = t_font, bg = parent["bg"])
                    l.place(relx = nextpos + offset, rely=dist + relh, relheight=t_relsize, relwidth = relw)
            b.place(relx = nextpos + offset, rely=dist, relheight=relh, relwidth = relw)
            nextpos += relw + offset
        else: # must be vertical, we have checked this already
            offset = dict_widgets[i]["OFFSET"] * factor
            relh   = dict_widgets[i]["RELH"] * factor 
            relw   = dict_widgets[i]["RELW"]
            size_available = relw # the size available
            if relw >= 1: 
                relw = 1
            if dict_widgets[i]["ANCHOR"] == "START":
                dist = 0
            elif dict_widgets[i]["ANCHOR"] == "END":
                dist = 1 - relw
            elif dict_widgets[i]["ANCHOR"] == "CENTER":
                dist = (1 - relw) / 2
            else:
                raise ValueError("{:s}.{:s}: line {:s} {:s} {:s} ({:s})".format(__name__, inspect.currentframe().f_code.co_name, 
                  i, "wrong ANCHOR", dict_widgets[i]["ANCHOR"],
                  "represents a hidden bug, do not catch this"))
            if title_yn == 'y': # create Label and correct some values
                # Example: relw = 0.8, t_relsize = 0.3, after correction relw = 0.56, t_relsize = 0.3 * 0.8 = 0.24. Sum is .56 + .24 = 0.8
                relw = relw* (1 - t_relsize) # relw (width of widget) has to be shared with label
                t_relsize = t_relsize * size_available
                if t_pos.upper() == "START":
                    # create the label
                    l = tk.Label(parent, text = t_text, font = font, bg = parent["bg"])
                    l.place(relx = dist, rely=nextpos + offset, relheight=relh, relwidth = t_relsize)
                    # now adjust dist for placement of widget
                    dist += t_relsize
                elif t_pos.upper() == "END": # we have to leave place for the title above the widget
                    # create the label
                    l = tk.Label(parent, text = t_text, font = t_font, bg = parent["bg"])
                    l.place(relx = dist + relw, rely=nextpos + offset, relheight=relh, relwidth = t_relsize)
            b.place(relx = dist, rely=nextpos + offset, relheight=relh, relwidth = relw)
            nextpos += relh + offset
        if "TEXT" in dict_widgets[i] and dict_widgets[i]["TEXT"] is not None: 
            b.config(text=dict_widgets[i]["TEXT"])
        if "CALLBACK" in dict_widgets[i] and dict_widgets[i]["CALLBACK"] is not None: 
            b.config(command=dict_widgets[i]["CALLBACK"])
        if "STATE" in dict_widgets[i] and dict_widgets[i]["STATE"] is not None: 
            b.config(state=dict_widgets[i]["STATE"])
        if "VAR" in dict_widgets[i] and dict_widgets[i]["VAR"] is not None: 
            setattr(caller, dict_widgets[i]["VAR"], b)
        else: #VAR must be given
            raise ValueError("{:s}.{:s}: line {:s} {:s} {:s} ({:s})".format(__name__, inspect.currentframe().f_code.co_name, 
              i, "parameter not specified", "VAR",
              "represents a hidden bug, do not catch this"))
        if "TT" in dict_widgets[i] and dict_widgets[i]["TT"] is not None: # we need a variable for the tooltip
            setattr(caller, dict_widgets[i]["VAR"] + "_tooltip", TT.ToolTip(b, dict_widgets[i]["TT"]))
 

def parse_title(s):
    # helper function for create_widgets_from_dict
    pattern = re.compile(r"^\s*(['\"])(.*?)\1\s*,\s*([0-9]*\.?[0-9]+)\s*,\s*(START|END)\s*$")
    m = pattern.match(s)
    if not m:
        return None
    text, relsize, pos = m.group(2), float(m.group(3)), m.group(4)
    return text, relsize, pos

def create_buttons_from_dict(caller, dict_buttons, frame, startpos, rgwidth, relsize, fon, orientation): # create Buttons in horizontal Frame
    # calculate rel width considering the offsets
    num_buttons = 0
    relw = 0.0
    sum_offsets = 0
    # part of frame to use for group of buttons
    rel_group_width = rgwidth
    for i in dict_buttons:
        sum_offsets = sum_offsets + dict_buttons[i]["OFFSET"] 
        num_buttons += 1
    relw  = (rel_group_width - sum_offsets) / num_buttons
    nextpos = startpos #<== set rel. start position
    for i in dict_buttons:
        offset = dict_buttons[i]["OFFSET"]
        b = dict_buttons[i]["WIDGET"](frame, text=dict_buttons[i]["TEXT"], command=dict_buttons[i]["CALLBACK"], state=dict_buttons[i]["STATE"])
        if orientation.upper() == "HORIZONTAL":
            b.place(relx = nextpos + offset, rely=(1 - relsize) / 2, relheight=relsize, relwidth = relw)
        elif orientation.upper() == "VERTICAL":
            b.place(relx = (1 - relsize) / 2, rely=nextpos + offset, relheight=relw, relwidth = relsize)
        else:
            raise ValueError(orientation + ' Represents a hidden bug, do not catch this')
        b.configure(font=fon)
        setattr(caller, dict_buttons[i]["VAR"], b)
        setattr(caller, dict_buttons[i]["VAR"] + "_tooltip", TT.ToolTip(b, dict_buttons[i]["TT"]))
        nextpos += relw + offset

def place_box_with_scrollbars(caller, frame, element, sb_h, sb_v, rw, d_n, d_e, d_s, d_w):
    # this function places a listbox or other scrollable element in a given Frame with horizontal and vertical scrollbars
    # element ist the element to be placed, sb_h and sb_v the scrollbars (horizonzal, vertical)
    # d_n, d_e, d_s, d_w are the rel. distances from the frame borders (North, east, south, west.
    # the box with the scrollbars fills the area in the frame completely.
    # the last parameter is the font
    # the relative width is given with respect to the listbox to be constructed, so we have to correct it according to its rel. width
    # The height of the horizontal scrollbar is the same as the width of the vertical scrollbar
    # on call the frame is given and the width of the vertical scrollbar. 
    
    # scrollbar width as fraction of frame-width
    parent_width_in_pixel  = frame.winfo_width()
    parent_height_in_pixel = frame.winfo_height()
    area_width_in_pixel  = parent_width_in_pixel * (1 - d_w - d_e)
    area_height_in_pixel = parent_height_in_pixel * (1 - d_n - d_s)
    factor = parent_width_in_pixel / parent_height_in_pixel
    rel_size_sb_x = rw * area_width_in_pixel / parent_width_in_pixel
    rel_size_sb_y = rel_size_sb_x * factor # width relative to y
    element_width  = area_width_in_pixel / parent_width_in_pixel - rel_size_sb_x
    element_height = area_height_in_pixel / parent_height_in_pixel - rel_size_sb_y
    element.place(relx = d_w, rely = d_n, relheight = element_height, relwidth = element_width, anchor = tk.NW)     
    sb_h.place(relx = d_w, rely = d_n + element_height, relheight = rel_size_sb_y, relwidth = element_width, anchor = tk.NW)
    sb_v.place(relx = d_w + element_width, rely = d_n, relheight = element_height, relwidth = rel_size_sb_x, anchor = tk.NW)

def create_checkboxes_from_dict(caller, dict_controls, frame, startpos, rgwidth, relsize, fon, orientation, bgcolor): # create Buttons in horizontal Frame
    # calculate rel width considering the offsets
    num_controls = 0
    relw = 0.0
    sum_offsets = 0
    # part of frame to use for group of buttons
    rel_group_width = rgwidth
    for i in dict_controls:
        sum_offsets = sum_offsets + dict_controls[i]["OFFSET"] 
        num_controls += 1
    relw  = (rel_group_width - sum_offsets) / num_controls
    nextpos = startpos #<== set rel. start position
    for i in dict_controls:
        offset = dict_controls[i]["OFFSET"]
        b = tk.Checkbutton(frame, text=dict_controls[i]["TEXT"], command=dict_controls[i]["CALLBACK"], anchor='w')
        if orientation.upper() == "HORIZONTAL":
            b.place(relx = nextpos + offset, rely=(1 - relsize) / 2, relheight=relsize, relwidth = relw)
        elif orientation.upper() == "VERTICAL":
            b.place(relx = (1 - relsize) / 2, rely=nextpos + offset, relheight=relw, relwidth = relsize)
        else:
            raise ValueError(orientation + ' Represents a hidden bug, do not catch this')
        b.configure(font=fon)
        v = tk.IntVar()
        v.set(dict_controls[i]["STATE"])
        setattr(caller, dict_controls[i]["VAR"], b) # the variable for the control
        setattr(caller, dict_controls[i]["VAR"] + "_var", v) # the variable
        setattr(caller, dict_controls[i]["VAR"] + "_tooltip", TT.ToolTip(b, dict_controls[i]["TT"])) # the tooltip
        b.configure(variable=v, background = bgcolor)
        nextpos += relw + offset


class Globals:
    imagetype = ""
    generated = False # set to true if generated, set to false after selection of camera
    screen_width = 0
    screen_height = 0
    uncomment = ""
    gap = 10
    config_files_xml    = None
    config_files_subdir = None
    cmd_files_subdir    = None
    datadir = ""
    dict_thumbnails = {}
    dict_duplicates = {}
    outdir = ""
    list_result_diatisch = []
    resized = False # only temporary set to True on resize window

def info_box(nachricht, level="info"):
    """
    Zeigt eine Box mit Source-Infos an.
    level: "info", "warnung" oder "fehler" (beendet Programm)
    """
    caller = inspect.currentframe().f_back
    datei = os.path.basename(caller.f_code.co_filename)
    zeile = caller.f_lineno
    funktion = caller.f_code.co_name
    
    # Herkunft zusammenbauen
    klasse = caller.f_locals.get('self').__class__.__name__ + "." if 'self' in caller.f_locals else ""
    source_info = f"\n\n[Ort: {datei} -> {klasse}{funktion}() -> Zeile {zeile}]"
    
    voller_text = f"{nachricht}{source_info}"

    if level.lower() == "fehler":
        mb.showerror("Kritischer Fehler", voller_text)
        sys.exit()  # Beendet das Programm sofort
    elif level.lower() == "warnung":
        mb.showwarning("Warnung", voller_text)
    else:
        mb.showinfo("Information", voller_text)

class BusyDialog:
    def __init__(self, root, title="Bitte warten", text="Vorgang läuft…"):
        self.root = root
        self.cancelled = False

        self.dialog = tk.Toplevel(root)
        self.dialog.title(title)
        self.dialog.geometry("320x180")
        self.dialog.resizable(False, False)

        # Modal
        self.dialog.transient(root)
        self.dialog.grab_set()

        # Cursor
        self.dialog.config(cursor="watch")
        root.config(cursor="watch")

        # Text
        self.label_text = tk.Label(self.dialog, text=text)
        self.label_text.pack(pady=10)

        # Fortschrittsbalken
        self.progress = ttk.Progressbar(self.dialog, orient="horizontal",
                                        length=250, mode="determinate")
        self.progress.pack(pady=5)

        # Prozentanzeige
        self.label_progress = tk.Label(self.dialog, text="0 %")
        self.label_progress.pack()

        # Abbrechen-Knopf
        self.button_cancel = tk.Button(self.dialog, text="Abbrechen",
                                       command=self._cancel)
        self.button_cancel.pack(pady=10)

        self.dialog.update()

    def _cancel(self):
        self.cancelled = True

    def update_progress(self, current, total):
        percent = int(current / total * 100)

        # Fortschrittsbalken aktualisieren
        self.progress["value"] = percent

        # Text aktualisieren
        self.label_progress.config(text=f"{percent} %   ({current} / {total})")

        # GUI aktualisieren
        self.dialog.update()

    def close(self):
        self.dialog.destroy()
        self.root.config(cursor="")
        self.root.update()

class RestartableTimer:
    def __init__(self, root, interval_ms, callback):
        self.root = root
        self.interval_ms = interval_ms
        self.callback = callback
        self._timer_id = None

    def start(self):
        self.cancel()  # Falls bereits laufend, abbrechen
        self._timer_id = self.root.after(self.interval_ms, self._execute)

    def cancel(self):
        if self._timer_id is not None:
            self.root.after_cancel(self._timer_id)
            self._timer_id = None

    def _execute(self):
        self._timer_id = None
        self.callback()
        
class MyThumbnail:
    #image = "" # hier stehen Klassenvariablen, im Gegensatz zu den Instanzvariablen

    # The class "constructor" - It's actually an initializer 
    def __init__(self, image, pmain, start, end, file, mts, showfile, id, text_id, rect_id, frameids, lineno, player, duplicate, canvas, targetfile, \
      text = None, parent = None, tooold = False):
        self.main = pmain
        self.image = image
        self.start = start
        self.end   = end
        self.file = file
        self.mts  = mts
        self.showfile = showfile
        self.image_id = id
        self.state_id_text = text_id
        self.state_id_rect = rect_id
        self.frameids = frameids
        self.lineno = lineno
        self.player = player 
        self.targetfile = targetfile
        self.fsimage = None
        self.dupl = None
        self.state = INCLUDE
        self.canvas = canvas
        self.text = text
        self.parent = parent
        self.duplicate = duplicate
        self.tooold = tooold
        self.setState(self.state)

        statinfo = os.stat(file)
        st_ctime = statinfo.st_ctime
        st_mtime = statinfo.st_mtime
        self.filectime = datetime.fromtimestamp(st_ctime).strftime('%Y-%m-%d %H:%M')
        self.filemtime = datetime.fromtimestamp(st_mtime).strftime('%Y-%m-%d %H:%M')
        self.filesize  = os.stat(file).st_size/(1024*1024.0) 
        self.frame_selected = False # we need this for Resize of Window in order to hide / show dotted rect
        
    def get_filectime(self):
        return self.filectime
        
    def get_filemtime(self):
        return self.filemtime
        
    def get_filesize(self):
        return self.filesize
                
    def updateIds(self, text_id, rect_id, frameids): #necessary after sort when thumbnail is reused, but items in canvas are created new
        self.state_id_text = text_id
        self.state_id_rect = rect_id
        self.frameids = frameids

    def getImage(self):
        #print("*** retrieve Image ")
        return self.image    

    def setImage(self, image):
        #print("*** retrieve Image ")
        self.image = image    

    def setPlayer(self, p):
        self.player = p
        
    def setStart(self, start):
        self.start = start   

    def getStart(self):
        return self.start    

    def setEnd(self, end):
        self.end = end   

    def getEnd(self):
        return self.end    

    def getFile(self):
        return self.file    
    def getShowfile(self):
        return self.showfile    

    def setId(self, id):
        self.image_id = id    
    def getId(self):
        return self.image_id    

    def set_tooold(self, tooold):
        self.tooold = tooold    
    def get_tooold(self):
        return self.tooold    

    def getDuplicate(self):
        return self.duplicate    

    def setState(self, state, caller = None, do_save = True):
        if state != self.state:
            state_changed = True
        else:
            state_changed = False
        self.state = state # neuer Status
        if self.text is not None:
            # change line in text
            # die Textzeile beschaffen
            lstart = "%d.0" % (self.lineno)
            lend   = "%d.0 lineend" % (self.lineno)
            # tindex = "%d.0, %d.0 lineend" % (lineno, lineno + 1)
            line    = self.text.get(lstart, lend)
            #print ("Retrieved Textline: " + line)
        if self.state == INCLUDE:
            self.canvas.itemconfigure(self.state_id_text, state='hidden')
            self.canvas.itemconfigure(self.state_id_rect, state='hidden')
            if self.text is not None:
                linenew = line
                linenew = re.sub(rf"{Globals.uncomment}", '', linenew)
                self.text.delete(lstart, lend) # without delete / insert highlighttag does not work. Bug in Python?
                self.text.insert(lstart, line)
                self.text.tag_add("include", lstart, lend) # normal foreground
                self.scrollTextToLineno()
        if self.state == EXCLUDE and state_changed:
            self.canvas.itemconfigure(self.state_id_text, state='normal')
            self.canvas.itemconfigure(self.state_id_rect, state='normal')
            if self.text is not None:
                linenew = line
                linenew = re.sub(r"^", f"{Globals.uncomment}", linenew)
                self.text.delete(lstart, lend) # without delete / insert highlighttag does not work. Bug in Python?
                self.text.insert(lstart, line)
                self.text.tag_add("exclude", lstart, lend) # exclude foreground(grey)
                self.scrollTextToLineno()
        if self.parent is not None:
            self.parent.setState(state, caller)
        if self.fsimage is not None:
            self.fsimage.exclude_call(state) # synchronisiert das FSImge, falls vorhanden
            print("FSImage Exclude-Call")
        if self.dupl is not None:
            #print("dupl is: " + str(self.dupl) + "caller is: " + str(caller))
            if caller != self.dupl: # to avoid loop
                self.dupl.exclude_call(self, state) # synchronisiert das Duplicate, falls vorhanden
                #print("Duplicate Exclude-Call")
        if state_changed and do_save:
            self.main.write_cmdfile(Globals.imagetype)
            print ("setState: SAVE requested")
    def getState(self):
        return self.state   

    def getLineno(self):
        return self.lineno    

    def setLineno(self, lineno):
        self.lineno = lineno 
        
    def scrollTextToLineno(self): # reset all lines to "unselect", keep exclude / include Info, hide frame
        for t in Globals.thumbnails[Globals.imagetype]:
            lineno = t.getLineno()
            lstart = "%d.0" % (lineno)
            lend   = "%d.0 lineend" % (lineno)
            line    = self.text.get(lstart, lend) # text widget is the same for all thumbnails
            # without delete / insert tag_add will not work. Bug in tkinter?
            self.text.delete(lstart, lend) # without delete / insert highlighttag does not work. Bug in Python?
            self.text.insert(lstart, line)
            #print("try to select line " + line)
            if t.getState() == INCLUDE:
                self.text.tag_add("normal_include", lstart, lend)
            else:
                self.text.tag_add("normal_exclude", lstart, lend)
            self.canvas.itemconfigure("imageframe", state = 'hidden')
            self.frame_selected = False
        # now set tag for this thumbnail
        lstart = "%d.0" % (self.lineno)
        lend   = "%d.0 lineend" % (self.lineno)
        line    = self.text.get(lstart, lend)
        # without delete / insert tag_add will not work. Bug in tkinter?
        self.text.delete(lstart, lend) # without delete / insert highlighttag does not work. Bug in Python?
        self.text.insert(lstart, line)
        #self.text.mark_set(tk.INSERT, "%d.%d" % (self.lineno, 0))
        #print("try to select line " + line)
        if self.getState() == INCLUDE:
            self.text.tag_add("select_include", lstart, lend)
        else:
            self.text.tag_add("select_exclude", lstart, lend)
        self.text.see(lstart)
        lineinfo = self.text.dlineinfo(lstart)
        self.text.yview_scroll(lineinfo[1], 'pixels' )
        #self.canvas.itemconfigure("imageframe", state = 'normal')
        #print("Frameids: " + str(self.frameids))
        self.frame_selected = True
        self.show_hide_frame()

    def show_hide_frame(self):
        if self.frame_selected:
            for frameid in self.frameids:
                self.canvas.itemconfigure(frameid, state = 'normal')
        else:
            self.canvas.itemconfigure("imageframe", state = 'hidden')
 
    def register_FSimage(self, fsimage):
        self.fsimage = fsimage

    def register_Dupl(self, dupl):
        self.dupl = dupl

    def getPlayer(self):
        return self.player   

    def getTargetfile(self):
        return self.targetfile   

    def __del__(self):
        if self.player is not None:
            self.player.pstop()
            del self.player
        width = self.end -self.start 
        #print("*** Deleting MyThumbnail-Objekt. " + self.file + " lineno in cmdfile " + str(self.lineno))

# The following code is added to facilitate the Scrolled widgets
class AutoScroll(object):
    '''Configure the scrollbars for a widget.'''
    def __init__(self, master):
        try: #if which vertical scrolling is not supported...
            vsb = ttk.Scrollbar(master, orient='vertical', command=self.yview)
        except:
            pass
        hsb = ttk.Scrollbar(master, orient='horizontal', command=self.xview)
        try:
            self.configure(yscrollcommand=self._autoscroll(vsb))
        except:
            pass
        self.configure(xscrollcommand=self._autoscroll(hsb))
        self.grid(column=0, row=0, sticky='nsew')
        try:
            vsb.grid(column=1, row=0, sticky='ns')
        except:
            pass
        hsb.grid(column=0, row=1, sticky='ew')
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(0, weight=1)
        # Copy geometry methods of master  (taken from ScrolledText.py)
        methods = tk.Pack.__dict__.keys() | tk.Grid.__dict__.keys() \
                  | tk.Place.__dict__.keys()
        for meth in methods:
            if meth[0] != '_' and meth not in ('config', 'configure'):
                setattr(self, meth, getattr(master, meth))

    @staticmethod
    def _autoscroll(sbar):
        '''Hide and show scrollbar as needed.'''
        def wrapped(first, last):
            first, last = float(first), float(last)
            if first <= 0 and last >= 1:
                sbar.grid_remove()
            else:
                sbar.grid()
            sbar.set(first, last)
        return wrapped

    def __str__(self):
        return str(self.master)

def _create_container(func):
    '''Creates a ttk Frame with a given master, and use this new frame to
    place the scrollbars and the widget.'''
    def wrapped(cls, master, **kw):
        container = ttk.Frame(master)
        container.bind('<Enter>', lambda e: _bound_to_mousewheel(e, container))
        container.bind('<Leave>', lambda e: _unbound_to_mousewheel(e, container))
        return func(cls, container, **kw)
    return wrapped

class ScrolledTreeView(AutoScroll, ttk.Treeview):
    '''A standard ttk Treeview widget with scrollbars that will
    automatically show/hide as needed.'''
    @_create_container
    def __init__(self, master, **kw):
        ttk.Treeview.__init__(self, master, **kw)
        AutoScroll.__init__(self, master)

import platform
def _bound_to_mousewheel(event, widget):
    child = widget.winfo_children()[0]
    if platform.system() == 'Windows' or platform.system() == 'Darwin':
        child.bind_all('<MouseWheel>', lambda e: _on_mousewheel(e, child))
        child.bind_all('<Shift-MouseWheel>', lambda e: _on_shiftmouse(e, child))
    else:
        child.bind_all('<Button-4>', lambda e: _on_mousewheel(e, child))
        child.bind_all('<Button-5>', lambda e: _on_mousewheel(e, child))
        child.bind_all('<Shift-Button-4>', lambda e: _on_shiftmouse(e, child))
        child.bind_all('<Shift-Button-5>', lambda e: _on_shiftmouse(e, child))

def _unbound_to_mousewheel(event, widget):
    if platform.system() == 'Windows' or platform.system() == 'Darwin':
        widget.unbind_all('<MouseWheel>')
        widget.unbind_all('<Shift-MouseWheel>')
    else:
        widget.unbind_all('<Button-4>')
        widget.unbind_all('<Button-5>')
        widget.unbind_all('<Shift-Button-4>')
        widget.unbind_all('<Shift-Button-5>')

def _on_mousewheel(event, widget):
    if platform.system() == 'Windows':
        widget.yview_scroll(-1*int(event.delta/120),'units')
    elif platform.system() == 'Darwin':
        widget.yview_scroll(-1*int(event.delta),'units')
    else:
        if event.num == 4:
            widget.yview_scroll(-1, 'units')
        elif event.num == 5:
            widget.yview_scroll(1, 'units')

def _on_shiftmouse(event, widget):
    if platform.system() == 'Windows':
        widget.xview_scroll(-1*int(event.delta/120), 'units')
    elif platform.system() == 'Darwin':
        widget.xview_scroll(-1*int(event.delta), 'units')
    else:
        if event.num == 4:
            widget.xview_scroll(-1, 'units')
        elif event.num == 5:
            widget.xview_scroll(1, 'units')
