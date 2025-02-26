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
        self.Frame_process_list.place(relx=.01, rely= self.frame_labels_height + .01, relheight= 1- self.frame_labels_height, relwidth=0.98)
        self.Frame_process_list.configure(relief='flat')
        self.Frame_process_list.configure(background="#d9d9d9") if self.debug else True # uncomment for same colour as window (default) or depend on debug

        # listbox for procsteps
        self.listbox_procsteps_var = tk.StringVar()
        self.listbox_procsteps = tk.Listbox(self.Frame_process_list)
        self.listbox_procsteps.place(relx=.0, rely=0, relheight=.9, relwidth=0.9)
        self.listbox_procsteps.configure(font=self.text_font)
        self.listbox_procsteps.configure(selectmode='single')
        self.listbox_procsteps.configure(listvariable=self.listbox_procsteps_var)


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

    def close_handler(self): #calles when window is closing:
        self.root.destroy()

    def __del__(self):
        self.a = 1

