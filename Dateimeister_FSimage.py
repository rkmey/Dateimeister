#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

# hier speichern wir die full-size-Bilder

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

import Dateimeister
import dateimeister_video as DV

INCLUDE = 1
EXCLUDE = 2


class MyFSImage:

    # The class "constructor" - It's actually an initializer 
    def __init__(self, file, thumbnail, dict_caller, pmain, str_title_prefix, str_include, str_exclude, str_included, str_excluded, debug): 
        self.main = pmain
        self.thumbnail = thumbnail
        self.player = None
        self.str_include = str_include
        self.str_exclude = str_exclude
        self.str_included = str_included
        self.str_excluded = str_excluded
        self.debug = debug
        if thumbnail.getPlayer() is None: # still image
            self.image  = Image.open(file)
        self.file = file
        self.dict_caller = dict_caller
        # register at thumbnail, so it can call us for reacting to state
        self.thumbnail.register_FSimage(self)
        # Create secondary (or popup) window.
        self.root = tk.Toplevel(name = "fsimage")
        self.w2 = Dateimeister.Toplevel2(self.root)

        # create the canvas
        self.f = tk.Canvas(self.root)
        self.f.place(relx=0.0, rely=0.0, relheight=1.0, relwidth=0.75)
        self.f.configure(background="#d9d9d9")
        self.f.configure(borderwidth="2")
        self.f.configure(highlightbackground="#d9d9d9")
        self.f.configure(highlightcolor="black")
        self.f.configure(insertbackground="black")
        self.f.configure(relief="ridge")
        self.f.configure(selectbackground="#c4c4c4")
        self.f.configure(selectforeground="black")

        if self.thumbnail.getState() == INCLUDE:
            self.w2.Button_exclude.config(text = self.str_exclude)
            self.w2.Label_status.config(text = self.str_included)
        else: # toggle to not exclude
            self.w2.Button_exclude.config(text = self.str_include)
            self.w2.Label_status.config(text = self.str_excluded)
        # zur Behandlung von Events brauchen wir den Imagefile-Namen. Darüber kommen wir an das Window und
        # das Image selbst. Das ist erforderlich, weil wir ja mehrere Fenster haben können
        # kurz gesagt: mit dieser Methode kann man Parameter an den Handler übergeben
        self.w2.Button_fit.config(command = self.fit_handler)
        self.w2.Button_fscale.config(command = self.fscale_handler)
        self.w2.Button_exclude.config(command = self.exclude_handler)
        self.w2.Button_pp.config(command = self.pp_handler)
        self.w2.Button_restart.config(command = self.restart_handler)
        self.w2.Scale_fps.config(command = self.setFps)
        self.f.bind("<MouseWheel>", self.mousewheel_handler)
        self.root.protocol("WM_DELETE_WINDOW", self.close_handler)

        self.root.title(str_title_prefix + file)
        screen_width  = int(self.root.winfo_screenwidth() * 0.9)
        screen_height = int(self.root.winfo_screenheight() * 0.8)
        print("Bildschirm ist " + str(screen_width) + " x " + str(screen_height))
        width,height=screen_width,screen_height
        v_dim=str(width)+'x'+str(height)
        self.root.geometry(v_dim)
        self.root.resizable(True, True)

        # Scrollbars
        self.V_I = Scrollbar(self.f)
        self.V_I.config(command=self.f.yview)
        self.f.config(yscrollcommand=self.V_I.set)  
        self.H_I = Scrollbar(self.f, orient = HORIZONTAL)
        self.H_I.config(command=self.f.xview)
        self.f.config(xscrollcommand=self.H_I.set)
        if thumbnail.getPlayer() is None:
            self.image.close
        self.zoomfaktor = 1.0
        self.V_I.pack(side=RIGHT, fill=Y)
        self.H_I.pack(side=BOTTOM, fill=BOTH)
        # Bind keys to canvas for scrolling
        self.f.bind("<Left>",  lambda event: self.scrollx(-1, "unit"))
        self.f.bind("<Right>", lambda event: self.scrollx( 1, "unit"))
        self.f.bind("<Up>",    lambda event: self.scrolly(-1, "unit"))
        self.f.bind("<Down>",  lambda event: self.scrolly( 1, "unit"))

        self.zoomfaktor = 1.0 # wir fangen immer mit dem Bild in voller Auflösung an.
        self.f.focus_set()
        if thumbnail.getPlayer() is None: # still image
            self.image_zoom(self.zoomfaktor)
            self.player = None
            self.w2.Button_pp.place_forget()
            self.w2.Button_restart.place_forget()
            self.w2.Scale_fps.place_forget()
            self.w2.Label_fps.place_forget()
        else: #video, we need a new one the existing is for playing in thumbnal
            self.w2.Button_fit.place_forget()
            self.w2.Button_fscale.place_forget()
            self.H_I.pack_forget()
            self.V_I.pack_forget()
            self.f.update()
            self.player   = DV.VideoPlayer(self.root, self.file, self.f, self.f.winfo_width(), self.f.winfo_height())
            self.image_width, self.image_height, self.pimg = self.player.get_photo()  
            print(file, " height / width: ",  self.image_width, self.image_height)
            self.id = self.f.create_image(0, 0, anchor='nw',image = self.pimg, tags = 'images')
            self.f.tag_raise("text")
            self.f.tag_raise("line")
            self.player.setId(self.id)
            self.player.resize()
            self.player.pstart()
            fps = self.player.getFPS()
            self.player.setDelay(int(1000 / fps))
            self.w2.Scale_fps.set(int(1000 / fps))
            self.playerstatus = 'play'
            self.w2.Button_pp.config(text = 'pause')
            #self.image = self.player.get_image()
            
        # frame for Label displaying file info start at  0,75 (width of canvas
        self.text_font = Font(family="Helvetica", size=6)
        self.Frame_labels = tk.Frame(self.root)
        self.Frame_labels.place(relx=.75, rely=0.00, relheight=0.1, relwidth=0.2)
        self.Frame_labels.configure(relief='flat')
        self.Frame_labels.configure(background="#d9d9d9") if self.debug else True # uncomment for same colour as window (default) or depend on debug
        self.Label_fileinfo = tk.Label(self.Frame_labels)
        self.Label_fileinfo.place(relx=0.0, rely=0.0, relheight=1, relwidth=1)
        self.Label_fileinfo.configure(anchor=tk.NW)
        self.Label_fileinfo.configure(font=self.text_font)
        mytext = "{:s}\n created {:s} size {:.3f}".format(thumbnail.getFile(), thumbnail.get_filectime(), thumbnail.get_filesize())
        self.Label_fileinfo.configure(text=mytext)
        self.width  = 0
        self.height = 0
        self.adjust_zoom = 0
        self.timer = Dateimeister.RestartableTimer(self.root, 666, self.resize)  # ms
        self.root.bind("<Configure>", self.on_configure) # we want to know if size changes
    
        
    def on_configure(self, event):
        x = event.widget
        self.adjust_zoom = 1.0
        if x == self.root:
            if (self.width != event.width or self.height != event.height):
                if self.player: # Video we have to pause the player
                    self.player.pstop()
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
            # we have to change fontsize according to Minimum of new Height / width
            fontsize_width  = int(new_width * .025) 
            #fontsize_height = int(.7 * min(12.0, new_height * .75))
            fontsize_height = int(new_height * .025)
            fontsize_use = min(fontsize_width, fontsize_height)
            # we calculate the correction factor for zoom
            if old_width != 0 and old_height != 0 and new_width != 0 and new_height != 0:
                self.adjust_zoom = min(new_width / old_width, new_height / old_height)
            else:    
                self.adjust_zoom = 1.0
            print(f"RESIZE: new width {new_width} new height {new_height} set fontsize to {fontsize_use}, old width = {old_width}, old height = {old_height}, zoomadjust = {self.adjust_zoom}") if self.debug else True
            self.text_font.configure(size=fontsize_use) 
        self.zoomfaktor = self.zoomfaktor * self.adjust_zoom
        self.image_zoom(self.zoomfaktor)

    def debug_info_resize(self, text):
        print("{:s} elapsed start resize".format(text))

    def getPlayer(self):
        return self.player
    
    def scrollx(self, amount, unit):
        #print("scroll command: " + str(amount) + ' ' + unit)
        self.f.xview_scroll(amount, unit)
        return "break"
    def scrolly(self, amount, unit):
        #print("scroll command: " + str(amount) + ' ' + unit)
        self.f.yview_scroll(amount, unit)
        return "break"
     
    def fit_handler(self):
        self.button_fit()

    def pp_handler(self):
        if self.playerstatus == 'play': 
            self.player.pstop()
            self.playerstatus = 'pause'
            self.w2.Button_pp.config(text = 'play')
        else:
            self.player.pstart()
            self.playerstatus = 'play'
            self.w2.Button_pp.config(text = 'pause')

    def setPlaystatus(self, newstatus):
        if newstatus == 'play': 
            self.playerstatus = 'play'
            self.w2.Button_pp.config(text = 'pause')
        else:
            self.playerstatus = 'pause'
            self.w2.Button_pp.config(text = 'play')

    def restart_handler(self):
        self.player.restart()
        self.setPlaystatus('play')

    def fscale_handler(self):
        self.image_zoom(1) # damit bringt image_zoom das Foto in höchster Auflösung zur Anzeige
        
    def setFps(self, value):
        self.player.setDelay(int(1000 / int(value)))

    def exclude_handler(self): # react to own Button, thumbnail can be from main or duplicates
        # Button -> this method -> thumbnail.setstate -> exclude_call
        if self.thumbnail.getState() == INCLUDE:
            self.w2.Button_exclude.config(text = self.str_include)
            self.w2.Label_status.config(text = self.str_excluded)
            self.thumbnail.setState(EXCLUDE)
        else: # toggle to not exclude, delete Item
            self.w2.Button_exclude.config(text = self.str_exclude)
            self.w2.Label_status.config(text = self.str_included)
            self.thumbnail.setState(INCLUDE)
        self.main.historize_process()

    def exclude_call(self, state): # react to request from outside
        print("MyFSImage.exclude_call, state = {:d}".format(state)) if self.debug else True
        if state == INCLUDE:
            self.w2.Button_exclude.config(text = self.str_exclude)
            self.w2.Label_status.config(text = self.str_included)
        else: # toggle to not exclude, delete Item
            self.w2.Button_exclude.config(text = self.str_include)
            self.w2.Label_status.config(text = self.str_excluded)
    
    def close_handler(self): #calles when window is closing: delete player and fsimage, remove from dict_file_image
        t = self.dict_caller[self.file]
        self.thumbnail.register_FSimage(None)
        self.dict_caller.pop(self.file)
        if self.player is not None:
            self.player.pstop()
            del self.player
        self.root.destroy()
        del t
        
    def close_handler_external(self): # called from external. Do the same things as close_handler, except remove from dict_file_image
        # can be called from main window or Duplicates-Window which use different dicts
        t = self.dict_caller[self.file]
        self.thumbnail.register_FSimage(None)
        if self.player is not None:
            self.player.pstop()
            del self.player
        self.root.destroy()
        del t
        
    def mousewheel_handler(self, event):
        if self.player is None: # exception when used for video
            zoomincrement = (event.delta / 120) / 100 # Windows-spezifisch, macOS: keine Division durch 120
            if (zoomincrement > 0):
                if self.zoomfaktor + zoomincrement <= 1:
                    newzoomfaktor = self.zoomfaktor + zoomincrement
                else:
                    newzoomfaktor = 1.0
            else: # lt 0
                if self.zoomfaktor + zoomincrement >= .1:
                    newzoomfaktor = self.zoomfaktor + zoomincrement
                else:
                    newzoomfaktor = 0.1
            #print ("Mousewheel Delta is " + str(event.delta) + " Zoomfaktor old / new is: " + str(self.zoomfaktor) + ' / ' + str(newzoomfaktor))
            self.zoomfaktor = newzoomfaktor
            self.image_zoom(self.zoomfaktor)

    def button_fit(self):
        self.image_zoom(0) # damit bringt image_zoom das Foto vollständig und canvas-füllend zur Anzeige

    def image_zoom(self, zoomfaktor):
        # zoomfaktor 0 heißt: selbst errechnen, so dass Bild formatfüllend ist.
        if self.thumbnail.getPlayer() is None: # still image
            image_width_orig, image_height_orig = self.image.size
        else:
            image_width_orig  =self.image_width
            image_height_orig =self.image_height
        self.f.update()
        canvas_width  = self.f.winfo_width()
        canvas_height = self.f.winfo_height()
        if  zoomfaktor == 0: # wir brauchen die Scrollbars nicht und errechnen den formatfüllenden Zoomfaktor
            #self.V_I.pack_forget()
            #self.H_I.pack_forget()
            faktor = min(canvas_height / image_height_orig, canvas_width / image_width_orig)
            self.zoomfaktor = faktor
            print("... calculate faktor for Image to fit in Canvas")
        else:
            #self.V_I.pack(side=RIGHT, fill=Y)
            #self.H_I.pack(side=BOTTOM, fill=BOTH)
            faktor = zoomfaktor
            self.zoomfaktor = faktor
            
        newsize = (int(image_width_orig * faktor), int(image_height_orig * faktor))
        #print("*** faktor is: " + str(faktor) + " canvas_height: " + str(canvas_height) + " origsize: " + str(self.image.size) + " newsize: " +str(newsize))
        if self.thumbnail.getPlayer(): # Video we have to resize the player
            # video size is calculated automatically as the display process uses the actual canvas size, but we have to redraw the progress bar
            # start the player again which has been stopped in on configure
            self.player.resize()
            self.player.pstart()
        else:
            r_img = self.image.resize(newsize, Image.Resampling.NEAREST)
            self.pimg = ImageTk.PhotoImage(r_img)
            self.f.delete('images')
            #f.itemconfig(canvas_id, image = pimg)
            self.id = self.f.create_image(0, 0, anchor='nw',image = self.pimg, tags = 'images')
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
            
        self.f.config(scrollregion = self.f.bbox("all")) 

    def __del__(self):
        self.a = 1
        #print("*** Deleting FSImage-Objekt. File is " + str(self.file))
