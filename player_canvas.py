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

mpv_path = r"C:\mpv\mpv.exe"
ffprobe_path = r"C:\Users\rkmey\AppData\Local\Programs\Python\Python312\share\ffpyplayer\ffmpeg\bin\ffprobe.exe"
    
    
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

        self.frame_video.grid(row=0, column=0, sticky="nsew")
        self.frame_preview.grid(row=1, column=0, sticky="nsew")

        self.root.grid_rowconfigure(0, weight=9)
        self.root.grid_rowconfigure(1, weight=1)
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
        self.mpv_proc = subprocess.Popen([
            mpv_path,
            f"--wid={wid}",
            "--no-border",
            "--keep-open=yes",
            "--loop-file=no",
            video_path
        ])
            

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

        pipe_name = r"\\.\pipe\mpvthumb"
        thumb_height = self.canvas_preview.winfo_height()
        mpv_thumb_proc = subprocess.Popen([
            mpv_path,
            "--idle=yes",
            "--pause",
            "--no-terminal",
            "--vo=null",
            f"--vf=scale=-1:{thumb_height}:flags=fast_bilinear",
            f"--input-ipc-server={pipe_name}",
            video_path
        ])

        for _ in range(50):
            try:
                pipe = open(pipe_name, "r+b", buffering=0)
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
 