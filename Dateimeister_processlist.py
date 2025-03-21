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
    def __init__(self, pmain, dict_processlist, debug):
        self.root = tk.Toplevel()
        self.main = pmain
        self.initialized = False
        
        self.root.protocol("WM_DELETE_WINDOW", self.close_handler)

        self.root.bind("<Configure>", self.on_configure) # we want to know if size changes
        screen_width  = int(self.root.winfo_screenwidth() * 0.7)
        screen_height = int(self.root.winfo_screenheight() * 0.5)
        print("Bildschirm ist " + str(screen_width) + " x " + str(screen_height))
        width,height=screen_width,screen_height
        v_dim=str(width)+'x'+str(height)
        self.root.geometry(v_dim)
        self.root.resizable(True, True)

        self.dict_processlist = dict_processlist
        self.debug = debug
        self.procstep_selected = None

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

        self.Label_proc_ctr = tk.Label(self.Frame_labels)
        self.Label_proc_ctr.place(relx=0.0, rely=0.0, relheight=self.label_height, relwidth=0.3)
        self.Label_proc_ctr.configure(anchor=tk.NW)
        self.Label_proc_ctr.configure(font=self.text_font)
        self.Label_proc_ctr.configure(text='Num Procteps: 0')

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

        self.initialized = True

    def on_configure(self, event):
        x = str(event.widget)
        #print(" x is: " + str(x))
        if x == ".!toplevel": # . is toplevel window
            if (self.width != event.width):
                self.width = event.width
                #print(f"The width of Toplevel is {self.width}") if self.debug else True
            if (self.height != event.height):
                self.height = event.height
                self.Label_proc_ctr.update()
                l_height = self.Label_proc_ctr.winfo_height()
                fontsize_use = int(.8 * min(12.0, l_height * .75))
                print(f"The height of Toplevel is {self.height}, label height is {l_height} set fontsize to {fontsize_use}") if self.debug else True
                self.text_font.configure(size=fontsize_use)                
            if self.initialized:
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
        # fill listbox_process_hist
        self.listbox_process_hist.delete(0, 'end')
        for tkey in dict_p:
            tvalue = dict_p[tkey]
            tline = "{:03d} {:s}".format(tkey, tvalue.text)
            self.listbox_process_hist.insert(END, tline)

    def listbox_process_hist_double(self, event = None):
        selected_indices = self.listbox_process_hist_double.curselection()
        if not selected_indices:
            self.procstep_selected = None
            messagebox.showwarning("Warning", "Listbox process_hist: nothing selected", parent = self.Frame_process_hist)
        else:
            procstep = ",".join([self.listbox_process_hist_double.get(i) for i in selected_indices]) # because listbox has single selection
            print("procstep selected is: " + procstep) if self.debug else True
            self.procstep_selected = procstep

    def listbox_process_list_double(self, event = None):
        selected_indices = self.listbox_process_list_double.curselection()
        if not selected_indices:
            self.procstep_selected = None
            messagebox.showwarning("Warning", "Listbox process_list: nothing selected", parent = self.Frame_process_list)
        else:
            procstep = ",".join([self.listbox_process_list_double.get(i) for i in selected_indices]) # because listbox has single selection
            print("procstep selected is: " + procstep) if self.debug else True
            self.procstep_selected = procstep

    def listbox_process_undo_double(self, event = None):
        selected_indices = self.listbox_process_list_double.curselection()
        if not selected_indices:
            self.procstep_selected = None
            messagebox.showwarning("Warning", "Listbox process_undo: nothing selected", parent = self.Frame_process_undo)
        else:
            procstep = ",".join([self.listbox_process_list_double.get(i) for i in selected_indices]) # because listbox has single selection
            print("procstep selected is: " + procstep) if self.debug else True
            self.procstep_selected = procstep

    def close_handler(self): #calles when window is closing:
        self.root.destroy()

    def __del__(self):
        self.a = 1

