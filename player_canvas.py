import sys
import os
import argparse
import time
import inspect
from PIL import Image, ImageTk
import socket
import json

import tkinter as tk
import gc
#gc.disable() # disable garbage collection

# windows timer base to 1ms instead of system default
import ctypes
import atexit

import subprocess
import threading
import queue
import uuid

mpv_path = r"C:\mpv\mpv.exe"
ffprobe_path = r"C:\Users\rkmey\AppData\Local\Programs\Python\Python312\share\ffpyplayer\ffmpeg\bin\ffprobe.exe"
    
    
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


class MyFSImage:

    # The class "constructor" - It's actually an initializer 
    def __init__(self, root = None, file = None, temp_dir = None, debug = False, anz_thumbnails = None): 
        self.player = None
        self.file = file
        self.debug = debug
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
        
        # Frames und canvas
        self.frame_video  = tk.Frame(self.root, bg="black")
        self.frame_preview = tk.Frame(self.root, bg="gray")
        self.frame_controls = tk.Frame(self.root, bg="gray20")

        self.frame_video.grid(row=0, column=0, sticky="nsew")
        self.frame_preview.grid(row=1, column=0, sticky="nsew")
        self.frame_controls.grid(row=2, column=0, sticky="ew")

        self.root.grid_rowconfigure(0, weight=9)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)
        self.root.grid_columnconfigure(0, weight=1)

        self.canvas_gallery = tk.Canvas(self.frame_video, bg="black")
        self.canvas_preview = tk.Canvas(self.frame_preview, bg="gray")

        # WICHTIG: Canvas darf keine eigene Höhe verlangen
        self.canvas_gallery.configure(height=1)
        self.canvas_preview.configure(height=1)

        self.canvas_gallery.pack(fill="both", expand=True)
        self.canvas_preview.pack(fill="both", expand=True)
        self.root.update_idletasks()
        print("NACH LAYOUT:")
        print("root       :", self.root.winfo_width(), self.root.winfo_height())
        print("frame video:", self.frame_video.winfo_width(), self.frame_video.winfo_height())
        print("frame prev :", self.frame_preview.winfo_width(), self.frame_preview.winfo_height())
        print("canvas vid :", self.canvas_gallery.winfo_width(), self.canvas_gallery.winfo_height())
        print("canvas prev:", self.canvas_preview.winfo_width(), self.canvas_preview.winfo_height())

        print(os.path.exists(ffprobe_path))
        self.temp_dir = temp_dir
        if not os.path.exists(temp_dir):
            print(f"TEMP_DIR {self.temp_dir} does not exist")
            exit(1)
        if not os.path.exists(ffprobe_path):
            print(f"FFPROBE_DIR {ffprobe_path} does not exist")
            exit(1)
        if not os.path.exists(mpv_path):
            print(f"MPV_DIR {mpv_path} does not exist")
            exit(1)

        self.pipe_name_thumb = rf"\\.\pipe\mpvthumb_{uuid.uuid4().hex}" # we need a unique name
        self.anz_t = anz_thumbnails
        
        self.preview_photos = []
        self.preview_photos = self.generate_thumbnails(self.anz_t)
        xpos = 0
        ypos = 0
        for photo in self.preview_photos:
            self.canvas_preview.create_image(xpos, ypos, image=photo, anchor="nw")
            width = photo.width()
            #print (f"Photo Breite ist {width}")
            xpos += width
        
        video_path = self.file
        wid = self.canvas_gallery.winfo_id()
        self.pipe_name_main = rf"\\.\pipe\mpvmain_{uuid.uuid4().hex}"
        self.mpv_proc = subprocess.Popen([
            mpv_path,
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
                if pos is not None and self.duration:
                    pct = max(0.0, min(100.0, (pos / self.duration) * 100.0))
                    try:
                        self.root.after(0, lambda p=pct, t=pos: self._update_position_ui(p, t))
                    except RuntimeError:
                        break  # Fenster bereits zerstört
            time.sleep(0.5)

    def _update_position_ui(self, pct, current_seconds):
        self.var_position.set(pct)
        self.lbl_time.config(text=f"{format_time(current_seconds)} / {format_time(self.duration)}")

    def build_controls(self):
        f = self.frame_controls

        btn_restart = tk.Button(f, text="⏮", width=3, command=self.restart_video)
        btn_back    = tk.Button(f, text="⏪10s", command=lambda: self.seek_relative(-10))
        self.btn_playpause = tk.Button(f, text="⏯", width=3, command=self.toggle_playpause)
        btn_fwd     = tk.Button(f, text="10s⏩", command=lambda: self.seek_relative(10))

        btn_restart.grid(row=0, column=0, padx=2, pady=2)
        btn_back.grid(row=0, column=1, padx=2, pady=2)
        self.btn_playpause.grid(row=0, column=2, padx=2, pady=2)
        btn_fwd.grid(row=0, column=3, padx=2, pady=2)

        self.var_position = tk.DoubleVar(value=0.0)
        self.lbl_time = tk.Label(f, text=f"00:00 / {format_time(self.duration)}",
                                  bg="gray20", fg="white", width=12)
        self.lbl_time.grid(row=0, column=4, padx=(8, 4), pady=2)

        self.scale_position = tk.Scale(
            f, from_=0, to=100, orient="horizontal", showvalue=False,
            resolution=0.1, variable=self.var_position, length=300,
        )
        self.scale_position.grid(row=0, column=5, padx=8, pady=2, sticky="ew")
        self.scale_position.bind("<ButtonPress-1>", self._on_seek_press)
        self.scale_position.bind("<ButtonRelease-1>", self._on_seek_release)

        f.grid_columnconfigure(5, weight=1)

        self.var_mute = tk.BooleanVar(value=False)
        chk_mute = tk.Checkbutton(f, text="Stumm", variable=self.var_mute,
                                   command=self.on_mute_toggle, bg="gray20", fg="white",
                                   selectcolor="gray30")
        chk_mute.grid(row=0, column=6, padx=4, pady=2)

        tk.Label(f, text="Vol", bg="gray20", fg="white").grid(row=0, column=7, padx=(8, 0))
        self.var_volume = tk.IntVar(value=100)
        scale_volume = tk.Scale(
            f, from_=0, to=150, orient="horizontal", showvalue=True,
            variable=self.var_volume, length=140, command=self.on_volume_change,
        )
        scale_volume.grid(row=0, column=8, padx=(0, 8), pady=2)

    def toggle_playpause(self):
        if self.mpv_ipc:
            self.mpv_ipc.toggle_pause()

    def restart_video(self):
        if self.mpv_ipc:
            self.mpv_ipc.seek(0, "absolute")
            self.mpv_ipc.set_property("pause", False)
            self.var_position.set(0.0)
            self.lbl_time.config(text=f"00:00 / {format_time(self.duration)}")

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

    def on_volume_change(self, value):
        if self.mpv_ipc:
            self.mpv_ipc.set_property("volume", int(float(value)))

    def on_mute_toggle(self):
        if self.mpv_ipc:
            self.mpv_ipc.set_property("mute", bool(self.var_mute.get()))

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
                    ffprobe_path,
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

    def generate_thumbnails(self, n):
        video_path = os.path.abspath(self.file).replace("\\", "/")

        duration = self.get_video_duration(video_path)
        if duration is None:
            duration = 60.0
            print("Warnung: Konnte Dauer nicht ermitteln, verwende Fallback 60s")
        else:
            print(f"Video-Dauer: {duration:.1f}s")
        self.duration = duration

        print(f"PIPE Name = {self.pipe_name_thumb}")
        thumb_height = self.canvas_preview.winfo_height()
        mpv_thumb_proc = subprocess.Popen([
            mpv_path,
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

if __name__ == "__main__":
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-f", "--file",    help="Video File")
    argParser.add_argument("-d", "--debug",   help="Debug Mode")
    argParser.add_argument("-t", "--tempdir", help="dir for storing temp. files")
    argParser.add_argument("-n", "--anz_thumbnails", help="number of thumbnails for preview")
    args = argParser.parse_args()
    print("args=%s" % args)
    print("args.debug=%s" % args.debug)
    debug = 'N'
    file = None
    temp_dir = None
    temp_dir = None
    anz_thumbnails = None
    if args.file:
        file = args.file
    if args.tempdir:
        temp_dir = args.tempdir
    if args.debug:
        debug = args.debug.upper()
    if args.anz_thumbnails:
        anz_thumbnails = int(args.anz_thumbnails)

    if not file:
        print("File -f or --file must be given")
        sys.exit(1)
    if not temp_dir:
        print("Temp_dir -t or --tempdir must be given")
        sys.exit(1)
    if not anz_thumbnails:
        print("anz_thumbnails -n or --anz_thumbnails must be given")
        sys.exit(1)
    root = tk.Tk()
    app = MyFSImage(root = root, file = file, debug = debug, temp_dir = temp_dir, anz_thumbnails = anz_thumbnails)  # when run as main we have no list of image files and no result list, no callback
    root.mainloop()
 