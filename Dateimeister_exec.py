#! /usr/bin/env python3
#  -*- coding: utf-8 -*-

# Message Output from generated scripts

import os
import subprocess
import tkinter as tk
from tkinter.constants import *
from tkinter import Scrollbar

import Tooltip as TT
import tools
from tools import Globals, INCLUDE, EXCLUDE, FileStateEvent, ClosingEvent, PrintRequestEvent, CameraChangedEvent

class MyExecWindow:

    # The class "constructor" - It's actually an initializer
    def __init__(self, pmain, datadir, cmd_files_subdir, imagetype, dict_target_count, dict_source_target, dup_key,
                 copyscript=None, deletescript=None, delrelpathscript=None, debug = 'n'):
        self.root = tk.Toplevel()
        self.main = pmain

        self.datadir = datadir
        self.cmd_files_subdir = cmd_files_subdir
        self.copyscript = copyscript
        self.deletescript = deletescript
        self.delrelpathscript = delrelpathscript
        self.dict_target_count = dict_target_count
        self.dict_source_target = dict_source_target
        self._dup_key = dup_key
        self.imagetype = imagetype
        self.debug = debug

        self.root.protocol("WM_DELETE_WINDOW", self.close_handler)
        self.root.title(self.imagetype)

        # ----- Fenster-Layout (frueher Toplevel_messages in Dateimeister.py) -----
        self._build_ui()

        # Fenstergroesse an Bildschirm anpassen (wie bisher)
        screen_width  = int(self.root.winfo_screenwidth() * 0.7)
        screen_height = int(self.root.winfo_screenheight() * 0.5)
        print("Bildschirm ist " + str(screen_width) + " x " + str(screen_height))
        v_dim = str(screen_width) + 'x' + str(screen_height)
        self.root.geometry(v_dim)
        self.root.resizable(True, True)

        self.cb_delrelpath_var.set(0)
        self.Button_execute.config(command=self.exec_handler)
        self.Button_expected.config(command=self.expected_handler)

        # ----- Scrollbars -----
        # Script
        self.VS = Scrollbar(self.Frame_script)
        self.VS.config(command=self.Text_script.yview)
        self.Text_script.config(yscrollcommand=self.VS.set)
        self.HS = Scrollbar(self.Frame_script, orient=HORIZONTAL)
        self.HS.config(command=self.Text_script.xview)
        self.Text_script.config(xscrollcommand=self.HS.set)
        self.VS.place(relx=1, rely=0,     relheight=0.98, relwidth=0.04, anchor=tk.NE)
        self.HS.place(relx=0, rely=1, relheight=0.02, relwidth=0.96, anchor=tk.SW)

        # Messages
        self.VM = Scrollbar(self.Frame_messages)
        self.VM.config(command=self.Text_messages.yview)
        self.Text_messages.config(yscrollcommand=self.VM.set)
        self.HM = Scrollbar(self.Frame_messages, orient=HORIZONTAL)
        self.HM.config(command=self.Text_messages.xview)
        self.Text_messages.config(xscrollcommand=self.HM.set)
        self.VM.place(relx=1, rely=0,     relheight=0.98, relwidth=0.02, anchor=tk.NE)
        self.HM.place(relx=0, rely=1, relheight=0.02, relwidth=0.98, anchor=tk.SW)

        # Errors
        self.VE = Scrollbar(self.Frame_errors)
        self.VE.config(command=self.Text_errors.yview)
        self.Text_errors.config(yscrollcommand=self.VE.set)
        self.HE = Scrollbar(self.Frame_errors, orient=HORIZONTAL)
        self.HE.config(command=self.Text_errors.xview)
        self.Text_errors.config(xscrollcommand=self.HE.set)
        self.VE.place(relx=1, rely=0,     relheight=0.98, relwidth=0.04, anchor=tk.NE)
        self.HE.place(relx=0, rely=1, relheight=0.02, relwidth=0.96, anchor=tk.SW)

        # ----- Radiobuttons fuer Skriptauswahl -----
        self.rb_value = tk.StringVar()
        self.Radiobutton_copyscript.config(value="copy",
                                           variable=self.rb_value,
                                           command=self.script_select)
        self.Radiobutton_deletescript.config(value="delete",
                                             variable=self.rb_value,
                                             command=self.script_select)
        self.Radiobutton_delrelpathscript.config(value="delrelpath",
                                                 variable=self.rb_value,
                                                 command=self.script_select)
        if not self.delrelpathscript:
            self.Radiobutton_delrelpathscript.config(state=DISABLED)
            self.Checkbutton_delrelpath.config(state=DISABLED)
        self.Radiobutton_copyscript.select()
        self.show_script(copyscript)
        self.action = "copy"
        self.Label_script.config(text=copyscript)
        self.Checkbutton_delrelpath.config(state=DISABLED)
        self.Label_scripttype.config(text="Copyscript")

        # get expected copies, new files and overwrites
        num_expected_copies, num_override, num_new = self.count_expected_copies(Globals.imagetype)
        print(f"EXEC pressed, num expected, override, new = {num_expected_copies},{num_override},{num_new}") if self.debug else True
    # ------------------------------------------------------------------
    # UI-Aufbau (aus Dateimeister.Toplevel_messages uebernommen)
    # ------------------------------------------------------------------
    def _build_ui(self):
        top = self.root
        top.minsize(120, 1)
        top.maxsize(2564, 1421)
        top.configure(background="#d9d9d9")
        top.configure(highlightbackground="#d9d9d9")
        top.configure(highlightcolor="black")

        # Frame_messages
        self.Frame_messages = tk.Frame(top)
        self.Frame_messages.place(relx=0.262, rely=0.014, relheight=0.801,
                                  relwidth=0.48)
        self.Frame_messages.configure(relief='groove', borderwidth="2",
                                      background="#d9d9d9",
                                      highlightbackground="#d9d9d9",
                                      highlightcolor="black")

        self.Text_messages = tk.Text(self.Frame_messages)
        self.Text_messages.place(relx=0.0, rely=0.0, relheight=0.98,
                                 relwidth=0.98)
        self.Text_messages.configure(background="white", font="TkTextFont",
                                     foreground="black",
                                     highlightbackground="#d9d9d9",
                                     highlightcolor="black",
                                     insertbackground="black",
                                     selectbackground="#c4c4c4",
                                     selectforeground="black",
                                     wrap="none")

        # Frame_errors
        self.Frame_errors = tk.Frame(top)
        self.Frame_errors.place(relx=0.745, rely=0.014, relheight=0.8,
                                relwidth=0.25)
        self.Frame_errors.configure(relief='groove', borderwidth="2",
                                    background="#d9d9d9",
                                    highlightbackground="#d9d9d9",
                                    highlightcolor="black")

        self.Text_errors = tk.Text(self.Frame_errors)
        self.Text_errors.place(relx=0.0, rely=0.0, relheight=0.98,
                               relwidth=0.961)
        self.Text_errors.configure(background="white", font="TkTextFont",
                                   foreground="black",
                                   highlightbackground="#d9d9d9",
                                   highlightcolor="black",
                                   insertbackground="black",
                                   selectbackground="#c4c4c4",
                                   selectforeground="black",
                                   wrap="none")

        # Button_execute
        self.Button_execute = tk.Button(top)
        self.Button_execute.place(relx=0.179, rely=0.919, height=34, width=77)
        self.Button_execute.configure(activebackground="beige",
                                      activeforeground="black",
                                      background="#d9d9d9",
                                      compound='left',
                                      disabledforeground="#a3a3a3",
                                      font="-family {Segoe UI} -size 9",
                                      foreground="black",
                                      highlightbackground="#d9d9d9",
                                      highlightcolor="black",
                                      pady="0",
                                      text='copy')
        self.Button_execute_tooltip = TT.ToolTip(
            self.Button_execute, 'execute command')

        # Button_expected
        self.Button_expected = tk.Button(top)
        self.Button_expected.place(relx=0.179, rely=0.85, height=34, width=77)
        self.Button_expected.configure(activebackground="beige",
                                      activeforeground="black",
                                      background="#d9d9d9",
                                      compound='left',
                                      disabledforeground="#a3a3a3",
                                      font="-family {Segoe UI} -size 9",
                                      foreground="black",
                                      highlightbackground="#d9d9d9",
                                      highlightcolor="black",
                                      pady="0",
                                      text='show expected')
        self.Button_expected_tooltip = TT.ToolTip(
            self.Button_expected, 'expected command')

        # Checkbutton_delrelpath
        self.cb_delrelpath_var = tk.IntVar()
        self.Checkbutton_delrelpath = tk.Checkbutton(top)
        self.Checkbutton_delrelpath.place(relx=0.246, rely=0.919,
                                          relheight=0.046, relwidth=0.124)
        self.Checkbutton_delrelpath.configure(activebackground="beige",
                                              activeforeground="black",
                                              anchor='w',
                                              background="#d9d9d9",
                                              compound='left',
                                              disabledforeground="#a3a3a3",
                                              font="-family {Segoe UI} -size 9",
                                              foreground="black",
                                              highlightbackground="#d9d9d9",
                                              highlightcolor="black",
                                              justify='left',
                                              selectcolor="#d9d9d9",
                                              text='delrelpath',
                                              variable=self.cb_delrelpath_var)
        self.Checkbutton_delrelpath_tooltip = TT.ToolTip(
            self.Checkbutton_delrelpath, 'delete copied subdirs')

        # Frame_script
        self.Frame_script = tk.Frame(top)
        self.Frame_script.place(relx=0.007, rely=0.014, relheight=0.8,
                                relwidth=0.25)
        self.Frame_script.configure(relief='groove', borderwidth="2",
                                    background="#d9d9d9",
                                    highlightbackground="#d9d9d9",
                                    highlightcolor="black")

        self.Text_script = tk.Text(self.Frame_script)
        self.Text_script.place(relx=0.0, rely=0.0, relheight=0.98,
                               relwidth=0.961)
        self.Text_script.configure(background="white", font="TkTextFont",
                                   foreground="black",
                                   highlightbackground="#d9d9d9",
                                   highlightcolor="black",
                                   insertbackground="black",
                                   selectbackground="#c4c4c4",
                                   selectforeground="black",
                                   wrap="none")

        # Radiobuttons
        self.selectedButton = tk.IntVar()

        self.Radiobutton_copyscript = tk.Radiobutton(top)
        self.Radiobutton_copyscript.place(relx=0.015, rely=0.85,
                                          relheight=0.047, relwidth=0.095)
        self.Radiobutton_copyscript.configure(activebackground="beige",
                                              activeforeground="black",
                                              anchor='w',
                                              background="#d9d9d9",
                                              compound='left',
                                              disabledforeground="#a3a3a3",
                                              font="-family {Segoe UI} -size 9",
                                              foreground="black",
                                              highlightbackground="#d9d9d9",
                                              highlightcolor="black",
                                              justify='left',
                                              selectcolor="#d9d9d9",
                                              text='copyscript',
                                              variable=self.selectedButton)

        self.Radiobutton_deletescript = tk.Radiobutton(top)
        self.Radiobutton_deletescript.place(relx=0.015, rely=0.891,
                                            relheight=0.035, relwidth=0.086)
        self.Radiobutton_deletescript.configure(activebackground="beige",
                                                activeforeground="black",
                                                anchor='w',
                                                background="#d9d9d9",
                                                compound='left',
                                                disabledforeground="#a3a3a3",
                                                font="-family {Segoe UI} -size 9",
                                                foreground="black",
                                                highlightbackground="#d9d9d9",
                                                highlightcolor="black",
                                                justify='left',
                                                selectcolor="#d9d9d9",
                                                text='deletescript',
                                                variable=self.selectedButton)

        self.Radiobutton_delrelpathscript = tk.Radiobutton(top)
        self.Radiobutton_delrelpathscript.place(relx=0.015, rely=0.93,
                                                relheight=0.034, relwidth=0.146)
        self.Radiobutton_delrelpathscript.configure(
            activebackground="beige",
            activeforeground="black",
            anchor='w',
            background="#d9d9d9",
            compound='left',
            disabledforeground="#a3a3a3",
            font="-family {Segoe UI} -size 9",
            foreground="black",
            highlightbackground="#d9d9d9",
            highlightcolor="black",
            justify='left',
            selectcolor="#d9d9d9",
            text='delrelpathscript (view only)',
            variable=self.selectedButton)

        # Labels
        self.Label_script = tk.Label(top)
        self.Label_script.place(relx=0.44, rely=0.878, height=60, width=583)
        self.Label_script.configure(activebackground="#f9f9f9",
                                    activeforeground="black",
                                    anchor='w',
                                    background="#d9d9d9",
                                    compound='left',
                                    disabledforeground="#a3a3a3",
                                    font="-family {Segoe UI} -size 9",
                                    foreground="black",
                                    highlightbackground="#d9d9d9",
                                    highlightcolor="black",
                                    justify='left',
                                    text='Label',
                                    wraplength="500")

        self.Label_messages = tk.Label(top)
        self.Label_messages.place(relx=0.462, rely=0.824,
                                  height=20, width=123)
        self.Label_messages.configure(activebackground="#f9f9f9",
                                      activeforeground="black",
                                      anchor='w',
                                      background="#d9d9d9",
                                      compound='left',
                                      disabledforeground="#a3a3a3",
                                      font="-family {Segoe UI} -size 9",
                                      foreground="black",
                                      highlightbackground="#d9d9d9",
                                      highlightcolor="black",
                                      text='Messages')

        self.Label_errors = tk.Label(top)
        self.Label_errors.place(relx=0.835, rely=0.824, height=20, width=102)
        self.Label_errors.configure(activebackground="#f9f9f9",
                                    activeforeground="black",
                                    anchor='w',
                                    background="#d9d9d9",
                                    compound='left',
                                    disabledforeground="#a3a3a3",
                                    font="-family {Segoe UI} -size 9",
                                    foreground="black",
                                    highlightbackground="#d9d9d9",
                                    highlightcolor="black",
                                    text='Errors')

        self.Label_scripttype = tk.Label(top)
        self.Label_scripttype.place(relx=0.052, rely=0.824,
                                    height=20, width=202)
        self.Label_scripttype.configure(activebackground="#f9f9f9",
                                        activeforeground="black",
                                        anchor='w',
                                        background="#d9d9d9",
                                        compound='left',
                                        disabledforeground="#a3a3a3",
                                        font="-family {Segoe UI} -size 9",
                                        foreground="black",
                                        highlightbackground="#d9d9d9",
                                        highlightcolor="black",
                                        text='Label')

    # ------------------------------------------------------------------
    # Verhalten (unveraendert aus der bisherigen My-Messages-Window)
    # ------------------------------------------------------------------
    def script_select(self):
        print("Script selected is: " + self.rb_value.get())
        if self.rb_value.get() == "copy":
            self.show_script(self.copyscript)
            self.action = "copy"
            self.Button_execute.config(state=NORMAL)
            self.Label_script.config(text=self.copyscript)
            self.Checkbutton_delrelpath.config(state=DISABLED)
            self.Label_scripttype.config(text="Copyscript")
        elif self.rb_value.get() == "delete":
            self.show_script(self.deletescript)
            self.action = "delete"
            self.Button_execute.config(state=NORMAL)
            self.Label_script.config(text=self.deletescript)
            if self.delrelpathscript:
                self.Checkbutton_delrelpath.config(state=NORMAL)
            self.Label_scripttype.config(text="Deletescript")
        elif self.rb_value.get() == "delrelpath" and self.delrelpathscript:
            self.show_script(self.delrelpathscript)
            self.action = "delrelpath"
            self.Button_execute.config(state=DISABLED)
            self.Label_script.config(text=self.delrelpathscript)
            self.Checkbutton_delrelpath.config(state=DISABLED)
            self.Label_scripttype.config(text="Delrelpathscript")
        self.Button_execute.config(text=self.action)

    def show_script(self, script):
        try:
            with open(script, encoding=tools.CMD_FILE_ENCODING) as file:
                text = file.read()
        except FileNotFoundError:
            print("File does not exist: " + script)
            return
        self.Text_script.delete(1.0, 'end')
        self.Text_script.insert('end', text)
        self.Text_script.insert('end', "\r\n")

    def show_messages(self, text, b_clear):
        if b_clear:
            self.Text_messages.delete(1.0, 'end')
        self.Text_messages.insert('end', text)
        self.Text_messages.insert('end', "\r\n")

    def show_errors(self, text, b_clear):
        if b_clear:
            self.Text_errors.delete(1.0, 'end')
        self.Text_errors.insert('end', text)
        self.Text_errors.insert('end', "\r\n")

    def expected_handler(self):
        num_expected_copies = self.count_expected_copies(Globals.imagetype)
        print(f"Expected pressed, num expected = {num_expected_copies}") if self.debug else True

    def exec_handler(self):
        if self.action == "copy":
            cmdfile = self.copyscript
        elif self.action == "delete" or self.action == "delrelpath":
            cmdfile = self.deletescript
        self.Label_script.config(text=cmdfile)
        owndir = os.getcwd()
        os.chdir(os.path.join(self.datadir, self.cmd_files_subdir))

        process = subprocess.Popen(
            ["cmd.exe"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="cp850",
            errors="replace",
            bufsize=1
        )

        lines_total = 0
        lines_up_to_here = 0
        lines_exec = 0
        lines_exec_success = 0
        output   = []
        messages = []
        errors   = []
        # we process one command after another
        try:
            with open(cmdfile, encoding="cp850") as file:
                lines_total = sum(1 for line in file)            
            lines_up_to_here = 0
            lines_exec = 0
            lines_exec_success = 0
            with open(cmdfile, encoding="cp850") as file:
                busy = tools.BusyDialog(self.root, text= f"executing {cmdfile}")
                for line in file:
                    lines_up_to_here += 1
                    command = line.strip()
                    if not busy.cancelled:
                        if not command or command.lower().startswith(("rem ", "@rem ")):
                            continue
                        lines_exec += 1

                        # exec and show error status
                        process.stdin.write(command + "\n")
                        process.stdin.write('@echo __RESULT__%ERRORLEVEL%\n')
                        process.stdin.flush()

                        # Auf Ergebnis warten
                        output = []
                        while True:
                            result = process.stdout.readline()
                            output.append(result)
                            if result == "":
                                raise RuntimeError(
                                    "cmd.exe unexpededly ended"
                                )
                            if result.startswith("__RESULT__"):
                                errorlevel = int(
                                    result.split("__RESULT__")[1]
                                )
                                break

                        busy.update_progress(lines_up_to_here, lines_total)
                        if errorlevel == 0:
                            message = f"{command}: {errorlevel}"
                            lines_exec_success += 1
                            messages.append(message)
                        else:
                            error_text = "".join(output).replace("\r", " ").replace("\n", " ").strip()
                            errors.append(error_text)
                    else: 
                        break
                        command = line.strip()
                busy.close()

        finally:
            process.stdin.write("exit\n")
            process.stdin.close()
            process.wait()
            self.show_messages("\n".join(messages), True)
            if (lines_exec - lines_exec_success) > 0:
                self.show_errors("\n".join(errors), True)
                tools.info_box(parent = self.root,
                    nachricht = f"errors ({lines_exec - lines_exec_success}) during {self.action}, check messages and errors",
                    level = "warnung"
                )

        if (self.action == "delete" and self.delrelpathscript is not None
                and self.cb_delrelpath_var.get()):
            cmdfile_delrelpath = self.delrelpathscript
            my_cmd = "call " + cmdfile_delrelpath
            my_cmd_output = subprocess.Popen(
                my_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                shell=True)
            (output, error) = my_cmd_output.communicate()
            self.show_messages(output, False)
            self.show_errors(error, False)
            self.Label_script.config(text=cmdfile + ' + ' + cmdfile_delrelpath)
        os.chdir(owndir)

    def count_expected_copies(self, imagetype):
        """Anzahl der Dateien, die beim Exec tatsaechlich kopiert werden.

        Startet mit der Anzahl der Ziele (= Anzahl der moeglichen Kopien)
        und zieht fuer jede ausgeschlossene Quelle eine Kopie ab. Ist der
        Count eines Ziels dadurch 0, wird das Ziel gar nicht kopiert und
        die erwartete Anzahl sinkt um 1.

        Das Zaehl-Dict wird dabei NICHT dauerhaft veraendert - es wird
        eine Arbeitskopie benutzt, damit wiederholte Aufrufe dasselbe
        Ergebnis liefern.
        """
        base = self.dict_target_count.get(imagetype, {})
        counts = dict(base)
        num_expected = len(counts)
        thumbnails = Globals.dict_thumbnails.get(imagetype, {})
        source_target = self.dict_source_target.get(imagetype, {})   # <-- .get statt []

        for src, tgt in source_target.items():
            th = thumbnails.get(src)
            if th is not None and th.getState() == EXCLUDE:
                key = self._dup_key(tgt)
                counts[key] -= 1
                if counts[key] == 0:
                    num_expected -= 1
        
        num_new = 0
        num_override = 0
        for t in counts:
            n = counts[t]
            if n > 0: # not excluded
                if tools.isfile_fast(t):
                    print(f"{t} : already exists") if self.debug else True
                    num_override += 1
                else:
                    print(f"{t} : does not exist") if self.debug else True
                    num_new += 1
        return num_expected, num_override, num_new


    def close_handler(self):
        self.root.destroy()

    def __del__(self):
        self.a = 1