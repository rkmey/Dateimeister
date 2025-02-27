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

        self.Frame_process_list = tk.Frame(self.root)
        self.Frame_process_list.place(relx=.01, rely= self.frame_labels_height + .01, relheight= 1 - self.frame_labels_height -.02, relwidth=0.98)
        self.Frame_process_list.configure(relief='flat')
        self.Frame_process_list.configure(background="#d9d9d9") if self.debug else True # uncomment for same colour as window (default) or depend on debug

        # listbox for procsteps
        self.listbox_procsteps_relheight = .9
        self.listbox_procsteps_relwidth  = .9
        self.listbox_procsteps_var = tk.StringVar()
        self.listbox_procsteps = tk.Listbox(self.Frame_process_list)
        self.listbox_procsteps.place(relx=.0, rely=0, relheight= self.listbox_procsteps_relheight, relwidth=self.listbox_procsteps_relwidth)
        self.listbox_procsteps.configure(font=self.text_font)
        self.listbox_procsteps.configure(selectmode='single')
        self.listbox_procsteps.configure(listvariable=self.listbox_procsteps_var)

        # Scrollbars
        VI_PROCSTEPS = tk.Scrollbar(self.Frame_process_list, orient= VERTICAL)
        VI_PROCSTEPS.place(relx = self.listbox_procsteps_relwidth, rely = 0, relheight = self.listbox_procsteps_relheight, relwidth = .01, anchor = tk.NW)
        VI_PROCSTEPS.config(command = self.listbox_procsteps.yview)
        self.listbox_procsteps.config(yscrollcommand = VI_PROCSTEPS.set)
        HI_PROCSTEPS = tk.Scrollbar(self.Frame_process_list, orient= HORIZONTAL)
        HI_PROCSTEPS.place(relx = 0, rely = self.listbox_procsteps_relheight, relheight = 0.03, relwidth = self.listbox_procsteps_relwidth, anchor = tk.NW)
        HI_PROCSTEPS.config(command = self.listbox_procsteps.xview)
        self.listbox_procsteps.config(xscrollcommand = HI_PROCSTEPS.set)
        self.listbox_procsteps.bind('<Double-1>', self.listbox_procsteps_double)

    def on_configure(self, event):
        x = str(event.widget)
        if x == ".": # . is toplevel window
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

    def listbox_procsteps_double(self, event = None):
        selected_indices = self.listbox_procsteps_double.curselection()
        if not selected_indices:
            self.procstep_selected = None
            messagebox.showwarning("Warning", "Listbox Indir: nothing selected", parent = self.Frame_indir)
        else:
            procstep = ",".join([self.listbox_procsteps_double.get(i) for i in selected_indices]) # because listbox has single selection
            print("procstep selected is: " + procstep) if self.debug else True
            self.procstep_selected = procstep

    def close_handler(self): #calles when window is closing:
        self.root.destroy()

    def __del__(self):
        self.a = 1

