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
from time import gmtime, strftime
from datetime import datetime, timezone

import Dateimeister

class MyProcesslistWindow:

    # The class "constructor" - It's actually an initializer 
    def __init__(self, pmain, dict_processlist, debug):
        self.root = tk.Toplevel()
        self.main = pmain
        
        self.w = self.root
        self.root.protocol("WM_DELETE_WINDOW", self.close_handler)

        screen_width  = int(self.root.winfo_screenwidth() * 0.7)
        screen_height = int(self.root.winfo_screenheight() * 0.5)
        print("Bildschirm ist " + str(screen_width) + " x " + str(screen_height))
        width,height=screen_width,screen_height
        v_dim=str(width)+'x'+str(height)
        self.root.geometry(v_dim)
        self.root.resizable(True, True)

        self.dict_processlist = dict_processlist
        self.debug = debug

        self.Frame_process_list = tk.Frame(self.root)
        self.Frame_process_list.place(relx=.01, rely=0.01, relheight=0.75, relwidth=0.98)
        self.Frame_process_list.configure(relief='flat')
        self.Frame_process_list.configure(background="#d9d9d9") if self.debug else True # uncomment for same colour as window (default) or depend on debug



    def close_handler(self): #calles when window is closing:
        self.root.destroy()

    def __del__(self):
        self.a = 1

