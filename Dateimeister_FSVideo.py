import sys
import os
import argparse
import time
import inspect
from PIL import Image, ImageTk
import socket
import json

import tkinter as tk
from tkinter import ttk
from tkinter.font import Font
import gc
#gc.disable() # disable garbage collection

# windows timer base to 1ms instead of system default
import ctypes
import atexit

import subprocess
import threading
import queue
import uuid
import tools
import Tooltip as TT
from tools import Globals, INCLUDE, EXCLUDE, FileStateEvent, ClosingEvent, PrintRequestEvent


# ----------------------------------------------------------------------
# Metadata treeview: heading labels and button texts
# ----------------------------------------------------------------------
HEAD_CATEGORY    = "Category"
HEAD_KEY         = "Key"
HEAD_VALUE       = "Value"

NO_METADATA_TEXT = "(no metadata)"

BTN_ALL_META     = "view all meta"
BTN_SEL_META     = "view selected meta"


def format_time(seconds):
    """Formats seconds as mm:ss, or h:mm:ss if >= 1 hour."""
    if seconds is None or seconds < 0:
        seconds = 0
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

# window for displaying thumb on position scale
class PreviewTooltip(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)  # no window border
        self.label = tk.Label(self, bg="black")
        self.label.pack()
        self.withdraw()  # start hidden

        # keep tooltip above its master
        self.transient(master)
        self.lift(master)
        self.attributes("-topmost", True)

    def show(self, x, y, photo):
        # clamp position to screen (no negative coords)
        x = max(0, x)
        y = max(0, y)

        self.label.config(image=photo)
        self.label.image = photo  # keep reference
        self.geometry(f"+{x}+{y}")
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)

    def hide(self):
        self.withdraw()


class MpvIPC:
    """Small helper class to control an mpv instance via its
    --input-ipc-server named pipe (Windows). Thread-safe for simple
    calls (a lock protects write+read of one request/response)."""

    def __init__(self, pipe_name, timeout_connect=8.0):
        self.pipe_name = pipe_name
        self.pipe = None
        self._lock = threading.Lock()
        self._read_buf = b""
        self._next_id = 1
        self._connect(timeout_connect)

    def _connect(self, timeout):
        start = time.perf_counter()
        last_err = None
        while time.perf_counter() - start < timeout:
            try:
                self.pipe = open(self.pipe_name, "r+b", buffering=0)
                return
            except OSError as e:
                last_err = e
                time.sleep(0.1)
        raise RuntimeError(f"mpv IPC pipe {self.pipe_name} not reachable: {last_err}")

    def _read_line(self):
        while b"\n" not in self._read_buf:
            chunk = self.pipe.read(4096)
            if not chunk:
                raise RuntimeError("mpv pipe was closed unexpectedly")
            self._read_buf += chunk
        line, self._read_buf = self._read_buf.split(b"\n", 1)
        return line

    def command(self, cmd_list, timeout=3.0):
        """Sends a command synchronously and waits for the response with
        the matching request_id (unsolicited event lines are ignored)."""
        with self._lock:
            if self.pipe is None:
                return None
            rid = self._next_id
            self._next_id += 1
            payload = {"command": cmd_list, "request_id": rid}
            try:
                self.pipe.write((json.dumps(payload) + "\n").encode("utf-8"))
            except OSError:
                return None

            start = time.perf_counter()
            while time.perf_counter() - start < timeout:
                try:
                    line = self._read_line()
                except RuntimeError:
                    return None
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                if msg.get("request_id") == rid:
                    return msg
                # otherwise: unsolicited event, ignore and keep reading
            return None

    def set_property(self, name, value):
        return self.command(["set_property", name, value])

    def get_property(self, name):
        resp = self.command(["get_property", name])
        if resp and resp.get("error") == "success":
            return resp.get("data")
        return None

    def toggle_pause(self):
        return self.command(["cycle", "pause"])

    def seek(self, amount, mode="relative"):
        return self.command(["seek", amount, mode])

    def close(self):
        try:
            if self.pipe:
                self.pipe.close()
        except OSError:
            pass


class MyFSVideo:

    def __init__(
        self, 
        file: str = None, 
        thumbnail: tools.MyThumbnail = None, 
        caller: object = None, # can be several class instances, we dont enumerate all the candidates
        str_title_prefix: str = None, 
        str_include: str = None,
        str_exclude: str = None,
        str_included: str = None,
        str_excluded: str = None,
        temp_dir: str = None,
        num_thumbnails: int = None, 
        mpv_path: str = None, 
        ffprobe_path: str = None,
        debug: bool = False
    ): 
        self.player = None
        self.file = file
        self.str_include = str_include
        self.str_exclude = str_exclude
        self.str_included = str_included
        self.str_excluded = str_excluded
        self.debug = debug
        self.mpv_path = mpv_path
        self.ffprobe_path = ffprobe_path
        self.temp_dir = temp_dir
        self.thumbnail = thumbnail
        self.caller = caller
        self.text_font = Font(family="Helvetica", size=6)

        self.is_paused = False                  # mpv starts playing by default
        self._auto_paused_by_focus = False      # True if WE auto-paused on focus loss

        # for "hold" on frame-step buttons
        self._frame_hold_after_id = None
        self._frame_hold_step_func = None
        self._frame_hold_press_time = None
        self._frame_key_down = False       # prevents Tkinter key auto-repeat
        self.root = tk.Toplevel()
        # window size
        self.physical_width  = self.root.winfo_screenwidth()
        self.physical_height = self.root.winfo_screenheight()
        self.screen_width  = int(self.root.winfo_screenwidth() * .75) # adjust as needed
        self.screen_height = int(self.root.winfo_screenheight() * .75) # adjust as needed
        print("Screen is " + str(self.screen_width) + " x " + str(self.screen_height) + " physical: " + str(self.physical_width) + " x " + str(self.physical_height))
        v_dim=str(self.screen_width)+'x'+str(self.screen_height)
        self.root.geometry(v_dim)
        self.root.minsize(int(self.physical_width / 4), int(self.physical_height / 4))  # (minimum) width, (minimum) height
        self.root.resizable(True, True)

        self.root.update()
        
        self.is_fullscreen = False
        self._last_mouse_pos = None
        self._hide_timer_id = None
        self._mouse_watch_id = None
        
        # Frames and canvas
        # PanedWindow replaces the 3 root grid rows
        self.paned = ttk.PanedWindow(self.root, orient="vertical")
        self.paned.grid(row=0, column=0, sticky="nsew")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # container for the upper area (video + controls, 9:1 fixed)
        self.top_container = tk.Frame(self.paned)
        self.top_container.grid_rowconfigure(0, weight=9)
        self.top_container.grid_rowconfigure(1, weight=0)
        self.top_container.grid_columnconfigure(0, weight=1)

        # Frames
        self.frame_video    = tk.Frame(self.top_container, bg="black")
        self.frame_controls = tk.Frame(self.top_container, bg="gray20")
        self.frame_info     = tk.Frame(self.paned, bg="gray")

        self.frame_video.grid(row=0, column=0, sticky="nsew")
        self.frame_controls.grid(row=1, column=0, sticky="ew")

        # add panes
        self.paned.add(self.top_container, weight=9)
        self.paned.add(self.frame_info, weight=1)
        
        
        self.canvas_gallery = tk.Canvas(self.frame_video, bg="black")

        # IMPORTANT: canvas must not demand its own height
        self.canvas_gallery.configure(height=1)

        self.canvas_gallery.pack(fill="both", expand=True)
        self.root.update_idletasks()
        print("AFTER LAYOUT:")
        print("root       :", self.root.winfo_width(), self.root.winfo_height())
        print("frame video:", self.frame_video.winfo_width(), self.frame_video.winfo_height())
        print("frame prev :", self.frame_info.winfo_width(), self.frame_info.winfo_height())
        print("canvas vid :", self.canvas_gallery.winfo_width(), self.canvas_gallery.winfo_height())

        self.pipe_name_thumb = rf"\\.\pipe\mpvthumb_{uuid.uuid4().hex}" # we need a unique name
        self.num_t = num_thumbnails
        
        # create the small window for previewing frames on the position scale
        self.tooltip = PreviewTooltip(self.root)

        self.preview_photos = []
        self.preview_photos = self.generate_thumbnails(self.num_t, self.frame_video.winfo_height() // 15)
        
        video_path = self.file
        wid = self.canvas_gallery.winfo_id()
        self.pipe_name_main = rf"\\.\pipe\mpvmain_{uuid.uuid4().hex}"
        self.mpv_proc = subprocess.Popen([
            self.mpv_path,
            f"--wid={wid}",
            "--no-border",
            "--keep-open=yes",
            "--loop-file=no",
            f"--input-ipc-server={self.pipe_name_main}",
            video_path
        ])

        self.mpv_ipc = None
        self._seeking = False
        self._stop_polling = False

        # Flag for the metadata button
        self.show_all_meta = False

        self.build_controls()

        # initial population of the metadata treeview (thumbnail.metadata)
        self._populate_metadata_tree()

        threading.Thread(target=self._connect_main_ipc, daemon=True).start()

        # Space pauses/resumes, independent of which child widget has focus
        # (see takefocus=0 on the control buttons below, otherwise a previously
        # clicked button would swallow the space key itself)
        self.root.bind("<space>", self._on_space_key)
        
        # get / lose focus: trigger play / pause
        self.root.bind("<FocusIn>", self.on_focus_in)
        self.root.bind("<FocusOut>", self.on_focus_out)
        self.root.focus_set()

        self.root.protocol("WM_DELETE_WINDOW", self.close_handler)
        # 20260915 for better maintenance we convert the whole mechanism from callbacks to events; register event handlers
        Globals.eventManager.bind("FileStateChanged", self.on_file_state_changed) # include<=>exclude
        Globals.eventManager.bind("Closing", self.on_closing) # if a window or a process like generate closes


        self.width  = 0
        self.height = 0
        self.timer = tools.RestartableTimer(self.root, 666, self.resize)  # ms
        self.root.bind("<Configure>", self.on_configure) # we want to know if size changes
        self.root.after(0, self.resize) # force window height / width to work and call initial resize for fonts

    def on_configure(self, event):
        x = event.widget
        if x == self.root:
            if (self.width != event.width or self.height != event.height):
                self.timer.start()

    def resize(self):
        try:
            if not self.root.winfo_exists():
                # Window has already been destroyed -> disable the timer
                if hasattr(self, 'timer') and self.timer:
                    try:
                        self.timer.cancel()
                    except:
                        pass
                    self.timer = None
                return
        except:
            # On any error just return
            return
        
        # display debug info for resize, this is very difficult to debug
        self.debug_info_resize("TIMER") if self.debug else True
        old_width  = self.width
        old_height = self.height
        # we use the new dimension of the frame for calculating the fontsize needed
        self.root.update()
        new_width  = self.root.winfo_width()
        new_height = self.root.winfo_height()
        if (old_width != new_width or old_height != new_height):
            # store new values
            self.width  = new_width
            self.height = new_height
            # we calculate the correction factor for zoom
            self.text_font.configure(size=tools.calc_fontsize(self.physical_width, self.physical_height, self.width, self.height, self.debug)) 

            # Metadata treeview: font + rowheight to match the new font size
            try:
                fm = Font(font=self.text_font)
                rowheight = fm.metrics("linespace") + 2
                style = ttk.Style(self.root)
                style.configure("Metadata.Treeview",
                                font=self.text_font,
                                rowheight=rowheight)
                style.configure("Metadata.Treeview.Heading",
                                font=self.text_font)
            except Exception:
                pass

    def debug_info_resize(self, text):
        print("{:s} elapsed start resize".format(text))


    # ------------------------------------------------------------------
    # Control of the main player (mpv_proc) via IPC
    # ------------------------------------------------------------------

    def _connect_main_ipc(self):
        try:
            self.mpv_ipc = MpvIPC(self.pipe_name_main)
        except RuntimeError as e:
            print(f"Could not connect to main mpv: {e}")
            return
        threading.Thread(target=self._poll_position, daemon=True).start()

    def _poll_position(self):
        while not self._stop_polling:
            if self.mpv_ipc and not self._seeking:
                pos = self.mpv_ipc.get_property("time-pos")
                paused = self.mpv_ipc.get_property("pause")
                if pos is not None and self.duration:
                    pct = max(0.0, min(100.0, (pos / self.duration) * 100.0))
                    try:
                        self.root.after(0, lambda p=pct, t=pos, pa=paused: self._update_position_ui(p, t, pa))
                    except RuntimeError:
                        break  # window already destroyed
            time.sleep(0.5)

    def _update_position_ui(self, pct, current_seconds, paused=None):
        self.var_position.set(pct)
        self.lbl_time.config(text=f"{format_time(current_seconds)} / {format_time(self.duration)}")
        if paused is not None:
            self._set_paused_state(bool(paused))

    def build_controls(self):
        f = self.frame_controls

        btn_restart = tk.Button(f, text="⏮", width=3, command=self.restart_video, takefocus=0)
        TT.ToolTip(btn_restart, 'restart from begin')
        btn_back    = tk.Button(f, text="⏪10s", command=lambda: self.seek_relative(-10), takefocus=0)
        TT.ToolTip(btn_back, '10 sec. back')
        btn_frame_back = tk.Button(f, text="|◀", width=3, takefocus=0)
        TT.ToolTip(btn_frame_back, 'frame(s) back')
        self.btn_playpause = tk.Button(f, text="⏯", width=3, command=self.toggle_playpause, takefocus=0)
        TT.ToolTip(self.btn_playpause, 'play / pause')
        btn_frame_fwd  = tk.Button(f, text="▶|", width=3, takefocus=0)
        TT.ToolTip(btn_frame_fwd, 'frame(s) forward')
        btn_fwd     = tk.Button(f, text="10s⏩", command=lambda: self.seek_relative(10), takefocus=0)
        TT.ToolTip(btn_fwd, '10 sec. forward')
        self.btn_print = tk.Button(f, text="🖶 Print", command=self.print_frame, takefocus=0, state=tk.DISABLED)
        TT.ToolTip(self.btn_print, 'send frame to print preview')

        btn_frame_back.bind("<ButtonPress-1>", lambda e: self._on_frame_button_press(self.frame_step_backward))
        btn_frame_back.bind("<ButtonRelease-1>", lambda e: self._on_frame_button_release())
        btn_frame_fwd.bind("<ButtonPress-1>", lambda e: self._on_frame_button_press(self.frame_step_forward))
        btn_frame_fwd.bind("<ButtonRelease-1>", lambda e: self._on_frame_button_release())
        
        self.root.bind("<KeyPress-Left>",
                       lambda e: self._on_frame_key_press(self.frame_step_backward))
        self.root.bind("<KeyRelease-Left>", self._on_frame_key_release)
        self.root.bind("<KeyPress-Right>",
                       lambda e: self._on_frame_key_press(self.frame_step_forward))
        self.root.bind("<KeyRelease-Right>", self._on_frame_key_release)


        btn_restart.grid(row=0, column=0, padx=2, pady=2)
        btn_back.grid(row=0, column=1, padx=2, pady=2)
        btn_frame_back.grid(row=0, column=2, padx=2, pady=2)
        self.btn_playpause.grid(row=0, column=3, padx=2, pady=2)
        btn_frame_fwd.grid(row=0, column=4, padx=2, pady=2)
        btn_fwd.grid(row=0, column=5, padx=2, pady=2)
        self.btn_print.grid(row=0, column=6, padx=(8, 2), pady=2)

        self.btn_fullscreen = tk.Button(f, text="⛶", width=3, command=self.toggle_fullscreen, takefocus=0)
        TT.ToolTip(self.btn_fullscreen, 'full screen, esc to return to window')
        self.btn_fullscreen.grid(row=0, column=13, padx=(8, 2), pady=2)        
        
        self.var_position = tk.DoubleVar(value=0.0)
        
        self.lbl_time = tk.Label(f, text=f"00:00 / {format_time(self.duration)}",
                                  bg="gray20", fg="white", width=12)
        self.lbl_time.grid(row=0, column=7, padx=(8, 4), pady=2)

        self.scale_position = tk.Scale(
            f, from_=0, to=100, orient="horizontal", showvalue=False,
            resolution=0.1, variable=self.var_position, length=300,
        )
        self.scale_position.grid(row=0, column=8, padx=8, pady=2, sticky="ew")
        self.scale_position.bind("<ButtonPress-1>", self._on_seek_press)
        self.scale_position.bind("<ButtonRelease-1>", self._on_seek_release)
        self.scale_position.bind("<Motion>", self._on_scale_position_motion)
        self.scale_position.bind("<Leave>",  self._on_scale_position_leave)

        f.grid_columnconfigure(8, weight=1)

        self.var_mute = tk.BooleanVar(value=False)
        chk_mute = tk.Checkbutton(f, text="Mute", variable=self.var_mute,
                                   command=self.on_mute_toggle, bg="gray20", fg="white",
                                   selectcolor="gray30", takefocus=0)
        chk_mute.grid(row=0, column=9, padx=4, pady=2)

        tk.Label(f, text="Vol", bg="gray20", fg="white").grid(row=0, column=10, padx=(8, 0))
        self.var_volume = tk.IntVar(value=100)
        scale_volume = tk.Scale(
            f, from_=0, to=150, orient="horizontal", showvalue=True,
            variable=self.var_volume, length=140, command=self.on_volume_change,
        )
        scale_volume.grid(row=0, column=11, padx=(0, 8), pady=2)

        # ------------------------------------------------------------------
        # Metadata treeview and controls in frame_info
        # ScrolledTreeView uses pack internally, so we use pack here too
        # (grid + pack in the same parent is not allowed in Tkinter).
        # ------------------------------------------------------------------
        f = self.frame_info

        f.pack_propagate(False)   # important: prevents the frame from sizing
                                  # itself to its children, keeps PanedWindow size

        style = ttk.Style(self.root)
        style.configure("Metadata.Treeview", font=self.text_font)
        style.configure("Metadata.Treeview.Heading", font=self.text_font)

        self.tv = tools.ScrolledTreeView(f, style="Metadata.Treeview")
        self.tv.configure(columns="Col1, Col2, Col3")
        self.tv.heading("#0", text=HEAD_CATEGORY, anchor="w")
        self.tv.heading("#1", text=HEAD_KEY,      anchor="w")
        self.tv.heading("#2", text=HEAD_VALUE,    anchor="w")
        self.tv.column("#0", width=120, minwidth=120, stretch=True, anchor="w")
        self.tv.column("#1", width=180, minwidth=180, stretch=True, anchor="w")
        self.tv.column("#2", width=240, minwidth=240, stretch=True, anchor="w")

        # Pack button and label to the right first, so treeview fills the rest
        self.lbl_inex = tk.Label(f, text="inex", bg="gray20", fg="white")
        self.lbl_inex.pack(side="right", padx=2, pady=2, anchor="n")

        self.btn_inex = tk.Button(f, text="inex", width=15, command=self.on_button_state)
        TT.ToolTip(self.btn_inex, 'include / exclude video')
        self.btn_inex.pack(side="right", padx=2, pady=2, anchor="n")

        self.btn_all_meta = tk.Button(f, text=BTN_ALL_META, width=15, command=self.on_button_all_meta)
        TT.ToolTip(self.btn_all_meta, 'toggle between selected and all metadata')
        self.btn_all_meta.pack(side="right", padx=2, pady=2, anchor="n")

        # Treeview last, on the left
        self.tv.pack(side="left", fill="both", expand=True)


    def on_focus_in(self, event):
        if not self.mpv_ipc:
            return
        # only resume if WE paused on focus loss - a manual pause (space key,
        # frame-step) or a print preparation must not be undone by a focus change
        if self._auto_paused_by_focus and self.is_paused:
            print("got focus back - resuming (was auto-paused on focus loss)") if self.debug else True
            self.toggle_playpause()
        self._auto_paused_by_focus = False

    def on_focus_out(self, event):
        if not self.mpv_ipc:
            return
        if not self.is_paused:
            print("lost focus - auto-pausing") if self.debug else True
            self.toggle_playpause()
            self._auto_paused_by_focus = True
        else:
            # was already paused (manual or via frame-step) - that was not
            # our auto-pause, so do NOT resume automatically on focus in
            self._auto_paused_by_focus = False

    def activate(self):
        self.root.deiconify()      # in case it is minimized
        self.root.lift()
        self.root.focus_force()

    # all the functions for fullscreen and back to window, including small control panel in fullscreen mode
    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.exit_fullscreen()
            return

        self.is_fullscreen = True

        self.paned.forget(self.frame_info)

        self.frame_controls.grid_remove()
        self.top_container.grid_rowconfigure(0, weight=1)
        self.top_container.grid_rowconfigure(1, weight=0)

        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", self.exit_fullscreen)

        self._show_controls_overlay()
        self._start_mouse_watch()

    def exit_fullscreen(self, event=None):
        if not self.is_fullscreen:
            return
        self.is_fullscreen = False

        # stop timer/polling
        if self._hide_timer_id:
            self.root.after_cancel(self._hide_timer_id)
            self._hide_timer_id = None
        if self._mouse_watch_id:
            self.root.after_cancel(self._mouse_watch_id)
            self._mouse_watch_id = None

        self.root.attributes("-fullscreen", False)
        self.root.unbind("<Escape>")

        self.frame_controls.place_forget()
        self.frame_controls.grid()
        self.top_container.grid_rowconfigure(0, weight=9)
        self.top_container.grid_rowconfigure(1, weight=0)

        self.paned.add(self.frame_info, weight=1)

    def _show_controls_overlay(self):
        self.frame_controls.place(in_=self.top_container, relx=0, rely=1.0,
                                   anchor="sw", relwidth=1.0)
        self.frame_controls.lift()

        if self._hide_timer_id:
            self.root.after_cancel(self._hide_timer_id)
        self._hide_timer_id = self.root.after(2500, self._hide_controls_overlay)

    def _hide_controls_overlay(self):
        self._hide_timer_id = None
        if self.is_fullscreen:
            self.frame_controls.place_forget()

    def _start_mouse_watch(self):
        pos = (self.root.winfo_pointerx(), self.root.winfo_pointery())
        if pos != self._last_mouse_pos:
            self._last_mouse_pos = pos
            self._show_controls_overlay()

        if self.is_fullscreen:
            self._mouse_watch_id = self.root.after(150, self._start_mouse_watch)
    # End: fullscreen handling


    def toggle_playpause(self):
        if self.mpv_ipc:
            self.mpv_ipc.toggle_pause()
            self._sync_paused_state_now()

    def _on_space_key(self, event=None):
        self.toggle_playpause()
        return "break"

    FRAME_HOLD_THRESHOLD_MS = 1000   # hold this long before repeat starts
    FRAME_HOLD_REPEAT_MS = 250       # 4 frames per second while holding
    FRAME_HOLD_FAST_AFTER_S = 4.0    # faster after this many total seconds held
    FRAME_HOLD_REPEAT_FAST_MS = 125  # 8 frames per second from then on

    def frame_step_forward(self):
        if self.mpv_ipc:
            self.mpv_ipc.command(["frame-step"])  # pauses automatically if still playing
            self._sync_paused_state_now()

    def frame_step_backward(self):
        if self.mpv_ipc:
            self.mpv_ipc.command(["frame-back-step"])  # pauses automatically if still playing
            self._sync_paused_state_now()

    def _on_frame_key_press(self, step_func):
        # Windows/Tkinter fires additional KeyPress events while a key is held.
        # Those must not restart our hold mechanism every time.
        if self._frame_key_down:
            return "break"

        self._frame_key_down = True
        self._on_frame_button_press(step_func)
        return "break"

    def _on_frame_key_release(self, event=None):
        if not self._frame_key_down:
            return "break"

        self._frame_key_down = False
        self._on_frame_button_release()
        return "break"

    def _on_frame_button_press(self, step_func):
        self._cancel_frame_hold_timer()
        self._frame_hold_step_func = step_func
        self._frame_hold_press_time = time.time()
        step_func()  # the normal single step, as with a short click
        self._frame_hold_after_id = self.root.after(
            self.FRAME_HOLD_THRESHOLD_MS, self._start_frame_hold_repeat
        )

    def _start_frame_hold_repeat(self):
        if self._frame_hold_step_func is None:
            return  # released in the meantime
        self._frame_hold_step_func()
        elapsed = time.time() - self._frame_hold_press_time
        interval = (
            self.FRAME_HOLD_REPEAT_FAST_MS
            if elapsed >= self.FRAME_HOLD_FAST_AFTER_S
            else self.FRAME_HOLD_REPEAT_MS
        )
        self._frame_hold_after_id = self.root.after(interval, self._start_frame_hold_repeat)

    def _on_frame_button_release(self):
        self._cancel_frame_hold_timer()
        self._frame_hold_step_func = None

    def _cancel_frame_hold_timer(self):
        if self._frame_hold_after_id is not None:
            self.root.after_cancel(self._frame_hold_after_id)
            self._frame_hold_after_id = None

    def _sync_paused_state_now(self):
        """Ask for pause state immediately instead of waiting for the next
        poll cycle (up to 0.5s) - for direct feedback after a user action
        (play/pause, frame-step)."""
        if not self.mpv_ipc:
            return
        paused = self.mpv_ipc.get_property("pause")
        if paused is not None:
            self._set_paused_state(bool(paused))

    def _set_paused_state(self, paused: bool):
        self.is_paused = paused
        self.btn_print.config(state=tk.NORMAL if paused else tk.DISABLED)

    def print_frame(self):
        if not self.mpv_ipc or not self.is_paused:
            return  # button should be disabled anyway, double check

        filename = os.path.join(self.temp_dir, f"print_frame_{uuid.uuid4().hex}.png")
        self.mpv_ipc.command(["screenshot-to-file", filename, "video"])

        for _ in range(100):
            if os.path.exists(filename):
                break
            time.sleep(0.01)

        if not os.path.exists(filename):
            tools.info_box("Could not capture the current frame.", "fehler")
            return

        # Forward the print request to the central print logic in
        # Dateimeister_support. Creating / managing the PrintPreview happens
        # exclusively there.
        Globals.eventManager.generate(
            "PrintRequestEvent",
            PrintRequestEvent(filename, self)
        )


    def restart_video(self):
        if self.mpv_ipc:
            self.mpv_ipc.seek(0, "absolute")
            self.mpv_ipc.set_property("pause", False)
            self.var_position.set(0.0)
            self.lbl_time.config(text=f"00:00 / {format_time(self.duration)}")
            self._sync_paused_state_now()

    def seek_relative(self, secs):
        if self.mpv_ipc:
            self.mpv_ipc.seek(secs, "relative")

    def _on_seek_press(self, event):
        self._seeking = True

    def _on_seek_release(self, event):
        # convert click position on scale to seconds and jump there
        try:
            width = self.scale_position.winfo_width()
            pct = max(0.0, min(100.0, (event.x / max(width, 1)) * 100.0))
        except Exception:
            pct = self.var_position.get()
        self.var_position.set(pct)
        if self.mpv_ipc and self.duration:
            target = (pct / 100.0) * self.duration
            self.mpv_ipc.seek(target, "absolute")
            self.lbl_time.config(text=f"{format_time(target)} / {format_time(self.duration)}")
        self._seeking = False

    def _on_scale_position_motion(self, event):
        # show thumbnail according to position
        scale_width = self.scale_position.winfo_width()

        # mouse position relative to scale
        x = event.x

        # limit to width of scale
        x = max(0, min(x, scale_width))

        # relative number representing the position
        fraction = x / scale_width
        
        num_thumbs = len(self.preview_photos)
        idx_thumb = int(num_thumbs * fraction)

        #print(f"PREView fraction is {fraction} index of photo is {idx_thumb}") if self.debug else True

        photo = self.preview_photos[idx_thumb]    
        if photo is not None:
            x = event.x_root + 10
            y = event.y_root - (photo.height() + 40)
            self.tooltip.show(x, y, photo)
        else:
            self.tooltip.hide()

    
    def _on_scale_position_leave(self, event):
        self.tooltip.hide()

    def on_volume_change(self, value):
        if self.mpv_ipc:
            self.mpv_ipc.set_property("volume", int(float(value)))

    def on_mute_toggle(self):
        if self.mpv_ipc:
            self.mpv_ipc.set_property("mute", bool(self.var_mute.get()))

    def close_handler(self):
        self._stop_polling = True
        self._frame_key_down = False
        self._cancel_frame_hold_timer()
        if self.mpv_ipc:
            self.mpv_ipc.close()
        for proc in (getattr(self, "mpv_proc", None),):
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                except OSError:
                    pass
        # 20260915 important to avoid call after object is destroyed!
        Globals.eventManager.unbind("FileStateChanged", self.on_file_state_changed)
        Globals.eventManager.unbind("Closing", self.on_closing)
        Globals.eventManager.generate(
            "Closing",
            ClosingEvent(self.file, self) # file, self, see tools
        )
        self.root.destroy()

    def mpv_cmd(pipe, cmd):
        msg = json.dumps(cmd) + "\n"
        pipe.write(msg.encode("utf-8"))
        pipe.flush()

    def mpv_read(pipe_r):
        raw = pipe_r.readline().decode("utf-8")
        return json.loads(raw)


    def get_video_duration(self, video_path):
        """Determines the video duration via ffprobe, independent of mpv."""
        try:
            result = subprocess.run(
                [
                    self.ffprobe_path,
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    video_path,
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return float(result.stdout.strip())
        except (subprocess.TimeoutExpired, ValueError, OSError) as e:
            print("ffprobe exception:", repr(e))
            return None

    def generate_thumbnails(self, n, thumb_height):
        video_path = os.path.abspath(self.file).replace("\\", "/")

        duration = self.get_video_duration(video_path)
        if duration is None:
            duration = 60.0
            print("Warning: could not determine duration, using fallback 60s")
        else:
            print(f"Video duration: {duration:.1f}s")
        self.duration = duration

        print(f"PIPE name = {self.pipe_name_thumb}")
        mpv_thumb_proc = subprocess.Popen([
            self.mpv_path,
            "--idle=yes",
            "--pause",
            "--no-terminal",
            "--vo=null",
            f"--vf=scale=-1:{thumb_height}:flags=fast_bilinear",
            f"--input-ipc-server={self.pipe_name_thumb}",
            video_path
        ])

        for _ in range(50):
            try:
                pipe = open(self.pipe_name_thumb, "r+b", buffering=0)
                break
            except OSError:
                time.sleep(0.1)
        else:
            mpv_thumb_proc.terminate()
            raise RuntimeError("mpv IPC pipe not available")

        next_request_id = [1]
        read_buf = b""

        def read_line():
            nonlocal read_buf
            while b"\n" not in read_buf:
                chunk = pipe.read(4096)
                if not chunk:
                    raise RuntimeError("mpv pipe closed unexpectedly")
                read_buf += chunk
            line, read_buf = read_buf.split(b"\n", 1)
            return line

        def mpv_cmd_sync(cmd, timeout=3.0):
            """Sends a command and waits SYNCHRONOUSLY for the matching response.
            Ignores unsolicited event lines (e.g. property-change)."""
            rid = next_request_id[0]
            next_request_id[0] += 1
            cmd = dict(cmd)
            cmd["request_id"] = rid
            pipe.write((json.dumps(cmd) + "\n").encode("utf-8"))

            start = time.perf_counter()
            while time.perf_counter() - start < timeout:
                line = read_line()
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                if msg.get("request_id") == rid:
                    return msg
                # otherwise: unsolicited event, ignore and keep reading
            return None

        time.sleep(0.3)
        step = duration / (n - 1)
        photos = []

        for i in range(n):
            t = i * step
            if i == 0:
                t = min(0.1, duration * 0.01)  # small offset to force a real seek
            filenum = i+1
            filename = os.path.join(self.temp_dir, f"thumb_{filenum:02d}.png")

            mpv_cmd_sync({"command": ["seek", t, "absolute"]})
            mpv_cmd_sync({"command": ["screenshot-to-file", filename, "video"]})

            for _ in range(100):
                if os.path.exists(filename):
                    break
                time.sleep(0.005)

            if os.path.exists(filename):
                for _ in range(50):
                    try:
                        with Image.open(filename) as img:
                            img.load()
                            photo = ImageTk.PhotoImage(img, master = self.canvas_gallery)
                            photos.append(photo)
                            #print(f"Photo from {filename} generated") if self.debug else True
                        break
                    except OSError:
                        time.sleep(0.01)
                os.remove(filename)
            else:
                print(f"Warning: {filename} was not created.")

        mpv_thumb_proc.terminate()
        pipe.close()
        return photos

    # ------------------------------------------------------------------
    # Metadata treeview content (same logic as MyFSImage)
    # ------------------------------------------------------------------
    def _populate_metadata_tree(self, metadata=None):
        """
        Fills the treeview with metadata.
        metadata=None -> thumbnail.metadata (selection).
        metadata=dict -> use this structure (e.g. all EXIF data).
        Category is only written when it differs from the previous row.
        """
        tree = self.tv
        for item in tree.get_children(""):
            tree.delete(item)

        if metadata is None:
            metadata = self.thumbnail.metadata

        if not metadata:
            tree.insert("", "end", text="", values=("", NO_METADATA_TEXT))
            return

        prev_cat = None
        for category, entries in metadata.items():
            if not entries:
                continue
            cat_text = "" if category == prev_cat else str(category)
            prev_cat = category
            first_in_cat = True
            for key, value in entries.items():
                tree.insert("", "end",
                            text=cat_text if first_in_cat else "",
                            values=(str(key), str(value)))
                first_in_cat = False

    def on_button_all_meta(self):
        """Toggles between 'selection only' and 'all metadata'."""
        if not self.show_all_meta:
            all_meta = self._read_all_metadata()
            self._populate_metadata_tree(all_meta)
            self.btn_all_meta.config(text=BTN_SEL_META)
            self.show_all_meta = True
        else:
            self._populate_metadata_tree()   # default = thumbnail.metadata
            self.btn_all_meta.config(text=BTN_ALL_META)
            self.show_all_meta = False

    def _read_all_metadata(self):
        """
        Reads ALL metadata for the video file via ffprobe and returns it
        in the same shape as thumbnail.metadata (dict of category -> {key: value}).
        """
        result = {}

        try:
            proc = subprocess.run(
                [
                    self.ffprobe_path,
                    "-v", "error",
                    "-show_format",
                    "-show_streams",
                    "-print_format", "json",
                    self.file,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            data = json.loads(proc.stdout or "{}")
        except Exception as e:
            print(f"ffprobe error while reading all metadata: {e}") if self.debug else True
            return result

        def _fmt(v):
            if isinstance(v, dict):
                # ffprobe nests some values, e.g. tags as a sub-dict
                return ", ".join(f"{k}={v[k]}" for k in v)
            if isinstance(v, (list, tuple)):
                return ", ".join(str(x) for x in v)
            return str(v)

        # ---- Format section ----
        fmt = data.get("format", {}) or {}
        if fmt:
            result["Format"] = {k: _fmt(v) for k, v in fmt.items()}

        # ---- One category per stream ----
        for idx, stream in enumerate(data.get("streams", []) or []):
            codec_type = stream.get("codec_type", "stream")
            category = f"{codec_type.capitalize()} {idx}"   # e.g. "Video 0", "Audio 0"
            result[category] = {k: _fmt(v) for k, v in stream.items()}

        return result

    # the include / exclude and close logic
    # 20260915 for better maintenance we convert the whole mechanism from callbacks to events
    def on_button_state(self): # react to own button; thumbnail can be from main or duplicates
        # We just determine the new state; setting of the new state happens in the
        # event handler, so we avoid finding out whether it has already been done.
        # Button -> this method -> fire event
        if self.thumbnail.getState() == INCLUDE: 
            new_state = EXCLUDE
        else: 
            new_state = INCLUDE
        Globals.eventManager.generate(
            "FileStateChanged",
            FileStateEvent(self.file, new_state)
        )
        
    def on_closing(self, event): # if parent closes, close own window
        print(f"Caller closing: {event.obj} {self.caller}") if self.debug else True
        if event.obj is self.caller:
            self.close_handler()
            
        
    # the event handler for our file_state_changed event
    def on_file_state_changed(self, event):
        if self.file == event.filename: # otherwise we are not meant
            print(f"FSIMAGE received state changed event, file: {self.file} event-file: {event.filename} state: {self.thumbnail.getState()} new state: {event.state}") if self.debug else True
            if event.state == INCLUDE:
                self.btn_inex.config(text = self.str_exclude)
                self.lbl_inex.config(text = self.str_included)
            else: # toggle to not exclude, delete item
                self.btn_inex.config(text = self.str_include)
                self.lbl_inex.config(text = self.str_excluded)
            self.thumbnail.setState(event.state)
            # historize is now done in Dateimeister_support because it listens to the same event
    # 20260915