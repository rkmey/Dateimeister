import tkinter
import PIL.Image, PIL.ImageTk
import time
from ffpyplayer.player import MediaPlayer
import tools

class VideoPlayer:
    def __init__(self, window, video_source, canvas, canvas_width, canvas_height):
        self.window = window
        self.video_source = video_source
        self.canvas = canvas
        self.photo = None
        self.canvas_id = None
        self.do_update = False
        self.liney = 0.95
        
        # ff_opts optimiert für NAS/SSD
        ff_opts = {'sync': 'video', 'thread_lib': 'SDL', 
                   'infbuf': True, 'autoexit': True, 'framedrop': True}
        
        self.audio_player = MediaPlayer(video_source, ff_opts=ff_opts)
        self.audio_player.set_volume(0.0) # Startet stumm
        
        # Metadaten laden
        meta = {}
        for _ in range(50):
            meta = self.audio_player.get_metadata()
            if meta and meta.get('duration'):
                break
            time.sleep(0.02)
            
        self.duration = meta.get('duration') or 0.0
        self.fps = meta.get('fps') or 25.0
        self.frames_total = int(self.duration * self.fps)
        
        # Speicher für das letzte Roh-Frame (für Resize-Operationen)
        self.last_frame_obj = None

    def _render_frame_to_photo(self, image_obj):
        """Hilfsfunktion: Wandelt ffpyplayer-Image in skaliertes PhotoImage um"""
        v_w, v_h = image_obj.get_size()
        c_w = self.canvas.winfo_width()
        c_h = self.canvas.winfo_height()
        if c_w <= 1: c_w, c_h = 800, 600 # Fallback

        # Skalierungsfaktor (Aspect Ratio erhalten)
        faktor = min(c_h / v_h, c_w / v_w)
        self.image_width = int(v_w * faktor)
        self.image_height = int(v_h * faktor)

        # Byte-Daten extrahieren und zusammenfügen (TypeError Fix)
        img_data = image_obj.to_bytearray()
        if isinstance(img_data, list):
            img_data = bytes().join(img_data)
        
        # PIL Konvertierung & Resize
        pil_img = PIL.Image.frombytes("RGB", (v_w, v_h), img_data)
        pil_img = pil_img.resize((self.image_width, self.image_height), PIL.Image.Resampling.LANCZOS)
        self.photo = PIL.ImageTk.PhotoImage(image=pil_img)
        return self.photo

    def get_photo(self):
        """Wird bei Initialisierung"""
        # Falls wir schon ein Bild im Cache haben, nimm das (spart NAS/SSD Last)
        if self.last_frame_obj is None:
            frame, val = self.audio_player.get_frame()
            retry = 0
            while frame is None and retry < 50:
                time.sleep(0.01)
                frame, val = self.audio_player.get_frame()
                retry += 1
            if frame:
                self.last_frame_obj, _ = frame
                self.audio_player.set_pause(True)

        if self.last_frame_obj:
            self.photo = self._render_frame_to_photo(self.last_frame_obj)
            return self.image_width, self.image_height, self.photo
        else:
            tools.info_box("frame object not found", "fehler")

    def resize(self):
        #tools.info_box("searching frame object...", "info")
        # 1. Das Bild basierend auf der NEUEN Canvas-Größe neu berechnen
        if self.last_frame_obj:
            # _render_frame_to_photo nutzt intern self.canvas.winfo_width/height()
            self.photo = self._render_frame_to_photo(self.last_frame_obj)
            
            # 2. Das vorhandene Bild-Objekt auf dem Canvas aktualisieren
            if self.canvas_id:
                self.canvas.itemconfig(self.canvas_id, image=self.photo)
                print("... resize the video")
            else:
                tools.info_box("canvas_id not found")
                exit()
        else:
            tools.info_box("frame object not found", "fehler")
                
        bbox = self.canvas.bbox(self.canvas_id)
        if bbox:
            vx1, vy1, vx2, vy2 = bbox
            
            # Neue Koordinaten berechnen
            self.x1 = vx1
            self.y1 = vy1 + (self.image_height * self.liney)
            self.x2 = vx1 + self.image_width
            self.y2 = self.y1
            
            # Fortschritt ermitteln
            pts = self.audio_player.get_pts()
            progress = pts / self.duration if self.duration > 0 else 0
            current_x2 = self.x1 + int(self.image_width * progress)

            # 4. Linien aktualisieren oder neu erstellen
            # Wir nutzen einen eindeutigen Tag pro Video-Instanz
            my_tag = f"prog_{id(self)}"
            
            if not self.canvas.find_withtag(my_tag):
                self.line_total = self.canvas.create_line(self.x1, self.y1, self.x2, self.y2, 
                                                          width=5, fill='white', tags=(my_tag, "line"))
                self.line_progress = self.canvas.create_line(self.x1, self.y1, current_x2, self.y2, 
                                                             width=3, fill='black', tags=(my_tag, "line"))
            else:
                self.canvas.coords(self.line_total, self.x1, self.y1, self.x2, self.y2)
                self.canvas.coords(self.line_progress, self.x1, self.y1, current_x2, self.y2)

            # 5. Z-Index: Linien nach oben holen
            self.canvas.tag_raise("line")
        else:
            tools.info_box("unable to find bbox", "fehler")

    def update(self):
        if not self.do_update:
            return

        frame, val = self.audio_player.get_frame()

        # Check: Fast am Ende? (Verhindert Audio-Loop)
        pts = self.audio_player.get_pts()
        if val == 'eof' or (self.duration > 0 and pts > self.duration - 0.2):
            self.stop_and_rewind()
            return

        if frame:
            image_obj, pts = frame
            self.last_frame_obj = image_obj # Cache aktualisieren
            
            # Bild anzeigen
            self.photo = self._render_frame_to_photo(image_obj)
            self.canvas.itemconfig(self.canvas_id, image=self.photo)
            
            # Progressbar (basierend auf pts)
            progress = pts / self.duration if self.duration > 0 else 0
            x2 = self.x1 + int(self.image_width * progress)
            self.canvas.coords(self.line_progress, self.x1, self.y1, x2, self.y2)

            # Sync-Delay
            delay = max(int(val * 1000), 1)
            self.window.after(delay, self.update)
        else:
            self.window.after(5, self.update)

    def stop_and_rewind(self):
        self.do_update = False
        self.audio_player.set_pause(True)
        self.audio_player.set_volume(0.0)
        self.audio_player.seek(0, relative=False)
        # Progressbar optisch zurück auf Start
        self.canvas.coords(self.line_progress, self.x1, self.y1, self.x1, self.y2)

    def restart(self):
        self.do_update = True
        self.audio_player.set_volume(1.0)
        self.audio_player.seek(0, relative=False)
        self.audio_player.set_pause(False)
        self.update()

    def pstart(self):
        self.do_update = True
        self.audio_player.set_volume(1.0)
        self.audio_player.set_pause(False)
        self.update()

    def pstop(self):
        self.do_update = False
        self.audio_player.set_pause(True)
        self.audio_player.set_volume(0.0)

    # "alte" Funktionen
    def setId(self, id):
        self.canvas_id = id

    def getRun(self):
        return self.do_update
    def getFPS(self):
        return self.fps
    def getFrameCount(self):
        self.fc = self.frames_total
        return self.fc
    def getDelay(self):
        delay = self.delay
        return delay
    def setDelay(self, delay):
        self.delay = delay
    def setId(self, id):
        self.canvas_id = id


    def __del__(self):
        if self.audio_player:
            self.audio_player.close_player()
