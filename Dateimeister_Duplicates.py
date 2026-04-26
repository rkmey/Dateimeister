# display and process duplicates
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

import xml.etree.ElementTree as ET
    
from PIL import Image, ImageTk
from datetime import datetime, timezone

import Dateimeister
import dateimeister_config_xml as DX
import dateimeister_video as DV
import Diatisch as DIAT
import dateimeister_generator as DG
import Undo_Redo as UR
import Dateimeister_FSimage as FS
import Dateimeister_messages as DM
import Dateimeister_Duplicates as DD

import Tooltip as TT

import tools
from tools import Globals, INCLUDE, EXCLUDE
from tools import MyThumbnail

from enum import Enum

_bgcolor = 'grey90'
_bgcolor_dbg = 'green'
_fgcolor = 'black'
_tabfg1 = 'black' 
_tabfg2 = 'white' 
_bgmode = 'light' 
_tabbg1 = '#d9d9d9' 
_tabbg2 = 'gray40' 

_style_code_ran = 0


INCLUDE = 1
EXCLUDE = 2

class MyDuplicates:

    # The class "constructor" - It's actually an initializer 
    def __init__(self, pmain, debug):
        self.player = None
        self.main = pmain
        self.debug = debug
        self.thumbnails_duplicates = {}
        self.dict_thumbnails_duplicates = {}
        # register at thumbnail, so it can call us for reacting to state
        # Create secondary (or popup) window.
        self.root = tk.Toplevel()
        self.w3 = Dateimeister.Toplevel_dupl(self.root)
        self.w3.Button_dupl.config(command = self.dupl_handler)
        self.root.protocol("WM_DELETE_WINDOW", self.close_handler)

        width,height=Globals.screen_width,Globals.screen_height
        v_dim=str(width)+'x'+str(height)
        self.root.geometry(v_dim)
        self.root.resizable(False, False)
        title = self.root.title()
        self.root.title(title + " for " + Globals.outdir)

        # Frame_canvas
        self.frame_canvas = tk.Frame(self.root)
        rely = .6
        relheight = 1 - rely -0.01
        self.frame_canvas.place(relx=0.005, rely=rely, relheight=relheight, relwidth=0.995)
        self.frame_canvas.configure(relief='flat', background = _bgcolor)
        self.frame_canvas.configure(background=_bgcolor_dbg) if self.debug else True # uncomment for same colour as window (default) or depend on debug
        self.frame_canvas.update()

        self.f = tk.Canvas(self.frame_canvas, bg="yellow")
        self.f.place(relx=0.01, rely=0.0, relheight=.95, relwidth=.98)
        self.f.delete('all')
        self.f.update()

        # horizontal scrollbar for cancas
        self.H_I = Scrollbar(self.frame_canvas, orient = HORIZONTAL, command = self.xview)
        self.f.config(xscrollcommand=self.H_I.set)
        self.H_I.place(relx=0.01, rely=1, relheight= 1 - self.f.winfo_height() /  self.f.master.winfo_height(), relwidth=.98, anchor = tk.SW)

        # Bind keys to canvas for scrolling
        self.f.bind("<Left>",  lambda event: self.xview("scroll", -1, "units"))
        self.f.bind("<Right>", lambda event: self.xview("scroll",  1, "units"))
        self.f.bind("<Double-Button-1>", self.canvas_show)
        self.f.focus_set()
        
        # Listbox
        # vertical scrollbar for lisrbox
        self.V_L = Scrollbar(self.w3.Listbox_dupl, orient = VERTICAL)
        self.V_L.config(command = self.w3.Listbox_dupl.yview)                    
        self.V_L.pack(side=RIGHT, fill=BOTH)
        self.w3.Listbox_dupl.config(yscrollcommand = self.V_L.set) 
        self.w3.Listbox_dupl.bind('<Double-1>', self.lb_double)
        for key in Globals.dict_duplicates[Globals.imagetype]:
            self.w3.Listbox_dupl.insert(END, key)
        self.w3.Listbox_dupl.select_set(0)

        # Create the context menu
        self.context_menu = tk.Menu(self.f, tearoff=0)
        self.context_menu.add_command(label="Exclude", command=self.canvas_image_exclude)    
        self.context_menu.add_command(label="Show"   , command=self.canvas_image_show)    
        self.context_menu.add_command(label="Restart", command=self.canvas_video_restart)    

        self.f.bind("<Button-3>", self.show_context_menu)    
        self.f.bind('<Motion>', self.tooltip_imagefile)    
        self.f.bind('+', lambda event: self.delay_decr(event))
        self.f.bind('-', lambda event: self.delay_incr(event))
        self.f.bind('0', lambda event: self.delay_deflt(event))
        
        self.dict_child_parent = {}
        self.timestamp = datetime.now()
        self.tooltiptext = ""
        self.tt = TT.ToolTip(self.f, "no images available", delay=0, follow = True)
        
        self.dict_file_image = {}
        self.main.button_duplicates.config(state = DISABLED) # Duplicates Window must not exist more than once

    def exclude_call(self, parent, state): # react to request from outside, outside is root - thumbnail
        print("MyDuplicate.Exclude called, State = " + str(state))
        # we have to find child for parent ( this is the thumbnail in main window)
        for child in self.dict_child_parent:
            myparent = self.dict_child_parent[child]
            if myparent == parent:
                break
        child.setState(state, self)
    
    def canvas_image_exclude(self): # calls canvas_exclude with self.event
        print("Context menu exlude")
        self.canvas_exclude(self.event)

    def canvas_exclude(self, event):
        self.f.focus_set()

        canvas_x = self.f.canvasx(event.x)
        canvas_y = self.f.canvasy(event.y)
        thumbnail, index = self.get_thumbnail_by_position(canvas_x, canvas_y)
        if thumbnail is not None:
            if thumbnail.getState() == INCLUDE:
                thumbnail.setState(EXCLUDE, self)
            else: # toggle to not exclude, delete Item
                thumbnail.setState(INCLUDE, self)
            self.main.historize_process()

    def canvas_image_show(self):
        print("Context menu show")
        self.canvas_show(self.event)

    def canvas_show(self, event):
        self.f.focus_set()

        canvas_x = self.f.canvasx(event.x)
        canvas_y = self.f.canvasy(event.y)
        thumbnail, index = self.get_thumbnail_by_position(canvas_x, canvas_y)
        if thumbnail is not None:
            item_id = thumbnail.getId()
            self.display_image(thumbnail)

    def display_image(self, thumbnail):
        file = thumbnail.getShowfile()
        # wenn das Bild schon in einem Fenster angezeigt wird, dann verwenden wir dieses
        if file in self.dict_file_image:
            print ("FSImage exists for file: " + file)
            fs_image = self.dict_file_image[file]
            player = fs_image.getPlayer()
            if player is not None: # this is a video
                print ("FSImage restart file: " + file)
                player.restart()
                fs_image.setPlaystatus('play') # Status, Buttontext
        else: # ein neues Objekt anlegen und in self.dict_file_image eintragen
            print ("FSImage does not exist for file: " + file)
            fs_image = FS.MyFSImage(file, thumbnail, self.dict_file_image, self.main, "", "Include", "Exclude", "Included", "Excluded", self.main.debug)
            self.dict_file_image[file] = fs_image

    def canvas_video_restart(self):
        print("Context menu restart")
        self.f.focus_set()

        canvas_x = self.f.canvasx(self.event.x)
        canvas_y = self.f.canvasy(self.event.y)
        thumbnail, index = self.get_thumbnail_by_position(canvas_x, canvas_y)
        if thumbnail is not None:
            player = thumbnail.getPlayer()
            if player is not None: # this is a video
                player.restart()

    def show_context_menu(self, event):
        # das Event müssen wir speichern, da die eigenlichen Funktionen die x und y benötigen
        self.event = event
        # falls wir keine anzeigbare Datei haben, müssen wir show-Item disablen
        canvas_x = self.f.canvasx(event.x)
        canvas_y = self.f.canvasy(event.y)
        thumbnail, index = self.get_thumbnail_by_position(canvas_x, canvas_y)
        if thumbnail is not None:
            if thumbnail.getImage() == 0:
                print(" No Image availabl for " + thumbnail.getFile())
                self.context_menu.entryconfig(1, state="disabled")
            else:
                self.context_menu.entryconfig(1, state="normal")
            if thumbnail.getState() == INCLUDE:
                self.context_menu.entryconfig(0, label = "Exclude " + thumbnail.getFile())
            else:
                self.context_menu.entryconfig(0, label = "Include " + thumbnail.getFile())
            self.context_menu.entryconfig(1, label = "Show " + thumbnail.getFile())
            self.context_menu.post(event.x_root, event.y_root)
    
    def tooltip_imagefile(self, event):
        tsnow = datetime.now()
        tdiff = abs(tsnow - self.timestamp)
        milliseconds = tdiff.days * 86400 * 1000 + tdiff.seconds * 1000 + tdiff.microseconds / 1000
        if  milliseconds > 200:
            #print("Timer has finished, milliseconds is: ", milliseconds) if self.debug else True
            self.timestamp = tsnow
        else:
            return
        # Tooltip
        #x, y = canvas.winfo_pointerxy()
        text = "no image available"
        # canvas is drawn before the thumbnails are created, so check existence and length
        if Globals.imagetype in self.thumbnails_duplicates and len(self.thumbnails_duplicates[Globals.imagetype]) > 0:
            canvas_x = self.f.canvasx(event.x)
            canvas_y = self.f.canvasy(event.y)
            thumbnail, index = self.get_thumbnail_by_position(canvas_x, canvas_y)
            if thumbnail is not None:
                text = "{:s}\n created {:s} size {:.3f}".format(thumbnail.getFile(), thumbnail.get_filectime(), thumbnail.get_filesize())
                #print("Image clicked: " + text)
            if text != self.tooltiptext:
                self.tt.update(text)
                self.tooltiptext = text
                self.stop_all_players()
                # if file is video, play video
                if thumbnail is not None:
                    player = thumbnail.getPlayer()
                    if player is not None: # this is a video
                        player.pstart()
                        fps   = player.getFPS()
                        player.setDelay(int(1000 / fps))
                        fc    = player.getFrameCount()
                        delay = player.getDelay()
                        frames_per_second = 1000 / delay
                        duration_in_seconds = fc / frames_per_second
                        #print ("FPS is: ", fps, " Total Num of Frames is: ", fc, " Delay is: ", delay, " calc duration is: " + str(duration_in_seconds))
                        self.context_menu.entryconfig(2, state="normal")
                    else:
                        self.context_menu.entryconfig(2, state="disabled")
                        
    def delay_decr(self, event): # speed +
        self.f.focus_set()
        delta = -5
        canvas_x = self.f.canvasx(event.x)
        canvas_y = self.f.canvasy(event.y)
        thumbnail, index = self.get_thumbnail_by_position(canvas_x, canvas_y)
        if thumbnail is not None:
            player = thumbnail.getPlayer()
            if player is not None: # a video
                delay = player.getDelay()
                if delay + delta > 5:
                    player.setDelay(delay + delta)

    def delay_incr(self, event): # speed -
        self.f.focus_set()
        delta = 5
        canvas_x = self.f.canvasx(event.x)
        canvas_y = self.f.canvasy(event.y)
        thumbnail, index = self.get_thumbnail_by_position(canvas_x, canvas_y)
        if thumbnail is not None:
            player = thumbnail.getPlayer()
            if player is not None: # a video
                delay = player.getDelay()
                if delay + delta < 200:
                    player.setDelay(delay + delta)

    def delay_deflt(self, event): # speed normal
        self.f.focus_set()
        canvas_x = self.f.canvasx(event.x)
        canvas_y = self.f.canvasy(event.y)
        thumbnail, index = self.get_thumbnail_by_position(canvas_x, canvas_y)
        if thumbnail is not None:
            player = thumbnail.getPlayer()
            if player is not None: # a video
                delay = player.getDelay()
                player.setDelay(int(1000 / player.getFPS()))
                
    def lb_double(self, event):
        cs = self.w3.Listbox_dupl.curselection()
        self.thisduplicate = self.w3.Listbox_dupl.get(cs)
        #print("Duplicate selected: " + self.thisduplicate)
        self.display_duplicate(self.thisduplicate)
    
    def scrollx(self, amount, unit):
        #print("scroll command: " + str(amount) + ' ' + unit)
        self.f.xview_scroll(amount, unit)
        return "break"
     
    def dupl_handler(self):
        cs = self.w3.Listbox_dupl.curselection()
        self.thisduplicate = self.w3.Listbox_dupl.get(cs)
        #print("Duplicate selected: " + self.thisduplicate)
        self.display_duplicate(self.thisduplicate)

    def close_handler(self): #calles when window is closing
        print("ToDo, cleanup when window is closed")
        self.stop_all_players() # unregister to avoid calls after duplicate has been destroyed
        for child in self.dict_child_parent:
            parent = self.dict_child_parent[child]
            parent.register_Dupl(None)
        self.root.destroy()
        for t in self.dict_file_image: # destroy all FSImages
            u = self.dict_file_image[t]
            u.close_handler_external()
        self.main.button_duplicates.config(state = NORMAL)
        self.main.win_duplicates = None
        
    def stop_all_players(self):
        # stop all video players
        self.main.button_duplicates.config(state = DISABLED)
        if Globals.imagetype in self.thumbnails_duplicates:
            for t in self.thumbnails_duplicates[Globals.imagetype]: # stop all running players
                thisplayer = t.getPlayer()
                if thisplayer is not None:
                    if thisplayer.getRun(): # running
                        thisplayer.pstop()
                        #print ("Stop player for: " + t.getFile())
    
    def display_duplicate(self, target_file):
        self.main.stop_all_players() # should not continue running 
        self.f.delete('all')
        self.thumbnails_duplicates[Globals.imagetype] = []
        self.dict_thumbnails_duplicates[Globals.imagetype] = {}
        list_duplicate_sourcefiles = Globals.dict_duplicates[Globals.imagetype][target_file]
        self.lastposition = 0
        self.num_images = 0
        # distance from border for text-boxes
        dist_text  = 10
        # distance from border for image-frame
        dist_frame = 20
        height_scrollbar = self.H_I.winfo_height()

        for source_file in list_duplicate_sourcefiles:
            thumbnail = Globals.dict_thumbnails[Globals.imagetype][source_file]
            showfile = thumbnail.getShowfile()
            state = thumbnail.getState() # we want to use the current state and copy it to the duplicate-thumbnail
            if showfile != 'none':
                canvas_height = self.f.winfo_height() - self.H_I.winfo_height()
                canvas_width  = self.f.winfo_width()
                self.canvas_width_visible = self.f.winfo_width() # Fensterbreite
                player = None
                if thumbnail.getPlayer() is not None: # Video
                    print("try to create new videoplayer...")
                    # create new videoplayer
                    player   = DV.VideoPlayer(self.root, showfile, self.f, canvas_width, canvas_height)
                    image_width, image_height, pimg = player.get_photo()
                else: # still image
                    img  = Image.open(showfile)
                    image_width_orig, image_height_orig = img.size
                    faktor = canvas_height / image_height_orig
                    newsize = (int(image_width_orig * faktor), int(image_height_orig * faktor))
                    r_img = img
                    r_img.thumbnail(newsize)
                    image_width, image_height = r_img.size
                    print("try to print " + showfile + " width is " + str(image_width) + "(" + str(image_width_orig) + ")" + " height is " + str(image_height) + "(" + str(image_height_orig) + ")" \
                       + " factor is " + str(faktor))
                    pimg = ImageTk.PhotoImage(r_img)
                id = self.f.create_image(self.lastposition, 0, anchor='nw',image = pimg, tags = 'images')
                text_id = self.f.create_text(self.lastposition + dist_text, dist_text, text="EXCLUDE", fill="red", font=('Helvetica 10 bold'), anchor =  tk.NW, tag = "text")
                rect_id = self.f.create_rectangle(self.f.bbox(text_id), outline="blue", fill = "white", tag = 'rect')
                # the frame for selected image, consisting of 4 lines because there is no opaque rectangle in tkinter
                north_west = (self.lastposition + dist_frame, dist_frame)
                north_east = (self.lastposition + image_width - dist_frame, dist_frame)
                south_west = (self.lastposition + dist_frame, image_height - dist_frame)
                south_east = (self.lastposition + image_width - dist_frame, image_height - dist_frame)
                line_north = self.f.create_line(north_west, north_east, dash=(1, 1), fill = "red", tags="imageframe")
                line_east  = self.f.create_line(north_east, south_east, dash=(1, 1), fill = "red", tags="imageframe")
                line_south = self.f.create_line(south_west, south_east, dash=(1, 1), fill = "red", tags="imageframe")
                line_west  = self.f.create_line(north_west, south_west, dash=(1, 1), fill = "red", tags="imageframe")
                frameids = (line_north, line_east, line_south, line_west)

                self.f.tag_raise("rect")
                self.f.tag_raise("text")
                self.f.tag_raise("line")
                #self.f.tag_raise("imageframe")
                if player is not None:
                    player.setId(id)
                    player.resize()
                # we must also create a thumbnail_list for duplicate images, or the garbage collector will delete images
                mts = os.stat(showfile).st_mtime
                myimage = MyThumbnail(pimg, self.main, self.lastposition, self.lastposition + image_width, showfile, mts, showfile, id, \
                    text_id, rect_id, frameids, 0, player, 'j', self.f, None, None, thumbnail)
                self.thumbnails_duplicates[Globals.imagetype].append(myimage)
                myimage.setState(state)
                self.dict_thumbnails_duplicates[Globals.imagetype][showfile] = myimage # damit können wir auf thumbnails mit den Sourcefilenamen zugreifen, z.B. für Duplicates
                self.lastposition += image_width + Globals.gap 
            else: # wir haben kein Bild, ein Rechteck einfügen
                image_height = canvas_height
                image_width  = int(canvas_height * 4 / 3)
                id = self.f.create_rectangle(self.lastposition, 0, self.lastposition + image_width, canvas_height, fill="blue", tags = 'images')
                text_id = self.f.create_text(self.lastposition, 0, text="EXCLUDE", fill="red", font=('Helvetica 10 bold'), anchor =  tk.NW, tag = "text")
                rect_id = self.f.create_rectangle(self.f.bbox(text_id), outline="blue", fill = "white")
                # the frame for selected image, consisting of 4 lines because there is no opaque rectangle in tkinter
                north_west = (self.lastposition + dist_frame, dist_frame)
                north_east = (self.lastposition + image_width - dist_frame, dist_frame)
                south_west = (self.lastposition + dist_frame, image_height - dist_frame)
                south_east = (self.lastposition + image_width - dist_frame, image_height - dist_frame)
                line_north = self.f.create_line(north_west, north_east, dash=(1, 1), fill = "red", tags="imageframe")
                line_east  = self.f.create_line(north_east, south_east, dash=(1, 1), fill = "red", tags="imageframe")
                line_south = self.f.create_line(south_west, south_east, dash=(1, 1), fill = "red", tags="imageframe")
                line_west  = self.f.create_line(north_west, south_west, dash=(1, 1), fill = "red", tags="imageframe")
                frameids = (line_north, line_east, line_south, line_west)
                self.f.tag_raise("text")
                #self.f.tag_raise("imageframe")
                mts = os.stat(showfile).st_mtime
                myimage = MyThumbnail(0, self.main, self.lastposition, self.lastposition + image_width, showfile, mts, showfile, id, \
                    text_id, rect_id, frameids, 0, player, 'j', self.f, None, None, thumbnail)
                self.thumbnails_duplicates[Globals.imagetype].append(myimage)
                self.dict_thumbnails_duplicates[Globals.imagetype][showfile] = myimage
                self.lastposition += image_width + Globals.gap 
            self.num_images += 1
            # register at parent-thumbnail, so it can call us for reacting to state
            # we need a dict with child-parent-thumbnails in order to unregister on close
            self.dict_child_parent[myimage] = thumbnail # child -> parent
            thumbnail.register_Dupl(self)
        # Globals.gap haben wir einmal zuviel (fürs letzte) gezählt
        self.lastposition -= Globals.gap
        # damit wir am Ende auch bis zum letzten einzelnen Bild scrollen können, fügen wir ein Rechteck ein
        if len(self.thumbnails_duplicates[Globals.imagetype]) > 0: 
            thumbnail = self.thumbnails_duplicates[Globals.imagetype][-1]
            rect_len = self.canvas_width_visible - (thumbnail.getEnd() - thumbnail.getStart() + Globals.gap)
            self.f.create_rectangle(self.lastposition, 0, self.lastposition + rect_len, canvas_height, fill="yellow")
            self.f.config(scrollregion = self.f.bbox('all')) 
            self.canvas_width_images = self.f.bbox('images')[2]
            self.canvas_width_all    = self.f.bbox('all')[2]
            #print ("Canvas totale Breite(Images): " + str(self.canvas_width_images) + " totale Breite(All): " + str(self.canvas_width_all) \
            #    + " visible: " + str(self.canvas_width_visible) + " lastposition: " + str(self.lastposition))
        
        for child in self.dict_child_parent:
            parent = self.dict_child_parent[child]
            print("Child file / parent file is: " + child.getFile() + ' / ' + parent.getFile())
        #print("self.thumbnails_duplicates is: " + str(self.thumbnails_duplicates))
        self.f.focus_set()

    def xview(self, *args):
        print (*args)
        s1 = 0.0
        s2 = 1.0
        scrolldelta = 0
        width_scrollbar = self.H_I.winfo_width()
        #print ("Scroll Canvas totale Breite(Images): " + str(self.canvas_width_images) + " totale Breite(All): " + str(self.canvas_width_all) \
        #    + " visible: " + str(self.canvas_width_visible) + " Scrollbarwidth: " + str(width_scrollbar) + " BBOX: " + str(self.f.bbox('all')))
        slider_width = int((self.canvas_width_visible / self.canvas_width_all) * width_scrollbar)
        # aktuelle Scroll-Position des Canvas
        canvas_x = self.f.canvasx(0)
        canvas_y = self.f.canvasy(0)
        # aktuelle position der Scrollbar
        scrollposition = self.H_I.get()[0]
        
        #print("scroll_position_H_I: " + str(canvas_x) + " scroll_position Scrollbar: " + str(scrollposition))
        # wenn wir die Pfeiltasten betätigen, wollen wir auf den Anfang des nächsten (vorherigen) Bildes scrollen.
        # wenn das aktuelle Bild nur teilweise zusehen ist, scrollen wir bei Linkstaste auf den Bildbeginn
        if len(args) == 3 and args[2] == "units":
            # den scrollbetrag auf die Größe des Bildes am linken Rand setzen
            thumbnail, index = self.get_thumbnail_by_position(canvas_x + 11, canvas_y)
            if thumbnail is not None:
                if int(args[1]) > 0:
                    scrolldelta = (thumbnail.getEnd() - canvas_x + Globals.gap)
                else:
                    if canvas_x - thumbnail.getStart() > 10: # Bild links abgeschnitten, an den Anfang scrollen
                        scrolldelta = (thumbnail.getStart() - canvas_x) # ist dann negativ, was wir ja wollen
                        #print("Bild links abgeschnitten, weil canvas_x = " + str(canvas_x) + " und Bildstart = " + str(thumbnail.getStart()))
                    else: #Bild ist vollständig zu sehen, also zurück zum nächsten
                        if index > 0: # es gibt einen Vorgänger
                            scrolldelta = (self.thumbnails_duplicates[Globals.imagetype][index - 1].getStart()) - canvas_x
                            #print("Vorgänger ist: " + Globals.thumbnails[Globals.imagetype][index - 1].getFile() + " Start: " + str(Globals.thumbnails[Globals.imagetype][index - 1].getStart())\
                            #    + " canvas_x is: " + str(canvas_x) + " scrolldelta is: " + str(scrolldelta))
                
                new_canvas_x = canvas_x + scrolldelta
                # nach links scrollen machr keinen Sinn, wenn wir schon ganz links stehen, analog rechts
                if (int(args[1]) < 0 and canvas_x <= 0) or (int(args[1]) > 0 and new_canvas_x >= self.canvas_width_images):
                   return
                s2 = new_canvas_x / self.canvas_width_all
                s1 = (new_canvas_x - slider_width) / self.canvas_width_all
                print ("new Scroll posiion in canvas  is: " + str(new_canvas_x) + " S1, S2 = " + str(s1) + "," + str(s2) + " slider-widt: " + str(slider_width))
            self.H_I.set(s1, s2)
            self.f.xview('moveto', s2)
        else:
            #if (1 == 0):
                #return
            self.f.xview(*args)

    def get_thumbnail_by_position(self, canvas_x, canvas_y):
        index = -1
        found = False
        for thumbnail in self.thumbnails_duplicates[Globals.imagetype]:
            start = thumbnail.getStart()
            end   = thumbnail.getEnd()
            if (canvas_x >= start and canvas_x <= end):
                index = self.thumbnails_duplicates[Globals.imagetype].index(thumbnail)
                #print("retrieved " + thumbnail.getFile() + " Index: " + str(index))
                found = True
                break
        if not found:
            thumbnail = None
            index = None
        return (thumbnail, index)

    def __del__(self):
        self.a = 1
        print("*** Deleting MyDuplicates-Objekt. Outdir is " + str(Globals.outdir))

