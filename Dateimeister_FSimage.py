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

import tools
import dateimeister_video as DV
import Tooltip as TT

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
        if thumbnail.get_imagetype() == "STILL": # still image
            self.image  = Image.open(file)
        self.file = file
        self.dict_caller = dict_caller
        # register at thumbnail, so it can call us for reacting to state
        self.thumbnail.register_FSimage(self)
        # Create secondary (or popup) window.
        self.root = tk.Toplevel(name = "fsimage")
        # Fenstergröße
        self.physical_width  = self.root.winfo_screenwidth()
        self.physical_height = self.root.winfo_screenheight()
        self.screen_width  = int(self.root.winfo_screenwidth() * .75) # adjust as needed
        self.screen_height = int(self.root.winfo_screenheight() * .75) # adjust as needed
        print("Bildschirm ist " + str(self.screen_width) + " x " + str(self.screen_height) + " physical: " + str(self.physical_width) + " x " + str(self.physical_height))
        v_dim=str(self.screen_width)+'x'+str(self.screen_height)
        self.root.geometry(v_dim)
        self.root.minsize(int(self.physical_width / 4), int(self.physical_height / 4))  # (minimum ) width , ( minimum) height
        self.root.resizable(True, True)

        # we create the frames. on the left side we have the vanvas width width relw_frame_canvas, and the height relh_frame_canvas.
        # on the right we have two frames for 2 columns of buttons resp. button / label
        # beneath is the frame for the Scale (playback speed), followed by a frame for the treeview displaying the metadata. 
        gap = .005 # frame around frame
        relw_frame_canvas = .75 # rel width of frame for canvas
        relh_frame_canvas = 1-gap # rel height of frame for canvas
        relw_frame_1      = (1 - relw_frame_canvas) / 2 - 2* gap # rel width for each of the 2 frames on top right
        relw_frame_2      = (1 - relw_frame_canvas) - gap # rel width for the frame bottom right (treeview for metadata)
        relh_1            =.3 - gap # the height the top frames
        relh_2            = .1 # relh for speed scale
        relh_3            = 1-relh_1 -relh_2 -2*gap # relh for metadata frame

        # frame_canvas
        self.frame_canvas = tk.Frame(self.root)
        self.frame_canvas.place(relx=gap, rely=gap, relheight=relh_frame_canvas, relwidth=relw_frame_canvas)
        self.frame_canvas.configure(relief='flat', background = tools._bgcolor)
        self.frame_canvas.configure(background=tools._bgcolor_dbg) if self.debug else True # uncomment for same colour as window (default) or depend on debug
        self.frame_canvas.update()

        # frame_1_1 for 1 label and 2 buttons vertically
        self.frame_1_1 = tk.Frame(self.root)
        self.frame_1_1.place(relx=relw_frame_canvas+2*gap, rely=gap, relheight=relh_1, relwidth=relw_frame_1)
        self.frame_1_1.configure(relief='flat', background = tools._bgcolor)
        self.frame_1_1.configure(background=tools._bgcolor_dbg) if self.debug else True # uncomment for same colour as window (default) or depend on debug
        self.frame_1_1.update()

        # frame_1_2 for 1 label and 2 buttons vertically
        self.frame_1_2 = tk.Frame(self.root)
        self.frame_1_2.place(relx=relw_frame_canvas + relw_frame_1 + 3*gap, rely=gap, relheight=relh_1, relwidth=relw_frame_1)
        self.frame_1_2.configure(relief='flat', background = tools._bgcolor)
        self.frame_1_2.configure(background=tools._bgcolor_dbg) if self.debug else True # uncomment for same colour as window (default) or depend on debug
        self.frame_1_2.update()

        # frame_2 for speed scale
        self.frame_2 = tk.Frame(self.root)
        self.frame_2.place(relx=relw_frame_canvas+2*gap, rely=relh_1 + 3*gap, relheight=relh_2, relwidth=relw_frame_2 - 2* gap)
        self.frame_2.configure(relief='flat', background = tools._bgcolor)
        self.frame_2.configure(background=tools._bgcolor_dbg) if self.debug else True # uncomment for same colour as window (default) or depend on debug
        self.frame_2.update()

        # create widgets
        self.text_font = Font(family="Helvetica", size=6)
        relw_button = 0.975
        relh_button = .25

        dict_widgets = {}
        dict_widgets["1"] = {
          "WIDGET":tk.Label,"VAR":"future_use","OFFSET":0.00,"RELH":.6,"RELW":relw_button,"ANCHOR":"START","TEXT":"future_use","FONT":self.text_font}
        if thumbnail.get_imagetype() == "STILL": # still image
            dict_widgets["2"] = {
              "WIDGET":tk.Button,"VAR":"Button_fit","OFFSET":0.00,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"START","CALLBACK":self.fit_handler,
              "TEXT":"Fit Canvas","STATE":tk.ACTIVE,"TT":"Scale Image to fit","FONT":self.text_font}
        dict_widgets["3"] = {
          "WIDGET":tk.Button,"VAR":"Button_exclude","OFFSET":0.00,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"START","CALLBACK":self.exclude_handler,
          "TEXT":"Exclude","STATE":tk.ACTIVE,"TT":"include / exclude","FONT":self.text_font}
        if thumbnail.get_imagetype() == "VIDEO": # video image
            dict_widgets["4"] = {
              "WIDGET":tk.Button,"VAR":"Button_pp","OFFSET":0.0,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"START","CALLBACK":self.pp_handler,
              "TEXT":"play / pause","STATE":tk.ACTIVE,"TT":"play / pause video player","FONT":self.text_font}
        tools.create_widgets_from_dict(dict_widgets, self.frame_1_1, "VERTICAL", font = self.text_font, bgcolor = tools._bgcolor)

        dict_widgets = {}
        dict_widgets["1"] = {
          "WIDGET":tk.Label,"VAR":"Label_fileinfo","OFFSET":0.00,"RELH":.6,"RELW":relw_button,"ANCHOR":"START","TEXT":"file info","FONT":self.text_font,
          "JUSTIFY":"left"}
        if thumbnail.get_imagetype() == "STILL": # still image
            dict_widgets["2"] = {
              "WIDGET":tk.Button,"VAR":"Button_fscale","OFFSET":0.00,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"START","CALLBACK":self.fscale_handler,
              "TEXT":"Full scale","STATE":tk.ACTIVE,"TT":"show image in full resolution","FONT":self.text_font}
        dict_widgets["3"] = {
          "WIDGET":tk.Label,"VAR":"Label_status","OFFSET":0.00,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"START","TEXT":"In/Ex","FONT":self.text_font}
        if thumbnail.get_imagetype() == "VIDEO": # video image
            dict_widgets["4"] = {
              "WIDGET":tk.Button,"VAR":"Button_restart","OFFSET":0.0,"RELH":relh_button,"RELW":relw_button,"ANCHOR":"START","CALLBACK":self.restart_handler,
              "TEXT":"Restart Video","STATE":tk.ACTIVE,"TT":"restart video from begin","FONT":self.text_font}
        tools.create_widgets_from_dict(dict_widgets, self.frame_1_2, "VERTICAL", font = self.text_font, bgcolor = tools._bgcolor)

        if thumbnail.get_imagetype() == "VIDEO": # still image          
            self.scale_progress =  tk.Scale(self.frame_2, from_=0, to=8.0, resolution=0.1, orient = tk.HORIZONTAL)
            rel_dist_from_frame_x = self.frame_2.winfo_width() / self.root.winfo_width() / 20
            rel_dist_from_frame_y = rel_dist_from_frame_x * (self.frame_2.winfo_width() / self.frame_2.winfo_height())
            self.scale_progress.place(relx=rel_dist_from_frame_x, rely=rel_dist_from_frame_y, relheight=1 - 2* rel_dist_from_frame_y, relwidth=1 - 2* rel_dist_from_frame_x)
            self.scale_progress.configure(activebackground="beige")
            self.scale_progress.configure(background="#d9d9d9")
            self.scale_progress.configure(font="-family {Segoe UI} -size 9")
            self.scale_progress.configure(foreground="black")
            self.scale_progress.configure(highlightbackground="#d9d9d9")
            self.scale_progress.configure(highlightcolor="black")
            self.scale_progress.configure(label="playback speed")
            self.scale_progress.configure(length="196")
            self.scale_progress.configure(troughcolor="#d9d9d9")
            self.scale_progress_tooltip = TT.ToolTip(self.scale_progress, '''set the playback speed''')
            self.scale_progress.config(command = self.on_position)
            self.scale_progress.bind("<ButtonPress-1>", self.on_press)
            self.scale_progress.bind("<ButtonRelease-1>", self.on_release)
            
        # create the canvas
        self.f = tk.Canvas(self.frame_canvas)
        #self.f.place(relx=0.0, rely=0.0, relheight=1.0, relwidth=1.0)
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
        self.H_I = Scrollbar(self.frame_canvas, orient = HORIZONTAL)
        self.H_I.config(command=self.f.xview)
        self.f.config(xscrollcommand=self.H_I.set)

        # position of canvas and scrollbars within frame
        tools.place_box_with_scrollbars(self, self.frame_canvas, self.f, self.H_I, self.V_I, rw = 0.01, d_n = 0.0, d_e = 0.0, d_s = 0.0, d_w = 0.0)

        # Bind keys to canvas for scrolling
        self.f.bind("<Left>",  lambda event: self.scrollx(-1, "unit"))
        self.f.bind("<Right>", lambda event: self.scrollx( 1, "unit"))
        self.f.bind("<Up>",    lambda event: self.scrolly(-1, "unit"))
        self.f.bind("<Down>",  lambda event: self.scrolly( 1, "unit"))

        if self.thumbnail.getState() == INCLUDE:
            self.Button_exclude.config(text = self.str_exclude)
            self.Label_status.config(text = self.str_included)
        else: # toggle to not exclude
            self.Button_exclude.config(text = self.str_include)
            self.Label_status.config(text = self.str_excluded)
        # zur Behandlung von Events brauchen wir den Imagefile-Namen. Darüber kommen wir an das Window und
        # das Image selbst. Das ist erforderlich, weil wir ja mehrere Fenster haben können
        # kurz gesagt: mit dieser Methode kann man Parameter an den Handler übergeben
        self.f.bind("<MouseWheel>", self.mousewheel_handler)
        self.root.protocol("WM_DELETE_WINDOW", self.close_handler)

        self.root.title(str_title_prefix + file)


        if thumbnail.get_imagetype() == "STILL":
            self.image.close
        self.zoomfaktor = 1.0 # we always start with full resolution
        self.f.focus_set()
        if thumbnail.get_imagetype() == "STILL": # still image
            self.image_zoom(self.zoomfaktor)
            self.player = None
        else: #video, we need a new one the existing is for playing in thumbnal
            self.Button_fit.place_forget() if not self.debug else True
            self.Button_fscale.place_forget() if not self.debug else True
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
            self.playerstatus = 'play'
            self.Button_pp.config(text = 'pause')
            self.image = self.pimg
            # we update the progress scale
            # register our function which will becalled during playback
            self.player.register_callback(self.display_progress)
            self.scale_progress.set(0)
            self.scale_progress.config(to = int(self.player.get_duration()))
            
        # set fileinfo
        mytext = "{:s}\ncreated {:s} size {:.3f}".format(thumbnail.getFile(), thumbnail.get_filectime(), thumbnail.get_filesize())
        self.Label_fileinfo.configure(text=mytext)
        
        self.width  = 0
        self.height = 0
        self.adjust_zoom = 0
        self.timer = tools.RestartableTimer(self.root, 666, self.resize)  # ms
        self.root.bind("<Configure>", self.on_configure) # we want to know if size changes
        self.root.after(0, self.resize) # force window height / width to work and call initial resize for fonts
        
    def display_progress(self, progress: int):
        self.scale_progress.set(progress)
   
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
            # we calculate the correction factor for zoom
            if old_width != 0 and old_height != 0 and new_width != 0 and new_height != 0:
                self.adjust_zoom = min(new_width / old_width, new_height / old_height)
            else:    
                self.adjust_zoom = 1.0
            self.text_font.configure(size=tools.calc_fontsize(self.physical_width, self.physical_height, self.width, self.height, self.debug)) 
            # as tkinter tends to make the label text too large, we reduce the length a little bit_length
            self.Label_fileinfo.update()
            self.Label_fileinfo.configure(wraplength=int(self.Label_fileinfo.winfo_width() * 0.95))
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
            self.Button_pp.config(text = 'play')
        else:
            self.player.pstart()
            self.playerstatus = 'play'
            self.Button_pp.config(text = 'pause')

    def setPlaystatus(self, newstatus):
        if newstatus == 'play': 
            self.playerstatus = 'play'
            self.Button_pp.config(text = 'pause')
        else:
            self.playerstatus = 'pause'
            self.Button_pp.config(text = 'play')

    def restart_handler(self):
        self.player.restart()
        self.setPlaystatus('play')

    def fscale_handler(self):
        self.image_zoom(1) # damit bringt image_zoom das Foto in höchster Auflösung zur Anzeige
        
    def on_position(self, value): # called during movement of slider
        f_value = float(value)
        #print ("Slider position is: " + str(f_value)) if self.debug else True

    def on_press(self, value):  # called on press of slider
        value = self.scale_progress.get()
        f_value = float(value)
        #print ("Slider press position is: " + str(f_value)) if self.debug else True
        self.player.user_scrubbing = True

    def on_release(self, value):  # calles on release of slider
        value = self.scale_progress.get()
        f_value = float(value)
        print ("Slider release position is: " + str(f_value)) if self.debug else True
        if not self.player.getRun():
            self.player.pstart()
        
        self.player.jump_to((f_value))
        self.player.user_scrubbing = False

    def exclude_handler(self): # react to own Button, thumbnail can be from main or duplicates
        # Button -> this method -> thumbnail.setstate -> exclude_call
        if self.thumbnail.getState() == INCLUDE:
            self.Button_exclude.config(text = self.str_include)
            self.Label_status.config(text = self.str_excluded)
            self.thumbnail.setState(EXCLUDE)
        else: # toggle to not exclude, delete Item
            self.Button_exclude.config(text = self.str_exclude)
            self.Label_status.config(text = self.str_included)
            self.thumbnail.setState(INCLUDE)
        self.main.historize_process()

    def exclude_call(self, state): # react to request from outside
        print("MyFSImage.exclude_call, state = {:d}".format(state)) if self.debug else True
        if state == INCLUDE:
            self.Button_exclude.config(text = self.str_exclude)
            self.Label_status.config(text = self.str_included)
        else: # toggle to not exclude, delete Item
            self.Button_exclude.config(text = self.str_include)
            self.Label_status.config(text = self.str_excluded)
    
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
        if self.thumbnail.get_imagetype() == "STILL": # still image
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
        if self.thumbnail.get_imagetype() == "VIDEO": # Video we have to resize the player
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
