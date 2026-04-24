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

