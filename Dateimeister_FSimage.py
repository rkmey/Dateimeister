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
from time import gmtime, strftime

from PIL import Image, ImageTk
from datetime import datetime, timezone

import Dateimeister
import dateimeister_video as DV

INCLUDE = 1
EXCLUDE = 2


class MyFSImage:

    # The class "constructor" - It's actually an initializer 
    def __init__(self, file, thumbnail, dict_caller, pmain, delay_default, debug): # close_handler has to delete self from the dict main or duplicate
        self.main = pmain
        self.thumbnail = thumbnail
        self.player = None
        self.debug = debug
        if thumbnail.getPlayer() is None: # still image
            self.image  = Image.open(file)
        self.file = file
        self.dict_caller = dict_caller
        # register at thumbnail, so it can call us for reacting to state
        self.thumbnail.register_FSimage(self)
        # Create secondary (or popup) window.
        self.root2 = tk.Toplevel()
        self.w2 = Dateimeister.Toplevel2(self.root2)
        self.f = self.w2.Canvas_image
        if self.thumbnail.getState() == INCLUDE:
            self.w2.Button_exclude.config(text = "Exclude")
            self.w2.Label_status.config(text = "Included")
        else: # toggle to not exclude
            self.w2.Button_exclude.config(text = "Include")
            self.w2.Label_status.config(text = "Excluded")
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
        self.root2.protocol("WM_DELETE_WINDOW", self.close_handler)

        self.root2.title(file)
        screen_width  = int(self.root2.winfo_screenwidth() * 0.9)
        screen_height = int(self.root2.winfo_screenheight() * 0.8)
        print("Bildschirm ist " + str(screen_width) + " x " + str(screen_height))
        width,height=screen_width,screen_height
        v_dim=str(width)+'x'+str(height)
        self.root2.geometry(v_dim)
        self.root2.resizable(True, True)

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
            self.player   = DV.VideoPlayer(self.root2, self.file, self.f, self.f.winfo_width(), self.f.winfo_height(), 0)
            self.image_width, self.image_height, self.pimg = self.player.get_pimg()  
            print(file, " height / width: ",  self.image_width, self.image_height)
            self.id = self.f.create_image(0, 0, anchor='nw',image = self.pimg, tags = 'images')
            self.f.tag_raise("text")
            self.f.tag_raise("line")
            self.player.setId(self.id)
            self.player.pstart()
            self.player.setDelay(delay_default)
            self.w2.Scale_fps.set(1000 / delay_default)
            self.playerstatus = 'play'
            self.w2.Button_pp.config(text = 'pause')
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
            self.thumbnail.setState(EXCLUDE)
            self.w2.Button_exclude.config(text = "Include")
            self.w2.Label_status.config(text = "Excluded")
        else: # toggle to not exclude, delete Item
            self.thumbnail.setState(INCLUDE)
            self.w2.Button_exclude.config(text = "Exclude")
            self.w2.Label_status.config(text = "Included")
        self.main.historize_process()

    def exclude_call(self, state): # react to request from outside
        print("MyFSImage.exclude_call, state = {:d}".format(state)) if self.debug else True
        if state == INCLUDE:
            self.w2.Button_exclude.config(text = "Exclude")
            self.w2.Label_status.config(text = "Included")
        else: # toggle to not exclude, delete Item
            self.w2.Button_exclude.config(text = "Include")
            self.w2.Label_status.config(text = "Excluded")
    
    def close_handler(self): #calles when window is closing: delete player and fsimage, remove from dict_file_image
        t = self.dict_caller[self.file]
        self.thumbnail.register_FSimage(None)
        self.dict_caller.pop(self.file)
        if self.player is not None:
            self.player.pstop()
            del self.player
        self.root2.destroy()
        del t
        
    def close_handler_external(self): # called from external. Do the same things as close_handler, except remove from dict_file_image
        # can be called from main window or Duplicates-Window which use different dicts
        t = self.dict_caller[self.file]
        self.thumbnail.register_FSimage(None)
        if self.player is not None:
            self.player.pstop()
            del self.player
        self.root2.destroy()
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
        image_width_orig, image_height_orig = self.image.size
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
