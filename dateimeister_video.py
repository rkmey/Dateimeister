import tkinter
import cv2
import PIL.Image, PIL.ImageTk
import time
#import kivy
#from kivy.weakmethod import WeakMethod
#import numpy as np
from ffpyplayer.player import MediaPlayer
class VideoPlayer:
    def __init__(self, window, video_source, canvas, canvas_width, canvas_height, start):
        self.window = window
        self.video_source = video_source        # open video source (by default this will try to open the computer webcam)
        self.canvas = canvas
        self.canvas_height = canvas_height
        self.canvas_width  = canvas_width
        self.start = start
        self.vid = MyVideoCapture(self.video_source)
        # After it is called once, the update method will be automatically called every delay milliseconds
        self.delay = 20
        self.liney = 0.95
        self.do_update = True
        self.frames_total = self.vid.getFrameCount()
        self.frames_till_now = 0
        
        ff_opts={'an':False, 'sync':'video','thread_lib':'SDL','infbuf':True, 'autoexit':True}
        #self.callback_ref = WeakMethod(self.audio_callback)
        self.callback_ref = self.audio_callback
        self.audio_player = MediaPlayer(video_source, callback = self.callback_ref, ff_opts = ff_opts)
    def audio_callback(self, a, b):
        print("AUDIO CALLBACK called with parms {:s} - {:s}".format(str(a), str(b)))
    
    def get_pimg(self): # get 1 Photoimage
        # Get a frame from the video source
        ret, new_w, new_h, frame = self.vid.get_frame(self.canvas_width, self.canvas_height)
        if ret:
            self.image_width  = new_w
            self.image_height = new_h
            self.photo = PIL.ImageTk.PhotoImage(image = PIL.Image.fromarray(frame))
            self.x1 = self.start
            self.y1 = self.image_height * self.liney
            self.x2 = self.start + self.image_width
            self.y2 = self.y1
            self.line_total    = self.canvas.create_line(self.x1, self.y1, self.x2, self.y2, width = 5, fill = 'white', tags = "line")
            self.line_progress = self.canvas.create_line(self.x1, self.y1, self.x1, self.y2, width = 3, fill = 'black', tags = "line")
            return new_w, new_h, self.photo # returns photoimage
    def update(self): # Play video
        # Get a frame from the video source
        ret, new_w, new_h, frame = self.vid.get_frame(self.canvas_width, self.canvas_height)
        if ret:
            self.photo = PIL.ImageTk.PhotoImage(image = PIL.Image.fromarray(frame))
            self.canvas.itemconfig(self.canvas_id, image = self.photo)
            x2 = self.x1 + int(self.image_width * (self.frames_till_now / self.frames_total))
            #print("x1=" + self.x1 + " x2=" + x2)
            self.canvas.coords(self.line_progress, self.x1, self.y1, x2, self.y2)
            self.frames_till_now += 1
            #self.canvas.tag_lower("images")
            self.canvas.update()
            #time.sleep(.08) #very bad lot of exceptions
            if self.do_update:
                #self.update()
                self.window.after(self.delay, self.update)
        else:
            print("Video " + self.video_source + " has finished")
            self.audio_player.seek(0)
            self.audio_player.set_pause(True)
    def restart(self): # restart from begin
        self.do_update = True
        #self.vid = MyVideoCapture(self.video_source)
        self.vid.setFrame(0)
        self.frames_till_now = 0
        self.audio_player.seek(0)
        self.audio_player.set_pause(False)
        self.update()
    def pstart(self):
        self.do_update = True
        self.audio_player.set_pause(False)
        self.update()
        #audio
        audio_frame, val = self.audio_player.get_frame()
        if val != 'eof' and audio_frame is not None:
            img, t = audio_frame
    def pstop(self):
        self.do_update = False
        self.audio_player.set_pause(True)
    def getRun(self):
        return self.do_update
    def getFPS(self):
        self.fps = self.vid.getFPS()
        return self.fps
    def getFrameCount(self):
        self.fc = self.vid.getFrameCount()
        return self.fc
    def getDelay(self):
        delay = self.delay
        return delay
    def setDelay(self, delay):
        self.delay = delay
    def setId(self, id):
        self.canvas_id = id
    def __del__(self):
        print("*** Deleting VideoPlayer-Objekt. " + self.video_source)
        self.audio_player.close_player()


class MyVideoCapture:
    def __init__(self, video_source):
        # Open the video source
        self.video_source = video_source
        self.vid = cv2.VideoCapture(video_source)
        if not self.vid.isOpened():
            raise ValueError("Unable to open video source", video_source)
        # Get video source width and height
        self.width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT)
    def get_frame(self, canvas_width, canvas_height):
        if self.vid.isOpened():
            ret, frame = self.vid.read()
            if ret:
                # Return a boolean success flag and the current frame converted to BGR
                height, width, layers = frame.shape
                faktor = min(canvas_height / height, canvas_width / width)
                colored = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                new_h = int(height * faktor)
                new_w = int(width * faktor)
                resized = cv2.resize(colored, (new_w, new_h))
                return (ret, new_w, new_h, resized)
            else:
                return (ret, 0, 0, None)
        else:
            return (ret, 0, 0, None)
    def getFPS(self):
        return self.vid.get(cv2.CAP_PROP_FPS)
    def getFrameCount(self):
        return self.vid.get(cv2.CAP_PROP_FRAME_COUNT)
    def setFrame(self, index):
        self.vid.set(cv2.CAP_PROP_POS_FRAMES, index)
    # Release the video source when the object is destroyed
    def __del__(self):
        if self.vid.isOpened():
            self.vid.release()
        print("*** Deleting MyVideoCapture-Objekt. " + self.video_source)
# Create a window and pass it to the Application object
#App(tkinter.Tk(), "Tkinter and OpenCV", "C:\Fotos\Dateimeister\Burda.mp4")
#App(tkinter.Tk(), "Tkinter and OpenCV", "_MOV.mov")



