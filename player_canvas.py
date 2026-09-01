import sys
import os
import argparse
import time
import tkinter as tk
from Dateimeister_FSVideo import MyFSVideo

if __name__ == "__main__":
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-f", "--file",    help="Video File")
    argParser.add_argument("-d", "--debug",   help="Debug Mode")
    argParser.add_argument("-t", "--tempdir", help="dir for storing temp. files")
    argParser.add_argument("-n", "--num_thumbnails", help="number of thumbnails for preview")
    args = argParser.parse_args()
    print("args=%s" % args)
    print("args.debug=%s" % args.debug)
    debug = 'N'
    file = None
    temp_dir = None
    temp_dir = None
    num_thumbnails = None
    if args.file:
        file = args.file
    if args.tempdir:
        temp_dir = args.tempdir
    if args.debug:
        debug = args.debug.upper()
    if args.num_thumbnails:
        num_thumbnails = int(args.num_thumbnails)

    if not file:
        print("File -f or --file must be given")
        sys.exit(1)
    if not temp_dir:
        print("Temp_dir -t or --tempdir must be given")
        sys.exit(1)
    if not num_thumbnails:
        print("num_thumbnails -n or --num_thumbnails must be given")
        sys.exit(1)

    # check paths
    mpv_path = r"C:\mpv\mpv.exe"
    ffprobe_path = r"C:\Users\rkmey\AppData\Local\Programs\Python\Python312\share\ffpyplayer\ffmpeg\bin\ffprobe.exe"
    if not os.path.exists(temp_dir):
        print(f"TEMP_DIR {self.temp_dir} does not exist")
        exit(1)
    if not os.path.exists(ffprobe_path):
        print(f"FFPROBE_DIR {ffprobe_path} does not exist")
        exit(1)
    if not os.path.exists(mpv_path):
        print(f"MPV_DIR {mpv_path} does not exist")
        exit(1)

    if debug in ('y', 'Y', 'j', 'J'):
        b_d = True
    else:
        b_d = False
    print (f"debug is {b_d}")
    root = tk.Tk()
    app = MyFSVideo(
        root = root, 
        file = file, 
        debug = b_d, 
        temp_dir = temp_dir, 
        num_thumbnails = num_thumbnails, 
        mpv_path = mpv_path,
        ffprobe_path = ffprobe_path
    )  # when run as main we have no list of image files and no result list, no callback
    root.mainloop()
 