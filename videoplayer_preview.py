# videoplayer_preview.py

import tkinter as tk
import PIL.Image, PIL.ImageTk
from ffpyplayer.player import MediaPlayer
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
                 max_decode_frames=300, debug = False):
                     
        self.debug = debug
        self.preview_player = MediaPlayer(
            video_source,
            ff_opts={'paused': True}
        )

        # wait until metadata is available (file really opened)
        for _ in range(50):
            meta = self.preview_player.get_metadata()
            if meta and meta.get("duration"):
                break

        self.tooltip = PreviewTooltip(master)
        self.thumb_width = thumb_width
        self.thumb_height = thumb_height
        self.max_decode_frames = max_decode_frames

    def show_preview(self, target_time, event):
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
