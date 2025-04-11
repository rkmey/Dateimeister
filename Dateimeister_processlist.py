#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

# Message Output from generated scripts
import re
import locale
import ctypes
import time
import operator

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

import Dateimeister

class MyProcesslistWindow:

    # The class "constructor" - It's actually an initializer 
    def __init__(self, caller_close_function, caller_display_function, dict_processlist, debug, debug_p):
        self.root = tk.Toplevel()
        self.pf_close   = caller_close_function
        self.pf_display = caller_display_function
        self.initialized = False
        
        self.root.protocol("WM_DELETE_WINDOW", self.close_handler)

        screen_width  = int(self.root.winfo_screenwidth() * 0.7)
        screen_height = int(self.root.winfo_screenheight() * 0.5)
        print("Bildschirm ist " + str(screen_width) + " x " + str(screen_height))
        width,height=screen_width,screen_height
        v_dim=str(width)+'x'+str(height)
        self.root.geometry(v_dim)
        self.root.resizable(True, True)

        self.dict_processlist = dict_processlist
        self.debug   = debug
        self.debug_p = debug_p
        self.procstep_selected = None
        self.dict_text_processid = {}

        # resizable font
        self.text_font = Font(family="Helvetica", size=6)
        self.width  = 0
        self.height = 0
        self.frame_labels_height = 0.04 # needed for calculation of font size
        self.label_height = 0.7 # needed for calculation of font size

        self.Frame_labels = tk.Frame(self.root)
        self.Frame_labels.place(relx=.01, rely=0.00, relheight=self.frame_labels_height, relwidth=0.98)
        self.Frame_labels.configure(relief='flat')
        self.Frame_labels.configure(background="#d9d9d9") if self.debug else True # uncomment for same colour as window (default) or depend on debug

        self.Label_hist_ctr = tk.Label(self.Frame_labels)
        self.Label_hist_ctr.place(relx=0.0, rely=0.0, relheight=self.label_height, relwidth=0.25)
        self.Label_hist_ctr.configure(anchor=tk.NW)
        self.Label_hist_ctr.configure(font=self.text_font)
        self.Label_hist_ctr_text = "Num Hist: {:d}"
        st = self.Label_hist_ctr_text.format(0)
        self.Label_hist_ctr.configure(text = st)

        self.Label_list_ctr = tk.Label(self.Frame_labels)
        self.Label_list_ctr.place(relx=0.34, rely=0.0, relheight=self.label_height, relwidth=0.25)
        self.Label_list_ctr.configure(anchor=tk.NW)
        self.Label_list_ctr.configure(font=self.text_font)
        self.Label_list_ctr_text = "Num List: {:d}"
        st = self.Label_list_ctr_text.format(0)
        self.Label_list_ctr.configure(text = st)

        self.Label_undo_ctr = tk.Label(self.Frame_labels)
        self.Label_undo_ctr.place(relx=0.68, rely=0.0, relheight=self.label_height, relwidth=0.25)
        self.Label_undo_ctr.configure(anchor=tk.NW)
        self.Label_undo_ctr.configure(font=self.text_font)
        self.Label_undo_ctr_text = "Num Undo: {:d}"
        st = self.Label_undo_ctr_text.format(0)
        self.Label_undo_ctr.configure(text = st)

        # Frame for process_hist
        self.Frame_process_hist = tk.Frame(self.root)
        self.Frame_process_hist.place(relx=.01, rely= self.frame_labels_height + .01, relheight= 1 - self.frame_labels_height -.02, relwidth=0.32)
        self.Frame_process_hist.configure(relief='flat')
        self.Frame_process_hist.configure(background="#d9d9d9") if self.debug else True # uncomment for same colour as window (default) or depend on debug

        # listbox for process_hist
        self.listbox_process_hist_relheight = .9
        self.listbox_process_hist_relwidth  = .9
        self.listbox_process_hist_var = tk.StringVar()
        self.listbox_process_hist = tk.Listbox(self.Frame_process_hist)
        self.listbox_process_hist.place(relx=.0, rely=0, relheight= self.listbox_process_hist_relheight, relwidth=self.listbox_process_hist_relwidth)
        self.listbox_process_hist.configure(font=self.text_font)
        self.listbox_process_hist.configure(selectmode='single')
        self.listbox_process_hist.configure(listvariable=self.listbox_process_hist_var)

        # Scrollbars for process_hist
        self.Frame_process_hist.update()
        w = self.Frame_process_hist.winfo_width()
        h = self.Frame_process_hist.winfo_height()
        f = 4000 / w # for 4k screen appr. 1
        b = f * w / 50000
        r = w / h
        print("frame width / height = {:d}, {:d}".format(w, h)) if self.debug else True
        self.vi_process_hist = tk.Scrollbar(self.Frame_process_hist, orient= VERTICAL)
        self.vi_process_hist.place(relx = self.listbox_process_hist_relwidth, rely = 0, relheight = self.listbox_process_hist_relheight, relwidth = min(max(b, 0.005 * f), .03), anchor = tk.NW)
        self.vi_process_hist.config(command = self.listbox_process_hist.yview)
        self.listbox_process_hist.config(yscrollcommand = self.vi_process_hist.set)
        self.hi_process_hist = tk.Scrollbar(self.Frame_process_hist, orient= HORIZONTAL)
        self.hi_process_hist.place(relx = 0, rely = self.listbox_process_hist_relheight, relheight = min(max(b * r, 0.005 * f * r), .03 * r), relwidth = self.listbox_process_hist_relwidth, anchor = tk.NW)
        self.hi_process_hist.config(command = self.listbox_process_hist.xview)
        self.listbox_process_hist.config(xscrollcommand = self.hi_process_hist.set)
        self.listbox_process_hist.bind('<Double-1>', self.listbox_process_hist_double)
        self.listbox_process_hist.bind('<ButtonPress-1>', self.listbox_process_hist_button_press_1)
        self.listbox_process_hist.bind("<<ListboxSelect>>", self.listbox_process_hist_selection_changed)
        self.listbox_process_hist.bind("<Down>", self.listbox_process_hist_arrow_down)
        self.listbox_process_hist.bind("<Up>", self.listbox_process_hist_arrow_up)
        self.listbox_process_hist_selection = 0

        # Frame for process_list
        self.Frame_process_list = tk.Frame(self.root)
        self.Frame_process_list.place(relx=.34, rely= self.frame_labels_height + .01, relheight= 1 - self.frame_labels_height -.02, relwidth=0.32)
        self.Frame_process_list.configure(relief='flat')
        self.Frame_process_list.configure(background="#d9d9d9") if self.debug else True # uncomment for same colour as window (default) or depend on debug

        # listbox for process_list
        self.listbox_process_list_relheight = .9
        self.listbox_process_list_relwidth  = .9
        self.listbox_process_list_var = tk.StringVar()
        self.listbox_process_list = tk.Listbox(self.Frame_process_list)
        self.listbox_process_list.place(relx=.0, rely=0, relheight= self.listbox_process_list_relheight, relwidth=self.listbox_process_list_relwidth)
        self.listbox_process_list.configure(font=self.text_font)
        self.listbox_process_list.configure(selectmode='single')
        self.listbox_process_list.configure(listvariable=self.listbox_process_list_var)

        # Scrollbars for process_list
        self.Frame_process_list.update()
        w = self.Frame_process_list.winfo_width()
        h = self.Frame_process_list.winfo_height()
        f = 4000 / w # for 4k screen appr. 1
        b = f * w / 50000
        r = w / h
        print("frame width / height = {:d}, {:d}".format(w, h)) if self.debug else True
        self.vi_process_list = tk.Scrollbar(self.Frame_process_list, orient= VERTICAL)
        self.vi_process_list.place(relx = self.listbox_process_list_relwidth, rely = 0, relheight = self.listbox_process_list_relheight, relwidth = min(max(b, 0.005 * f), .03), anchor = tk.NW)
        self.vi_process_list.config(command = self.listbox_process_list.yview)
        self.listbox_process_list.config(yscrollcommand = self.vi_process_list.set)
        self.hi_process_list = tk.Scrollbar(self.Frame_process_list, orient= HORIZONTAL)
        self.hi_process_list.place(relx = 0, rely = self.listbox_process_list_relheight, relheight = min(max(b * r, 0.005 * f * r), .03 * r), relwidth = self.listbox_process_list_relwidth, anchor = tk.NW)
        self.hi_process_list.config(command = self.listbox_process_list.xview)
        self.listbox_process_list.config(xscrollcommand = self.hi_process_list.set)
        self.listbox_process_list.bind('<Double-1>', self.listbox_process_list_double)

        # Frame for process_undo
        self.Frame_process_undo = tk.Frame(self.root)
        self.Frame_process_undo.place(relx=.67, rely= self.frame_labels_height + .01, relheight= 1 - self.frame_labels_height -.02, relwidth=0.32)
        self.Frame_process_undo.configure(relief='flat')
        self.Frame_process_undo.configure(background="#d9d9d9") if self.debug else True # uncomment for same colour as window (default) or depend on debug

        # listbox for process_undo
        self.listbox_process_undo_relheight = .9
        self.listbox_process_undo_relwidth  = .9
        self.listbox_process_undo_var = tk.StringVar()
        self.listbox_process_undo = tk.Listbox(self.Frame_process_undo)
        self.listbox_process_undo.place(relx=.0, rely=0, relheight= self.listbox_process_undo_relheight, relwidth=self.listbox_process_undo_relwidth)
        self.listbox_process_undo.configure(font=self.text_font)
        self.listbox_process_undo.configure(selectmode='single')
        self.listbox_process_undo.configure(listvariable=self.listbox_process_undo_var)

        # Scrollbars for process_undo
        self.Frame_process_undo.update()
        w = self.Frame_process_undo.winfo_width()
        h = self.Frame_process_undo.winfo_height()
        f = 4000 / w # for 4k screen appr. 1
        b = f * w / 50000
        r = w / h
        print("frame width / height = {:d}, {:d}".format(w, h)) if self.debug else True
        self.vi_process_undo = tk.Scrollbar(self.Frame_process_undo, orient= VERTICAL)
        self.vi_process_undo.place(relx = self.listbox_process_undo_relwidth, rely = 0, relheight = self.listbox_process_undo_relheight, relwidth = min(max(b, 0.005 * f), .03), anchor = tk.NW)
        self.vi_process_undo.config(command = self.listbox_process_undo.yview)
        self.listbox_process_undo.config(yscrollcommand = self.vi_process_undo.set)
        self.hi_process_undo = tk.Scrollbar(self.Frame_process_undo, orient= HORIZONTAL)
        self.hi_process_undo.place(relx = 0, rely = self.listbox_process_undo_relheight, relheight = min(max(b * r, 0.005 * f * r), .03 * r), relwidth = self.listbox_process_undo_relwidth, anchor = tk.NW)
        self.hi_process_undo.config(command = self.listbox_process_undo.xview)
        self.listbox_process_undo.config(xscrollcommand = self.hi_process_undo.set)
        self.listbox_process_undo.bind('<Double-1>', self.listbox_process_undo_double)

        self.timestamp = datetime.now() 
        self.root.bind("<Configure>", self.on_configure) # we want to know if size changes
        self.initialized = True

    def on_configure(self, event):
        x = str(event.widget)
        #print(" x is: " + str(x))
        if x == ".!toplevel" and self.initialized: # . is toplevel window
            if (self.width != event.width):
                self.width = event.width
                #print(f"The width of Toplevel is {self.width}") if self.debug else True
            if (self.height != event.height):
                self.height = event.height
                self.Label_hist_ctr.update()
                l_height = self.Label_hist_ctr.winfo_height()
                fontsize_use = int(.8 * min(12.0, l_height * .75))
                print(f"The height of Toplevel is {self.height}, label height is {l_height} set fontsize to {fontsize_use}") if self.debug else True
                self.text_font.configure(size=fontsize_use)                
                # configure scrollbars
                self.Frame_process_hist.update()
                # the following parameters are the same for all listboxes in processlist window
                w = self.Frame_process_hist.winfo_width()
                h = self.Frame_process_hist.winfo_height()
                f = 4000 / w # for 4k screen appr. 1
                b = f * w / 50000
                r = w / h
                print("frame width / height = {:d}, {:d}".format(w, h)) if self.debug else True
                self.vi_process_hist.place(relx = self.listbox_process_hist_relwidth, rely = 0, relheight = self.listbox_process_hist_relheight, relwidth = min(max(b, 0.005 * f), .02), anchor = tk.NW)
                self.hi_process_hist.place(relx = 0, rely = self.listbox_process_hist_relheight, relheight = min(max(b * r, 0.005* f * r), .02 * r), relwidth = self.listbox_process_hist_relwidth, anchor = tk.NW)
                self.vi_process_list.place(relx = self.listbox_process_hist_relwidth, rely = 0, relheight = self.listbox_process_hist_relheight, relwidth = min(max(b, 0.005 * f), .02), anchor = tk.NW)
                self.hi_process_list.place(relx = 0, rely = self.listbox_process_hist_relheight, relheight = min(max(b * r, 0.005* f * r), .02 * r), relwidth = self.listbox_process_hist_relwidth, anchor = tk.NW)
                self.vi_process_undo.place(relx = self.listbox_process_hist_relwidth, rely = 0, relheight = self.listbox_process_hist_relheight, relwidth = min(max(b, 0.005 * f), .02), anchor = tk.NW)
                self.hi_process_undo.place(relx = 0, rely = self.listbox_process_hist_relheight, relheight = min(max(b * r, 0.005* f * r), .02 * r), relwidth = self.listbox_process_hist_relwidth, anchor = tk.NW)
       

    def update_listbox_process_hist(self, dict_p):
        # fill listbox_process_hist, we use the dict of historized processids directly
        self.listbox_process_hist.delete(0, 'end')
        ii = 0
        self.dict_text_processid = {}
        for tkey in dict_p:
            tvalue = dict_p[tkey]
            tline = "{:03d} {:s}".format(tkey, tvalue.text)
            self.listbox_process_hist.insert(END, tline)
            ii += 1
            self.dict_text_processid[tline] = tkey
        self.Label_hist_ctr.configure(text = self.Label_hist_ctr_text.format(ii))

    def update_listbox_process_list(self, dict_p, list_p):
        # fill listbox_process_list, we have a list of processids which we use as key in callers dict_processid_histobj
        self.listbox_process_list.delete(0, 'end')
        ii = 0
        for tkey in list_p:
            tvalue = dict_p[tkey]
            tline = "{:03d} {:s}".format(tkey, tvalue.text)
            self.listbox_process_list.insert(END, tline)
            ii += 1
        self.Label_list_ctr.configure(text = self.Label_list_ctr_text.format(ii))

    def update_listbox_process_undo(self, dict_p, list_p):
        # fill listbox_process_undo, we have a list of processids which we use as key in callers dict_processid_histobj
        self.listbox_process_undo.delete(0, 'end')
        ii = 0
        for tkey in list_p:
            tvalue = dict_p[tkey]
            tline = "{:03d} {:s}".format(tkey, tvalue.text)
            self.listbox_process_undo.insert(END, tline)
            ii += 1
        self.Label_undo_ctr.configure(text = self.Label_undo_ctr_text.format(ii))

    def listbox_process_hist_double(self, event = None):
        selected_indices = self.listbox_process_hist.curselection()
        if not selected_indices:
            self.procstep_selected = None
            messagebox.showwarning("Warning", "Listbox process_hist: nothing selected", parent = self.Frame_process_hist)
        else:
            procstep = ",".join([self.listbox_process_hist.get(i) for i in selected_indices]) # because listbox has single selection
            self.listbox_process_hist_selection = selected_indices[0]
            #print("*** double click procstep selected is: " + procstep) if self.debug_p else True
            self.procstep_selected = procstep
            self.pf_display(self.dict_text_processid[procstep], "double click")

    def listbox_process_hist_button_press_1(self, event = None):
        # called when left button was pressed
        selected_indices = self.listbox_process_hist.curselection()
        if selected_indices:
            procstep = ",".join([self.listbox_process_hist.get(i) for i in selected_indices]) # because listbox has single selection
            self.listbox_process_hist_selection = selected_indices[0]
            #print("*** left button pressed, procstep selected is: " + procstep) if self.debug_p else True
            self.procstep_selected = procstep
            self.pf_display(self.dict_text_processid[procstep], "left click")
    
    def listbox_process_hist_arrow_down(self, event = None):
        if self.listbox_process_hist_selection < self.listbox_process_hist.size()-1:
            self.listbox_process_hist.select_clear(self.listbox_process_hist_selection)
            self.listbox_process_hist_selection += 1
            self.listbox_process_hist.select_set(self.listbox_process_hist_selection)
            procstep = self.listbox_process_hist.get(self.listbox_process_hist_selection)
            #print("procstep selected is: " + procstep) if self.debug else True
            self.procstep_selected = procstep
            self.pf_display(self.dict_text_processid[procstep], "selection changed by arrow down")

    def listbox_process_hist_arrow_up(self, event = None):
        if self.listbox_process_hist_selection > 0:
            self.listbox_process_hist.select_clear(self.listbox_process_hist_selection)
            self.listbox_process_hist_selection -= 1
            self.listbox_process_hist.select_set(self.listbox_process_hist_selection)    
            procstep = self.listbox_process_hist.get(self.listbox_process_hist_selection)
            #print("procstep selected is: " + procstep) if self.debug else True
            self.procstep_selected = procstep
            self.pf_display(self.dict_text_processid[procstep], "selection changed by arrow up")
        
    def listbox_process_hist_selection_changed(self, event = None):
        # as double click always generates single click (from selection of entry) we want to react only if there was no double click
        # single click event comes first, double click next. 
        tsnow = datetime.now()
        tdiff = abs(tsnow - self.timestamp)
        milliseconds = tdiff.days * 86400 * 1000 + tdiff.seconds * 1000 + tdiff.microseconds / 1000
        if  milliseconds < 500: # this is a double click
            print("*** double click, diff is: ", str(milliseconds)) if self.debug_p else True
        else:
            print("*** single click, diff is: ", str(milliseconds)) if self.debug_p else True
        
        self.timestamp = tsnow    
            
        selected_indices = event.widget.curselection()
        if selected_indices:
            procstep = ",".join([self.listbox_process_hist.get(i) for i in selected_indices]) # because listbox has single selection
            self.listbox_process_hist_selection = selected_indices[0]
            print("procstep selected is: " + procstep) if self.debug else True
            self.procstep_selected = procstep
            self.pf_display(self.dict_text_processid[procstep], "selection changed")

    def listbox_process_list_double(self, event = None):
        selected_indices = self.listbox_process_list.curselection()
        if not selected_indices:
            self.procstep_selected = None
            messagebox.showwarning("Warning", "Listbox process_list: nothing selected", parent = self.Frame_process_list)
        else:
            procstep = ",".join([self.listbox_process_list.get(i) for i in selected_indices]) # because listbox has single selection
            print("procstep selected is: " + procstep) if self.debug else True
            self.procstep_selected = procstep

    def listbox_process_undo_double(self, event = None):
        selected_indices = self.listbox_process_undo.curselection()
        if not selected_indices:
            self.procstep_selected = None
            messagebox.showwarning("Warning", "Listbox process_undo: nothing selected", parent = self.Frame_process_undo)
        else:
            procstep = ",".join([self.listbox_process_undo.get(i) for i in selected_indices]) # because listbox has single selection
            print("procstep selected is: " + procstep) if self.debug else True
            self.procstep_selected = procstep

    def close_handler(self): #calles when window is closing:
        self.root.destroy()
        if self.pf_close:
            self.pf_close()

    def __del__(self):
        self.a = 1

