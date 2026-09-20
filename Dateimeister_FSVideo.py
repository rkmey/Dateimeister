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
from print_preview import PrintPreview
import Tooltip as TT

    
def format_time(seconds):
    """Formatiert Sekunden als mm:ss, bzw. h:mm:ss falls >= 1 Stunde."""
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
    """Kleine Hilfsklasse zum Steuern einer mpv-Instanz über ihre
    --input-ipc-server Named Pipe (Windows). Threadsicher für einfache
    Aufrufe (ein Lock schützt Schreiben+Lesen einer Anfrage/Antwort)."""

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
        raise RuntimeError(f"mpv IPC pipe {self.pipe_name} nicht erreichbar: {last_err}")

    def _read_line(self):
        while b"\n" not in self._read_buf:
            chunk = self.pipe.read(4096)
            if not chunk:
                raise RuntimeError("mpv pipe wurde unerwartet geschlossen")
            self._read_buf += chunk
        line, self._read_buf = self._read_buf.split(b"\n", 1)
        return line

    def command(self, cmd_list, timeout=3.0):
        """Sendet ein Kommando synchron und wartet auf die Antwort mit
        passender request_id (unaufgeforderte Event-Zeilen werden ignoriert)."""
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
                # sonst: unaufgefordertes Event, ignorieren und weiterlesen
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

    # class-level (shared across all MyFSVideo instances/windows), so that
    # frames printed from several videos opened one after another end up in
    # the same preview, as long as the user hasn't closed it in between
    _shared_print_preview = None

    def __init__(self, 
        file = None, 
        root = None,
        thumbnail = None, 
        dict_caller = None,
        caller = None,
        str_title_prefix = None,
        str_include = None,
        str_exclude = None,
        str_included = None,
        str_excluded = None,
        temp_dir = None,
        num_thumbnails = None, 
        mpv_path = None, 
        ffprobe_path = None,
        print_preview = None,
        debug = None
    ): 
        self.player = None
        self.file = file
        self.debug = debug
        self.mpv_path = mpv_path
        self.ffprobe_path = ffprobe_path
        self.temp_dir = temp_dir
        self.dict_caller = dict_caller
        self.thumbnail = thumbnail
        self.print_preview_ext = print_preview  # von aussen mitgegeben, falls vorhanden
        self.is_paused = False                  # mpv startet standardmässig abspielend
        if root is None:
            self.root = tk.Toplevel()
        else:
            self.root = root
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

        self.root.update()
        
        self.is_fullscreen = False
        self._last_mouse_pos = None
        self._hide_timer_id = None
        self._mouse_watch_id = None
        
        # Frames and canvas
        # PanedWindow ersetzt die 3 root-Grid-Zeilen
        self.paned = ttk.PanedWindow(self.root, orient="vertical")
        self.paned.grid(row=0, column=0, sticky="nsew")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Container für den oberen Bereich (video + controls, 9:1 fix)
        self.top_container = tk.Frame(self.paned)
        self.top_container.grid_rowconfigure(0, weight=9)
        self.top_container.grid_rowconfigure(1, weight=0)
        self.top_container.grid_columnconfigure(0, weight=1)

        # Deine Frames -- ab hier unverändert nutzbar
        self.frame_video    = tk.Frame(self.top_container, bg="black")
        self.frame_controls = tk.Frame(self.top_container, bg="gray20")
        self.frame_info     = tk.Frame(self.paned, bg="gray")

        self.frame_video.grid(row=0, column=0, sticky="nsew")
        self.frame_controls.grid(row=1, column=0, sticky="ew")

        # Panes hinzufügen
        self.paned.add(self.top_container, weight=9)
        self.paned.add(self.frame_info, weight=1)
        
        
        self.canvas_gallery = tk.Canvas(self.frame_video, bg="black")

        # WICHTIG: Canvas darf keine eigene Höhe verlangen
        self.canvas_gallery.configure(height=1)

        self.canvas_gallery.pack(fill="both", expand=True)
        self.root.update_idletasks()
        print("NACH LAYOUT:")
        print("root       :", self.root.winfo_width(), self.root.winfo_height())
        print("frame video:", self.frame_video.winfo_width(), self.frame_video.winfo_height())
        print("frame prev :", self.frame_info.winfo_width(), self.frame_info.winfo_height())
        print("canvas vid :", self.canvas_gallery.winfo_width(), self.canvas_gallery.winfo_height())

        self.pipe_name_thumb = rf"\\.\pipe\mpvthumb_{uuid.uuid4().hex}" # we need a unique name
        self.num_t = num_thumbnails
        
        # create the small window for previewing frames on the psition scale
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
        self.build_controls()

        threading.Thread(target=self._connect_main_ipc, daemon=True).start()

        # Leertaste pausiert/setzt fort, unabhängig davon, welches Kind-Widget
        # gerade den Fokus hat (siehe takefocus=0 an den Control-Buttons weiter
        # unten, sonst würde ein zuvor angeklickter Button die Leertaste selbst
        # abfangen statt sie hierher durchzureichen)
        self.root.bind("<space>", self._on_space_key)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------------------------------------------
    # Steuerung des Hauptplayers (mpv_proc) über IPC
    # ------------------------------------------------------------------

    def _connect_main_ipc(self):
        try:
            self.mpv_ipc = MpvIPC(self.pipe_name_main)
        except RuntimeError as e:
            print(f"Konnte nicht mit Haupt-mpv verbinden: {e}")
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
                        break  # Fenster bereits zerstört
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
        btn_frame_back = tk.Button(f, text="|◀", width=3, command=self.frame_step_backward, takefocus=0)
        TT.ToolTip(btn_frame_back, 'frame(s) back')
        self.btn_playpause = tk.Button(f, text="⏯", width=3, command=self.toggle_playpause, takefocus=0)
        TT.ToolTip(self.btn_playpause, 'play / pause')
        btn_frame_fwd  = tk.Button(f, text="▶|", width=3, command=self.frame_step_forward, takefocus=0)
        TT.ToolTip(btn_frame_fwd, 'frame(s) forward')
        btn_fwd     = tk.Button(f, text="10s⏩", command=lambda: self.seek_relative(10), takefocus=0)
        TT.ToolTip(btn_fwd, '10 sec. forward')
        self.btn_print = tk.Button(f, text="🖶 Print", command=self.print_frame, takefocus=0, state=tk.DISABLED)
        TT.ToolTip(self.btn_print, 'send frame to print preview')

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
        chk_mute = tk.Checkbutton(f, text="Stumm", variable=self.var_mute,
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
        
        # scrolled treeview, button inclue/exclude nd label in frame info
        f = self.frame_info
        self.tv = tools.ScrolledTreeView(f)
        self.tv.configure(columns="Col1, Col2, Col3")
        f.grid_columnconfigure(0, weight=8)
 
        self.btn_inex = tk.Button(f, text="inex", width=15, command=self.inex)
        TT.ToolTip(self.btn_inex, 'include / exclude video')
        self.btn_inex.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        f.grid_columnconfigure(1, weight=1)

        lbl_inex = tk.Label(f, text="inex", bg="gray20", fg="white")
        lbl_inex.grid(row=0, column=2, padx=2, pady=2)
        f.grid_columnconfigure(2, weight=1)

    # all the functions for fullscreen and back to window including small controll panel in full screen modus
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

        # Timer/Polling stoppen
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
    # End: all the functions for fullscreen and back to window including small controll panel in full screen modus


    def toggle_playpause(self):
        if self.mpv_ipc:
            self.mpv_ipc.toggle_pause()
            self._sync_paused_state_now()

    def _on_space_key(self, event=None):
        self.toggle_playpause()
        return "break"

    def frame_step_forward(self):
        if self.mpv_ipc:
            self.mpv_ipc.command(["frame-step"])  # pausiert automatisch, falls noch am Abspielen
            self._sync_paused_state_now()

    def frame_step_backward(self):
        if self.mpv_ipc:
            self.mpv_ipc.command(["frame-back-step"])  # pausiert automatisch, falls noch am Abspielen
            self._sync_paused_state_now()

    def _sync_paused_state_now(self):
        """Fragt den Pause-Status sofort synchron ab, statt auf den naechsten
        Poll-Zyklus (bis zu 0.5s) zu warten - fuer direktes Feedback nach
        einer Nutzeraktion (Play/Pause-Taste, Frame-Step)."""
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
            return  # Button sollte ohnehin disabled sein, doppelt haelt besser

        filename = os.path.join(self.temp_dir, f"print_frame_{uuid.uuid4().hex}.png")
        self.mpv_ipc.command(["screenshot-to-file", filename, "video"])

        for _ in range(100):
            if os.path.exists(filename):
                break
            time.sleep(0.01)

        if not os.path.exists(filename):
            tools.info_box("Konnte den aktuellen Frame nicht erfassen.", "fehler")
            return

        preview = self._get_print_preview()
        preview.add_photo(filename)

    def _get_print_preview(self):
        if self.print_preview_ext is not None:
            if self._is_preview_window_alive(self.print_preview_ext):
                return self.print_preview_ext
            # der Aufrufer (bzw. dessen Anwender) hat dieses Fenster
            # geschlossen - ab jetzt verwalten wir unsere eigene Instanz,
            # unabhaengig davon, wer urspruenglich verantwortlich war
            self.print_preview_ext = None

        if MyFSVideo._shared_print_preview is None or not self._is_preview_window_alive(MyFSVideo._shared_print_preview):
            MyFSVideo._shared_print_preview = PrintPreview(
                self.root,
                close_callback=self._on_shared_print_preview_closed,
            )
        return MyFSVideo._shared_print_preview

    @staticmethod
    def _is_preview_window_alive(preview):
        try:
            return bool(preview.window.winfo_exists())
        except tk.TclError:
            return False

    def _on_shared_print_preview_closed(self):
        # der Anwender hat das (von irgendeinem Video-Fenster) selbst
        # erzeugte Print-Preview-Fenster geschlossen - beim naechsten
        # Print-Klick, egal von welchem offenen Video-Fenster, soll ein
        # neues gemeinsames entstehen
        MyFSVideo._shared_print_preview = None

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
        # Klick-Position auf der Scale in Sekunden umrechnen und anspringen
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

    def inex(self):
        # implementation what happens if button include / exlude pressed
        pass
        
    def on_close(self):
        self._stop_polling = True
        if self.mpv_ipc:
            self.mpv_ipc.close()
        for proc in (getattr(self, "mpv_proc", None),):
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                except OSError:
                    pass
        self.root.destroy()

        if self.dict_caller:
            # now unregister at thumbnail and remove entry from dict
            t = self.dict_caller[self.file]
            self.dict_caller.pop(self.file)
            del t
    
    def close_handler_external(self): # called from external. Do the same things as close_handler, except remove from dict_file_image
        # can be called from main window or Duplicates-Window which use different dicts
        if self.dict_caller:
            t = self.dict_caller[self.file]
            self.root.destroy()
            del t

    def mpv_cmd(pipe, cmd):
        msg = json.dumps(cmd) + "\n"
        pipe.write(msg.encode("utf-8"))
        pipe.flush()

    def mpv_read(pipe_r):
        raw = pipe_r.readline().decode("utf-8")
        return json.loads(raw)


    def get_video_duration(self, video_path):
        """Ermittelt die Videodauer über ffprobe, unabhängig von mpv."""
        try:
            result = subprocess.run(
                [
                    self.ffprobe_path,
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",  # <<< "wrappers", nicht "wrapper"
                    video_path,
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return float(result.stdout.strip())
        except (subprocess.TimeoutExpired, ValueError, OSError) as e:
            print("ffprobe Exception:", repr(e))
            return None

    def generate_thumbnails(self, n, thumb_height):
        video_path = os.path.abspath(self.file).replace("\\", "/")

        duration = self.get_video_duration(video_path)
        if duration is None:
            duration = 60.0
            print("Warnung: Konnte Dauer nicht ermitteln, verwende Fallback 60s")
        else:
            print(f"Video-Dauer: {duration:.1f}s")
        self.duration = duration

        print(f"PIPE Name = {self.pipe_name_thumb}")
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
            """Sendet ein Kommando und wartet SYNCHRON auf die passende Antwort.
            Ignoriert dabei unaufgeforderte Event-Zeilen (z.B. property-change)."""
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
                # sonst: unaufgefordertes Event, ignorieren und weiterlesen
            return None

        time.sleep(0.3)
        step = duration / (n - 1)
        photos = []

        for i in range(n):
            t = i * step
            if i == 0:
                t = min(0.1, duration * 0.01)  # kleiner Offset, erzwingt echten Seek
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
                            photo = ImageTk.PhotoImage(img)
                            photos.append(photo)
                            print(f"Photo from {filename} generated") if self.debug else True
                        break
                    except OSError:
                        time.sleep(0.01)
                os.remove(filename)
            else:
                print(f"Warnung: {filename} wurde nicht erzeugt.")

        mpv_thumb_proc.terminate()
        pipe.close()
        return photos

