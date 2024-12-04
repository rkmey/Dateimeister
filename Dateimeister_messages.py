#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

# Message Output from generated scripts
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
from datetime import datetime, timezone

import Dateimeister

class MyMessagesWindow:

    # The class "constructor" - It's actually an initializer 
    def __init__(self, pmain, datadir, cmd_files_subdir, imagetype, copyscript = None, deletescript = None, delrelpathscript = None):
        self.root = tk.Toplevel()
        self.main = pmain
        self.w = Dateimeister.Toplevel_messages(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self.close_handler)

        self.datadir = datadir
        self.cmd_files_subdir = cmd_files_subdir
        self.copyscript = copyscript
        self.deletescript = deletescript
        self.delrelpathscript = delrelpathscript
        self.root.title(imagetype)
        screen_width  = int(self.root.winfo_screenwidth() * 0.7)
        screen_height = int(self.root.winfo_screenheight() * 0.5)
        print("Bildschirm ist " + str(screen_width) + " x " + str(screen_height))
        width,height=screen_width,screen_height
        v_dim=str(width)+'x'+str(height)
        self.root.geometry(v_dim)
        self.root.resizable(True, True)

        self.w.cb_delrelpath = self.w.Checkbutton_delrelpath
        self.w.cb_delrelpath_var.set(0)

        self.w.Button_execute.config(command = self.exec_handler)
        # Scrollbars
        # Script
        parent_width  = self.w.Frame_script.winfo_width()
        parent_height = self.w.Frame_script.winfo_height()
        self.VS = Scrollbar(self.w.Frame_script)
        self.VS.config(command=self.w.Text_script.yview)
        self.w.Text_script.config(yscrollcommand=self.VS.set) 
        self.HS = Scrollbar(self.w.Frame_script, orient = HORIZONTAL)
        self.HS.config(command=self.w.Text_script.xview)
        self.w.Text_script.config(xscrollcommand=self.HS.set)
        self.VS.place(relx = 1, rely = 0,     relheight = 0.98, relwidth = 0.04, anchor = tk.NE)
        self.HS.place(relx = 0, rely = 1, relheight = 0.02, relwidth = 0.96, anchor = tk.SW)

        #Messages
        parent_width  = self.w.Frame_messages.winfo_width()
        parent_height = self.w.Frame_messages.winfo_height()
        self.VM = Scrollbar(self.w.Frame_messages)
        self.VM.config(command=self.w.Text_messages.yview)
        self.w.Text_messages.config(yscrollcommand=self.VM.set)  
        self.HM = Scrollbar(self.w.Frame_messages, orient = HORIZONTAL)
        self.HM.config(command=self.w.Text_messages.xview)
        self.w.Text_messages.config(xscrollcommand=self.HM.set)
        self.VM.place(relx = 1, rely = 0,     relheight = 0.98, relwidth = 0.02, anchor = tk.NE)
        self.HM.place(relx = 0, rely = 1, relheight = 0.02, relwidth = 0.98, anchor = tk.SW)
        
        # Errors
        parent_width  = self.w.Frame_errors.winfo_width()
        parent_height = self.w.Frame_errors.winfo_height()
        self.VE = Scrollbar(self.w.Frame_errors)
        self.VE.config(command=self.w.Text_errors.yview)
        self.w.Text_errors.config(yscrollcommand=self.VE.set) 
        self.HE = Scrollbar(self.w.Frame_errors, orient = HORIZONTAL)
        self.HE.config(command=self.w.Text_errors.xview)
        self.w.Text_errors.config(xscrollcommand=self.HE.set)
        self.VE.place(relx = 1, rely = 0,     relheight = 0.98, relwidth = 0.04, anchor = tk.NE)
        self.HE.place(relx = 0, rely = 1, relheight = 0.02, relwidth = 0.96, anchor = tk.SW)
        
        # Radio Buttons for selection of script
        # control variable
        self.rb_value = tk.StringVar()
        # Radiobutton
        self.w.Radiobutton_copyscript.config(value = "copy", variable = self.rb_value, command = self.script_select)
        self.w.Radiobutton_deletescript.config(value = "delete", variable = self.rb_value, command = self.script_select)
        self.w.Radiobutton_delrelpathscript.config(value = "delrelpath", variable = self.rb_value, command = self.script_select)
        if not self.delrelpathscript:
            self.w.Radiobutton_delrelpathscript.config(state = DISABLED)
            self.w.Checkbutton_delrelpath.config(state = DISABLED)
        self.w.Radiobutton_copyscript.select()    
        self.show_script(copyscript)        
        self.action = "copy"
        self.w.Label_script.config(text = copyscript)
        self.w.Checkbutton_delrelpath.config(state = DISABLED)
        self.w.Label_scripttype.config(text = "Copyscript")
    def script_select(self):
        print("Script selected is: " + self.rb_value.get())
        if self.rb_value.get() == "copy":
            self.show_script(self.copyscript)
            self.action = "copy"
            self.w.Button_execute.config(state = NORMAL)
            self.w.Label_script.config(text = self.copyscript)
            self.w.Checkbutton_delrelpath.config(state = DISABLED)
            self.w.Label_scripttype.config(text = "Copyscript")
        elif self.rb_value.get() == "delete":
            self.show_script(self.deletescript)
            self.action = "delete"
            self.w.Button_execute.config(state = NORMAL)
            self.w.Label_script.config(text = self.deletescript)
            if self.delrelpathscript:
                self.w.Checkbutton_delrelpath.config(state = NORMAL)
            self.w.Label_scripttype.config(text = "Deletescript")
        elif self.rb_value.get() == "delrelpath" and self.delrelpathscript:
            self.show_script(self.delrelpathscript)
            self.action = "delrelpath"
            self.w.Button_execute.config(state = DISABLED)
            self.w.Label_script.config(text = self.delrelpathscript)
            self.w.Checkbutton_delrelpath.config(state = DISABLED)
            self.w.Label_scripttype.config(text = "Delrelpathscript")
        self.w.Button_execute.config(text = self.action)

    def show_script(self, script):        
        try:
            file = open(script)
        except FileNotFoundError:
            print("File does not exist: " + script)
        text = file.read()
        self.w.Text_script.delete(1.0, 'end')
        self.w.Text_script.insert('end', text)
        self.w.Text_script.insert('end', "\r\n")

    def show_messages(self, text, b_clear):
        if b_clear:
            self.w.Text_messages.delete(1.0, 'end')
        self.w.Text_messages.insert('end', text)
        self.w.Text_messages.insert('end', "\r\n")

    def show_errors(self, text, b_clear):
        if b_clear:
            self.w.Text_errors.delete(1.0, 'end')
        self.w.Text_errors.insert('end', text)
        self.w.Text_errors.insert('end', "\r\n")
        
    def exec_handler(self):
        if self.action == "copy":
            cmdfile = self.copyscript
        elif self.action == "delete" or self.action == "delrelpath":
            cmdfile = self.deletescript
        self.w.Label_script.config(text = cmdfile)
        my_cmd = "call " + cmdfile 
        owndir = os.getcwd()
        os.chdir(os.path.join(self.datadir, self.cmd_files_subdir))    
        my_cmd_output = subprocess.Popen(my_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        (output, error) = my_cmd_output.communicate()
        self.show_messages(output, True)
        self.show_errors(error, True)
        if self.action == "delete" and self.delrelpathscript is not None and self.w.cb_delrelpath_var.get():
            cmdfile_delrelpath = self.delrelpathscript
            my_cmd = "call " + cmdfile_delrelpath 
            my_cmd_output = subprocess.Popen(my_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            (output, error) = my_cmd_output.communicate()
            self.show_messages(output, False)
            self.show_errors(error, False)
            self.w.Label_script.config(text = cmdfile + ' + ' + cmdfile_delrelpath)
        os.chdir(owndir)

    def close_handler(self): #calles when window is closing:
        self.root.destroy()

    def __del__(self):
        self.a = 1
        #print("*** Deleting Camera-Objekt.")

