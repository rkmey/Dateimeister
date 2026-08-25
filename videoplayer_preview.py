# videoplayer_preview.py

import tkinter as tk
import PIL.Image, PIL.ImageTk
from ffpyplayer.player import MediaPlayer
import bisect
import inspect

import tools


class PreviewTooltip(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        #self.overrideredirect(True)  # no window border
        self.label = tk.Label(self, bg="black")
        self.label.pack()
        #self.withdraw()  # start hidden

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


class VideoPreviewEngine:
    def __init__(self, video_source, master,
                 thumb_width=160, thumb_height=90,
                 max_decode_frames=300, debug = False, meta_data = ""):
                     
        self.debug = debug
        self.preview_player = MediaPlayer(
            video_source
        )

        meta = meta_data
        print("PREView Meta: ", str(meta)) if self.debug else True 
        self.tooltip = PreviewTooltip(master)
        self.thumb_width = thumb_width
        self.thumb_height = thumb_height
        self.max_decode_frames = max_decode_frames
        self.fps      = meta.get('fps') or 25.0
        self.duration = meta.get('duration') or 10
        self.frames_total = int(self.duration * self.fps)

        self.preview_pts, self.preview = self.create_previews(20)
        del self.preview_player

    def create_previews(self, pcount=100, size=(160, 90)):
        """Erzeugt die Preview-Bilder und die dazugehörigen PTS."""

        preview = {}
        preview_pts = []
        positions = []

        count = min(pcount, self.frames_total) # correction if video is very short
        #print("PREView: ", str(self.duration), str(count))

        if not self.duration or self.duration <= 0 or count < 1:
            raise ValueError("{:s}.{:s}: duration: {:d} count {:d}".format(__name__, inspect.currentframe().f_code.co_name, self.duration, count))
            return preview_pts, preview

        # gleichmäßig verteilte Zielpositionen
        if count == 1:
            positions = [self.duration / 2]
        else:
            for i in range(count):
                pos = min(self.duration * i / (count - 1), self.duration -.1)
                #print ("position: ", pos)
                positions.append(pos)

        #print ("PREView positions: ", str(positions))
        for position in positions:

            #print("PREView before seek position: ", str(position))
            self.preview_player.seek(int(position), relative=False)

            while True:
                frame, val = self.preview_player.get_frame()

                if val == 'eof':
                    break

                if frame is None:
                    continue

                img, pts = frame

                # ffpyplayer Image -> PIL
                data = img.to_bytearray()[0]
                pil_image = PIL.Image.frombytes(
                    'RGB',
                    (img.get_size()[0], img.get_size()[1]),
                    bytes(data)
                )

                pil_image.thumbnail(size)

                photo = PIL.ImageTk.PhotoImage(pil_image)

                preview[pts] = photo
                preview_pts.append(pts)

                break

        # Sicherheit, falls ffpyplayer PTS nicht exakt in
        # der erwarteten Reihenfolge geliefert hat
        preview_pts.sort()

        print ("PREView ptst: ", str(preview_pts)) if self.debug else True
        return preview_pts, preview    
    

    def show_preview(self, event, scale_width):
        """Liefert das zur Mausposition passende Preview-PhotoImage."""

        if not self.preview_pts:
            return None

        # Mausposition relativ zur Scale
        x = event.x

        # auf den Bereich der Scale begrenzen
        x = max(0, min(x, scale_width))

        # Position auf der Scale -> Zeitposition
        fraction = x / scale_width

        pts = fraction * self.duration
        print("PREView search photo with pts {:f}".format(pts)) if self.debug else True

        # nächstgelegenen PTS suchen
        i = bisect.bisect_left(self.preview_pts, pts)

        if i == 0:
            nearest_pts = self.preview_pts[0]

        elif i == len(self.preview_pts):
            nearest_pts = self.preview_pts[-1]

        else:
            before = self.preview_pts[i - 1]
            after = self.preview_pts[i]

            if pts - before <= after - pts:
                nearest_pts = before
            else:
                nearest_pts = after

        photo = self.preview[nearest_pts]    
        if photo is not None:
            x = event.x_root + 10
            y = event.y_root - (self.thumb_height + 40)
            self.tooltip.show(x, y, photo)
        else:
            self.tooltip.hide()


    def deprshow_preview(self, target_time, event):
        # ffpyplayer cannot reliably decode at 0.0 → enforce minimum seek
        seek_time = max(0.5, target_time)

        # player must NOT be paused before decoding
        self.preview_player.set_pause(False)
        self.preview_player.seek(seek_time, relative=False)

        photo = None

        # robust: take the first non-None frame after seek
        for _ in range(self.max_decode_frames):
            frame, val = self.preview_player.get_frame()

            if val == 'eof':
                break

            if not frame:
                continue

            img, pts = frame
            print ("PREView player event = {:s}, pts = {:0.3f}".format(str(event), pts)) if self.debug else True

            photo = self._render_frame_to_photo(img) 
            break

        if photo is not None:
            x = event.x_root + 10
            y = event.y_root - (self.thumb_height + 40)
            self.tooltip.show(x, y, photo)
        else:
            self.tooltip.hide()

        # pause again to avoid continuous decoding
        self.preview_player.set_pause(True)

    def _render_frame_to_photo(self, image_obj):
        """Hilfsfunktion: Wandelt ffpyplayer-Image in skaliertes PhotoImage um"""
        v_w, v_h = image_obj.get_size()
        c_w = self.thumb_width
        c_h = self.thumb_height

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


    def hide(self):
        self.tooltip.hide()

    def close(self):
        try:
            self.preview_player.close_player()
        except Exception:
            pass
        self.tooltip.destroy()
