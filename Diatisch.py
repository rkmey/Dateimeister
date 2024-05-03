import os
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import Dateimeister
from datetime import datetime, timezone


from enum import Enum
class action(Enum):
    PRESS   = 1
    RELEASE = 2
class dragposition(Enum):
    BEFORE  = 1
    BEHIND  = 2

class ScrollableCanvas(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<Configure>", self.on_configure)
        self.select_ctr = 0

    def on_configure(self, event):
        self.configure(scrollregion=self.bbox("all"))
        print ("<Configure> called")

class MyImage:
    def __init__(self, filename, image, canvas, frameids):
        self.filename = filename
        self.image = image
        self.frameids = frameids
        self.canvas = canvas
        self.selected = 0
        self.unselect(canvas)
        self.was_selected = False
        
    def get_filename(self):
        return self.filename
    def get_image(self):
        return self.image
    def select(self, canvas, ctr):
        for frameid in self.frameids:
            self.canvas.itemconfigure(frameid, state = 'normal')
        self.selected = ctr
    def unselect(self, canvas):
        for frameid in self.frameids:
            self.canvas.itemconfigure(frameid, state = 'hidden')
        self.selected = 0
    def is_selected(self):
        if self.selected > 0:
            return True
        else:
            return False
    def set_frameids(self, frameids):
        self.frameids = frameids

     
class ImageApp:
    def __init__(self, root, m, n):
        self.root = root
        self.root.title("Image Canvas")
        # Fenstergröße
        screen_width  = int(root.winfo_screenwidth() * .75) # adjust as needed
        screen_height = int(root.winfo_screenheight() * .5) # adjust as needed
        print("Bildschirm ist " + str(screen_width) + " x " + str(screen_height))
        v_dim=str(screen_width)+'x'+str(screen_height)
        root.geometry(v_dim)

        self.m, self.n = m, n
        self.image_width = 1500  # Adjust as needed
        self.row_height  = 200
        self.xpos = 0
        self.ypos = 0

        self.Frame_source = tk.Frame(root)
        self.Frame_source.place(relx=.01, rely=0.05, relheight=0.85, relwidth=0.48)
        self.Frame_source.configure(relief='groove')
        self.Frame_source.configure(borderwidth="2")
        self.Frame_source.configure(relief="groove")
        self.Frame_source.configure(background="#d9d9d9")
        self.Frame_source.configure(highlightbackground="#d9d9d9")
        self.Frame_source.configure(highlightcolor="black")

        self.Frame_target = tk.Frame(root)
        self.Frame_target.place(relx=.51, rely=0.05, relheight=0.85, relwidth=0.48)
        self.Frame_target.configure(relief='groove')
        self.Frame_target.configure(borderwidth="2")
        self.Frame_target.configure(relief="groove")
        self.Frame_target.configure(background="#d9d9d9")
        self.Frame_target.configure(highlightbackground="#d9d9d9")
        self.Frame_target.configure(highlightcolor="black")

        self.Frame_source_ctl = tk.Frame(root)
        self.Frame_source_ctl.place(relx=.01, rely=0.92, relheight=0.05, relwidth=0.48)
        self.Frame_source_ctl.configure(relief='groove')
        self.Frame_source_ctl.configure(borderwidth="2")
        self.Frame_source_ctl.configure(relief="groove")
        self.Frame_source_ctl.configure(background="#d9d9d9")
        self.Frame_source_ctl.configure(highlightbackground="#d9d9d9")
        self.Frame_source_ctl.configure(highlightcolor="black")

        self.Frame_target_ctl = tk.Frame(root)
        self.Frame_target_ctl.place(relx=.51, rely=0.92, relheight=0.05, relwidth=0.48)
        self.Frame_target_ctl.configure(relief='groove')
        self.Frame_target_ctl.configure(borderwidth="2")
        self.Frame_target_ctl.configure(relief="groove")
        self.Frame_target_ctl.configure(background="#d9d9d9")
        self.Frame_target_ctl.configure(highlightbackground="#d9d9d9")
        self.Frame_target_ctl.configure(highlightcolor="black")

        # canvas source with scrollbars
        self.source_canvas = ScrollableCanvas(self.Frame_source, bg="yellow")
        self.source_canvas.place(relx=0.01, rely=0.01, relheight=.92, relwidth=.95)

        self.V_source = tk.Scrollbar(self.Frame_source, orient = tk.VERTICAL)
        self.V_source.config(command=self.source_canvas.yview)
        self.source_canvas.config(yscrollcommand=self.V_source.set)
        self.V_source.place(relx = 1, rely = 0,     relheight = 0.98, relwidth = 0.02, anchor = tk.NE)        

        self.H_source = tk.Scrollbar(self.Frame_source, orient = tk.HORIZONTAL)
        self.H_source.config(command=self.source_canvas.xview)
        self.source_canvas.config(xscrollcommand=self.H_source.set)
        self.H_source.place(relx = 0, rely = 1, relheight = 0.02, relwidth = 0.98, anchor = tk.SW)
 
        # canvas target with scrollbars
        self.target_canvas = ScrollableCanvas(self.Frame_target, bg="darkgrey")
        self.target_canvas.place(relx=0.01, rely=0.01, relheight=.92, relwidth=.95)

        self.V_target = tk.Scrollbar(self.Frame_target, orient = tk.VERTICAL)
        self.V_target.config(command=self.target_canvas.yview)
        self.target_canvas.config(yscrollcommand=self.V_target.set)  
        self.V_target.place(relx = 1, rely = 0,     relheight = 0.98, relwidth = 0.02, anchor = tk.NE)        

        self.H_target = tk.Scrollbar(self.Frame_target, orient = tk.HORIZONTAL)
        self.H_target.config(command=self.target_canvas.xview)
        self.target_canvas.config(xscrollcommand=self.H_target.set)
        self.H_target.place(relx = 0, rely = 1, relheight = 0.02, relwidth = 0.98, anchor = tk.SW)
        
        # source control buttons
        anz_button_source = 5
        buttonpos_source  = 0.0
        relwidth_source   = 1 / anz_button_source
        self.load_button = tk.Button(self.Frame_source_ctl, text="Load Images", command=self.load_images)
        self.load_button.place(relx=buttonpos_source, rely=0.01, relheight=0.98, relwidth=relwidth_source)
        buttonpos_source += relwidth_source
        self.select_all_button = tk.Button(self.Frame_source_ctl, text="Select all", command=self.select_all_source_images)
        self.select_all_button.place(relx=buttonpos_source, rely=0.01, relheight=0.98, relwidth=relwidth_source)
        buttonpos_source += relwidth_source
        self.select_all_button = tk.Button(self.Frame_source_ctl, text="Copy selected", command=self.copy_selected_source_images)
        self.select_all_button.place(relx=buttonpos_source, rely=0.01, relheight=0.98, relwidth=relwidth_source)

        # target control buttons
        anz_button_target = 5
        buttonpos_target  = 0.0
        relwidth_target   = 1 / anz_button_source
        self.delete_selected_button = tk.Button(self.Frame_target_ctl, text="Delete selected", command=self.delete_selected)
        self.delete_selected_button.place(relx=buttonpos_target, rely=0.01, relheight=0.98, relwidth=relwidth_target)

        self.list_dragged_images = []

        self.dict_source_images = {}
        self.dict_target_images = {}

        self.source_row, self.source_col = 0, 0
        self.target_row, self.target_col = 0, 0
        self.drag_started_in = ""

        #self.source_canvas.bind("<ButtonPress-1>", self.start_drag)
        #self.target_canvas.bind("<ButtonRelease-1>", self.drop)
        self.target_canvas.bind("<B1-Motion>", self.on_motion)
        self.root.bind("<ButtonPress-1>", self.start_drag)
        self.root.bind("<ButtonRelease-1>", self.drop)

        # tooltips, context-menu
        self.tooltiptext_st = ""
        self.tooltiptext_tt = ""
        self.source_canvas.bind("<Button-3>", self.show_context_menu_source) 
        self.source_canvas.bind('<Motion>', self.tooltip_imagefile_source)    
        self.target_canvas.bind("<Button-3>", self.show_context_menu_target) 
        self.target_canvas.bind('<Motion>', self.tooltip_imagefile_target)    
        #self.target_canvas.bind('<Motion>', lambda event, i = self.target_canvas, j = self.dict_target_images, k = "target": self.tooltip_imagefile(event, i, j, k))    
        self.st = Dateimeister.ToolTip(self.source_canvas, "no images available", delay=0, follow = True)
        self.tt = Dateimeister.ToolTip(self.target_canvas, "no images available", delay=0, follow = True)

        self.list_source_imagefiles = []
        self.list_source_images = []
        self.list_target_images = []
        self.event = None
        # Create the context menues
        self.context_menu_source = tk.Menu(self.source_canvas, tearoff=0)
        self.context_menu_source.add_command(label="Show"   , command=self.canvas_image_show)    
        self.context_menu_target = tk.Menu(self.target_canvas, tearoff=0)
        self.context_menu_target.add_command(label="Show"   , command=self.canvas_image_show)  
        self.timestamp = datetime.now() 
        self.image_press = None
        self.image_release = None
        
       
    def show_context_menu_source(self, event):
        # das Event müssen wir speichern, da die eigenlichen Funktionen die x und y benötigen
        self.event = event
        text = "no image available"
        # falls wir keine anzeigbare Datei haben, müssen wir show-Item disablen
        canvas_x = self.source_canvas.canvasx(event.x)
        canvas_y = self.source_canvas.canvasy(event.y)
        if (closest := self.source_canvas.find_closest(self.source_canvas.canvasx(event.x), self.source_canvas.canvasy(event.y))):
            image_id = closest[0]
            img      = self.dict_source_images[image_id]
            text     = img.get_filename()
        self.context_menu_source.entryconfig(1, label = "Show " + text)
        self.context_menu_source.post(event.x_root, event.y_root)
    
    def show_context_menu_target(self, event):
        # das Event müssen wir speichern, da die eigenlichen Funktionen die x und y benötigen
        self.event = event
        text = "no image available"
        # falls wir keine anzeigbare Datei haben, müssen wir show-Item disablen
        canvas_x = self.target_canvas.canvasx(event.x)
        canvas_y = self.target_canvas.canvasy(event.y)
        if (closest := self.target_canvas.find_closest(self.target_canvas.canvasx(event.x), self.target_canvas.canvasy(event.y))):
            image_id = closest[0]
            img      = self.dict_target_images[image_id]
            text     = img.get_filename()
        self.context_menu_target.entryconfig(1, label = "Show " + text)
        self.context_menu_target.post(event.x_root, event.y_root)

    def tooltip_imagefile_source(self, event):
        tsnow = datetime.now()
        tdiff = abs(tsnow - self.timestamp)
        if  tdiff.microseconds > 100000:
            #print("Timer has finished, microsecons is: ", tdiff.microseconds)
            self.timestamp = tsnow
        else:
            return
        # Tooltip
        text = "no image available"
        if (closest := self.source_canvas.find_closest(self.source_canvas.canvasx(event.x), self.source_canvas.canvasy(event.y))):
            image_id = closest[0]
            img      = self.dict_source_images[image_id]
            text     = img.get_filename()
            if text != self.tooltiptext_st:
                self.st.update(text)
                self.tooltiptext_st = text

    def tooltip_imagefile_target(self, event):
        tsnow = datetime.now()
        tdiff = abs(tsnow - self.timestamp)
        if  tdiff.microseconds > 100000:
            #print("Timer has finished, microsecons is: ", tdiff.microseconds)
            self.timestamp = tsnow
        else:
            return
        # Tooltip
        text = "no image available"
        if (closest := self.target_canvas.find_closest(self.target_canvas.canvasx(event.x), self.target_canvas.canvasy(event.y))):
            image_id = closest[0]
            img      = self.dict_target_images[image_id]
            text     = img.get_filename()
            if text != self.tooltiptext_tt:
                self.tt.update(text)
                self.tooltiptext_tt = text
                       
    def canvas_image_show(self):
        # placeholder for call full screen display of image
        print("Context menu show")
        #self.canvas_show(self.event)


    def load_images(self):
        self.list_source_imagefiles = []
        self.list_source_images = []
        self.dict_source_images = []
        directory = filedialog.askdirectory()
        if directory:
            image_files = [f for f in os.listdir(directory) if (f.lower().endswith(".jpg") or f.lower().endswith(".jpeg"))]
            for img_file in image_files:
                img_path = os.path.join(directory, img_file)
                self.list_source_imagefiles.append(img_path)
                # get image
                img = Image.open(img_path)
                image_width_orig, image_height_orig = img.size
                faktor = min(self.row_height / image_height_orig, self.image_width / image_width_orig)
                #print("Image " + img_path + " width = " + str(image_width_orig) + " height = " + str(image_height_orig) + " Faktor = " + str(faktor))
                display_width  = int(image_width_orig * faktor)
                display_height = int(image_height_orig * faktor)
                newsize = (display_width, display_height)
                r_img = img.resize(newsize, Image.Resampling.NEAREST)
                photo = ImageTk.PhotoImage(r_img)
                # insert into self.list_source_images
                i = MyImage(img_path, photo, self.source_canvas, (0,0,0,0)) # frameids will be updated after insert in source_canvas
                self.list_source_images.append(i)
                
            self.dict_source_images = self.display_image_objects(self.list_source_images, self.source_canvas)
            self.unselect_all(self.dict_source_images, self.source_canvas)
        self.source_canvas.configure(scrollregion=self.source_canvas.bbox("all")) # update scrollregion

    def start_drag(self, event):
        # check where mouse is 
        source_rect = self.get_root_coordinates_for_widget(self.source_canvas)
        target_rect = self.get_root_coordinates_for_widget(self.target_canvas)
        #print ("source_canvas: ", str(source_rect))
        #print ("target_canvas: ", str(target_rect))
        #print ("event: ", " x_root: ", str(event.x_root), " y_root: ", str(event.y_root), " x: ", str(event.x), " y: ", str(event.y))
        #print ("Source canvasx: ", str(self.source_canvas.canvasx(event.x)), "canvasy: ", str(self.source_canvas.canvasy(event.y)))
        self.image_press = None
        if (self.check_event_in_rect(event, source_rect)): # select Image(s)
            #print("Event in source_canvas")
            self.drag_started_in = "source"
            img_closest_id, dist_event_left, dist_event_right = self.find_closest_item(event, source_rect, self.source_canvas, self.dict_source_images)
            if img_closest_id > 0:
                self.image_press = self.dict_source_images[img_closest_id]
                print("image found in source canvas, action = PRESS: ", self.image_press.get_filename())
                self.selection(event, self.source_canvas, self.dict_source_images, action.PRESS)
            else: # do nothing
                print("no image found in source canvas, action = PRESS")
        elif (self.check_event_in_rect(event, target_rect)):
            #print("Event in target_canvas")
            self.drag_started_in = "target"
            img_closest_id, dist_event_left, dist_event_right = self.find_closest_item(event, target_rect, self.target_canvas, self.dict_target_images)
            if img_closest_id > 0:
                self.image_press = self.dict_target_images[img_closest_id]
                print("image found in target canvas, action = PRESS: ", self.image_press.get_filename())
                self.selection(event, self.target_canvas, self.dict_target_images, action.PRESS)
            else: # do nothing
                print("no image found in target canvas, action = PRESS")
        else:
            #rint("Event not in canvas")
            self.drag_started_in = ""
            True

    def on_motion(self, event):
        if self.drag_started_in == "target":
            #print("Drag Motion in Target")
            True
    
    def selection(self, event, canvas, dict_images, action): #select / unselect image(s) from mouse click
        # returns True if no further processing required else False (rebuild target-canvas
        canvas_target_rebuild_required = False
        if self.image_press is None: # no selection possible
            return canvas_target_rebuild_required
        img = self.image_press
        if event.state & 0x4: # ctrl-key is pressed 
            ctrl_pressed = True
        else:
            ctrl_pressed = False
        if self.image_press != self.image_release: # same image
            same = False
        else:
            same = True
        if img.is_selected(): # save state before call to unselect_all
            selected = True
        else:
            selected = False
        if ctrl_pressed == False:
            #print("unselect all: ", str(dict_images))
            self.unselect_all(dict_images, canvas)
            True
        print ("***** Action is: "+ str(action)+ ", Selected = "+ str(selected)+ ", actual image is: "+ str(img.get_filename())+ \
          ", image press is: " + (self.image_press.get_filename() if self.image_press is not None else "None") + \
          ", image  release: " + (self.image_release.get_filename() if self.image_release is not None else "None") + \
          ", same = "+ str(same)+ ", ctrl_pressed = "+ str(ctrl_pressed), \
          ", was_selected = " + str(img.was_selected))
        if selected:
            print("Sy")
            if action == action.PRESS:
                print("SyP")
                img.was_selected = True
                self.select_image(img, canvas) # select because unselect all has unselected this image
            else: # action.RELEASE:
            # unselect only if actual image is the same as before
                print("SyR")
                if same:
                    print("SyRSy")
                    if img.was_selected:
                        print("SyRSyWy")
                        self.unselect_image(img, canvas)
                    else:
                        print("SyRSyWn")
                        img.was_selected = True
                        self.select_image(img, canvas) # select because unselect all has unselected this image
                else:
                    print("SyRSn")
                    self.select_image(img, canvas)
                    canvas_target_rebuild_required = True # drop image requires action

        else: # not selected
            print("Sn")
            if action == action.PRESS:
                print("SnP")
                self.select_image(img, canvas)
                img.was_selected = False
            else: # action.RELEASE:
            # unselect only if actual image is the same as before
                print("SnR")
                if same:
                    print("SnRSy")
                    if img.was_selected:
                        print("SnRSyWy")
                        self.unselect_image(img, canvas)
                    else:
                        print("SnRSyWn")
                        img.was_selected = True
                        self.select_image(img, canvas) # select because unselect all has unselected this image
                else:
                    print("SnRSn")
                    self.select_image(img, canvas)
                    canvas_target_rebuild_required = True # drop image requires action
        return canvas_target_rebuild_required
    
    def copy_selected_source_images(self): # copy selected images from source to target
        # find last selected target image, convert into event because we want to use the existing functions for dragging by mouse
        ii = 0
        index = -1 # index of selected Image, the last will and shall win
        for i in self.list_target_images:
            if i.is_selected():
                print("copy_selected_source_images, is_selected: ", i.get_filename())
                index = ii
            ii += 1
        print("copy_selected_source_images, index of last selected = ", str(index))
                

    def drop(self, event):
        # check if mouse is on target canvas
        #print("Drop")
        target_rect = self.get_root_coordinates_for_widget(self.target_canvas)
        source_rect = self.get_root_coordinates_for_widget(self.source_canvas)
        #print("Target rect is: ", str(target_rect))
        self.image_release = None
        if (self.check_event_in_rect(event, target_rect)): # there could be image(s) to drag
            print("*** Drop Event in target_canvas")
            print ("Drop event: ", " x_root: ", str(event.x_root), " y_root: ", str(event.y_root), " x: ", str(event.x), " y: ", str(event.y))
            print ("Target canvasx: ", str(self.target_canvas.canvasx(event.x)), "canvasy: ", str(self.target_canvas.canvasy(event.y)))
            img_closest_id, dist_event_left, dist_event_right = self.find_closest_item(event, target_rect, self.target_canvas, self.dict_target_images)
            if img_closest_id > 0:
                self.image_release = self.dict_target_images[img_closest_id]
                print("image found in target canvas, action = RELEASE: ", self.image_release.get_filename())
            if self.drag_started_in == "source": # drop images from source
                #for t in self.list_target_images:
                #    print("Before Target image: ", t.get_filename())
                # fill list of dragged images by checking if selected
                self.update_target_canvas(event, self.dict_source_images, target_rect)
            elif self.drag_started_in == "target": # move images within target
                # unselect image if it was selected and drop event is on saved image clicked (self.image_clicked)
                canvas_target_rebuild_required = self.selection(event, self.target_canvas, self.dict_target_images, action.RELEASE) 
                print("canvas_target_rebuild_required = ", str(canvas_target_rebuild_required))
                if canvas_target_rebuild_required:
                    self.update_target_canvas(event, self.dict_target_images, target_rect, True)
            else: # do nothing
                print("no image found in source canvas, action = RELEASE")
                
            print("Drag Done.")
                
        elif (self.check_event_in_rect(event, source_rect)): # finish drag and drop mode
            print("Drop Event in source")
            img_closest_id, dist_event_left, dist_event_right = self.find_closest_item(event, source_rect, self.source_canvas, self.dict_source_images)
            if img_closest_id > 0:
                self.image_release = self.dict_source_images[img_closest_id]
                print("image found in source canvas, action = RELEASE: ", self.image_release.get_filename())
                canvas_target_rebuild_required = self.selection(event, self.source_canvas, self.dict_source_images, action.RELEASE)
            else: # do nothing
                print("no image found in source canvas, action = PRESS")
                
        else:
            print("Drop-Event not in target canvas")
        self.drag_started_in = ""

    def update_target_canvas(self, event, dict_images, target_rect, move = False):
        # we want to know if filename of dragged images from source_canvas already exist. If so we don't want to drag them
        # may be in the future we will allow this but we have to rename them because Diatisch relies on uniqueness of filenames
        set_target_filenames = set() # create an empty set
        set_target_filenames.clear()
        if self.drag_started_in == "source":
            for i in self.list_target_images:
                set_target_filenames.add(i.get_filename())

        list_dragged_images = []
        for i in dict_images:
            img = dict_images[i]
            if img.is_selected():
                if img.get_filename() not in set_target_filenames: # skip if already exists
                    if self.drag_started_in == "source": # make a copy of the original source image because we need some independent attributes like selected
                        newcopy = MyImage(img.filename, img.image, self.target_canvas, img.frameids) # make a copy of the original source image because we need some independent attributes like selected 
                        newcopy.selected = img.selected
                        t = newcopy
                        #print("new image", " orig: ", str(img), " copy: ", str(t), " selected: ", str(t.is_selected()))
                    else: # move within target canvas
                        t = img
                    list_dragged_images.append(t)
                    print("appended to list_dragged_images: ", t.get_filename(), " selected: ", str(t.is_selected())) 
                else:
                    print("Dragged image: ", img.get_filename(), " skipped because it already exists")
        if list_dragged_images: #true when not empty

            # get id, distances of image under drop event
            img_closest_id, dist_event_left, dist_event_right = self.find_closest_item(event, target_rect, self.target_canvas, self.dict_target_images)
            
            dragpos = dragposition.BEFORE
            set_dragged_filenames = set() # create an empty set
            if img_closest_id > 0:
                no_target_image = False
                img_closest = self.dict_target_images[img_closest_id]
                file_at_dragposition = img_closest.get_filename()
                if dist_event_left > dist_event_right:
                    dragpos = dragposition.BEHIND # insert BEHIND hit image
                print("closest Target Image has ID: ", img_closest_id, " Filename: " + file_at_dragposition, \
                " dist left: ", str(dist_event_left), " dist right: ", str(dist_event_right), " dragposition: ", str(dragpos))
            else: # no closest image, append dragged images to existing list
                print("No closest Target")
                no_target_image = True
                
            # now insert list of dragged images in target list, before or behind file_at_dragposition
            for i in self.list_target_images:
                print("Before Target Image: ", i.get_filename(), " In list_dragged_images: ", str(i in list_dragged_images), " selected: ", str(i.is_selected()))
            list_dragged_images.sort(key=lambda a: int(a.selected))
            print("list dragged images: " + str(list_dragged_images))
            # we need a SET of dragged filenames
            set_dragged_filenames.clear()
            for i in list_dragged_images:
                set_dragged_filenames.add(i.get_filename())
            # insert dragged images into list_target_images
            # we iterate over list_target_images
            #   if filename in list_dragged_images: next(we don't want it twice)
            #   else if filename = file_at_dragposition
            #     if dragpos = BEFORE, insert list_dragged_images, insert filename
            #     else: insert filename, insert list_dragged_images
            #   else insert filename
            if self.list_target_images == [] or no_target_image: #initial drag from source or drop outside images
                for i in list_dragged_images:
                    self.list_target_images.append(i)
            else:
                list_temp = []
                for i in self.list_target_images:
                    thisfile = i.get_filename()
                    if thisfile ==  file_at_dragposition:
                        if dragpos == dragposition.BEFORE:
                            for j in list_dragged_images:
                                list_temp.append(j)
                            if thisfile not in set_dragged_filenames:
                                list_temp.append(i)
                        else: # dragposition.BEHIND
                            if thisfile not in set_dragged_filenames:
                                list_temp.append(i)
                            for j in list_dragged_images:
                                list_temp.append(j)
                    elif thisfile not in set_dragged_filenames: # skip if in set_dragged_filenames
                        list_temp.append(i)
                
                self.list_target_images = list_temp
            print("list_target_images: ", str(self.list_target_images))
            # rebuild target canvas, refresh dicts
            self.dict_target_images = self.display_image_objects(self.list_target_images, self.target_canvas)
            for t in self.dict_target_images:
                print("dict_target_images id: ", t, " Filename: ", self.dict_target_images[t].get_filename())
            # now select all dragged images
            for i in self.list_target_images:
                # for convenience we select all fragged images and unselect LL OTHERS
                thisfile = i.get_filename()
                print("After Target Image: ", thisfile, " In list_dragged_images: ", str(i in list_dragged_images), " sected: ", str(i.is_selected()))
                if thisfile in set_dragged_filenames: # select
                    self.select_image(i, self.target_canvas)
                    print("thisfile: ", thisfile, " sected: ", str(i.is_selected()), " select_ctr: ", str(self.target_canvas.select_ctr))
                else:
                    self.unselect_image(i, self.target_canvas)


    def find_closest_item(self, event, rect_canvas, canvas, dict_images):
        # this is necessary because tkinter find_closest does not work for drop event, reason unknown
        id = 0
        event_x_pos_in_canvas = event.x_root - rect_canvas[0]
        event_y_pos_in_canvas = event.y_root - rect_canvas[1]
        print ("event_x_pos_in_canvas is: ", str(event_x_pos_in_canvas), '/', str(event_y_pos_in_canvas))
        if canvas.bbox("all") is not None:
            canvas_width  = canvas.bbox("all")[2] - canvas.bbox("all")[0]
            canvas_height = canvas.bbox("all")[3] - canvas.bbox("all")[1]
        else:
            canvas_width  = 0
            canvas_height = 0
        current_scroll_x = canvas.xview()[0] * canvas_width
        current_scroll_y = canvas.yview()[0] * canvas_height
        print("Scroll position x is: ", str(canvas.xview()), " width is: ", str(canvas_width), " xpos: ", str(current_scroll_x))
        print("Scroll position y is: ", str(canvas.yview()), " height is: ", str(canvas_height), " ypos: ", str(current_scroll_y))
        hit = False
        dist_event_left = 0
        dist_event_right = 0
        for id in dict_images:
            #print("Dict Id: ", id, " BBOX: ", str(canvas.bbox(id)))
            pos_border_left   = canvas.bbox(id)[0] - current_scroll_x
            pos_border_right  = canvas.bbox(id)[2] - current_scroll_x
            pos_border_top    = canvas.bbox(id)[1] - current_scroll_y
            pos_border_bottom = canvas.bbox(id)[3] - current_scroll_y
            if pos_border_left <= event_x_pos_in_canvas <= pos_border_right and pos_border_top <= event_y_pos_in_canvas <= pos_border_bottom:
                print("Hit!")
                hit = True
                # distance to left / right border of image:
                dist_event_left  = event_x_pos_in_canvas - pos_border_left
                dist_event_right = pos_border_right - event_x_pos_in_canvas
                break
        if not hit:
            id = 0
        
        return id, dist_event_left, dist_event_right

    def select_all_source_images(self):
        print("select_all_source_images Pressed")
        self.select_all(self.list_source_images, self.source_canvas)

    def delete_selected(self):
        print("Delete Selected Pressed")

    def unselect_all(self, dict_images, canvas):
        for i in dict_images:
            image = dict_images[i]
            #print("Unselect: ", str(image.get_filename()))
            image.unselect(canvas)
        #reset counter
        canvas.select_ctr = 0
    
    def select_all(self, list_images, canvas):
        for i in list_images:
            canvas.select_ctr += 1
            i.select(canvas, canvas.select_ctr)

    def select_image(self, image, canvas):
        canvas.select_ctr += 1
        image.select(canvas, canvas.select_ctr)

    def toggle_selection(self, image, canvas):
        if image.is_selected():
            image.unselect(canvas)
        else: 
            canvas.select_ctr += 1
            image.select(canvas, canvas.select_ctr)

    def unselect_image(self, image, canvas):
        image.unselect(canvas)

    def get_root_coordinates_for_widget(self, widget):
        # return rect of widget-coordinates relative to root window
        x1 = widget.winfo_rootx() 
        x2 = x1 + widget.winfo_width()
        y1 = widget.winfo_rooty()
        y2 = y1 + widget.winfo_height()
        return [x1, y1, x2, y2]

    def check_event_in_rect(self, event, rect): # rect has to be qualified relative to root!
        # check if event is within rect
        if (event.x_root >= rect[0] and event.x_root <= rect[2] and event.y_root >= rect[1] and event.y_root <= rect[3]):
            return True
        else:
            return False

    def display_image_objects(self, list_obj, canvas): # display list of images on canvas, use already converted photos in objects, better performance
        xpos = 0
        ypos = 0
        row  = 0
        col  = 0
        canvas.delete("all")
        dict_images = {}
        for i in list_obj:
            #print("try to show image: " , i.get_filename())
            photo = i.get_image()
            display_width, display_height = photo.width(), photo.height()
            img_id = canvas.create_image(xpos, ypos, anchor='nw', image = photo, tags = 'images')
            # draw rect consisting of 4 dotted lines because create rectagle does not support dotted lines
            dist_frame = 20
            north_west = (xpos + dist_frame, ypos + dist_frame)
            north_east = (xpos + display_width - dist_frame, ypos + dist_frame)
            south_west = (xpos + dist_frame, ypos + display_height - dist_frame)
            south_east = (xpos + display_width - dist_frame, ypos + display_height - dist_frame)
            line_north = canvas.create_line(north_west, north_east, dash=(1, 1), fill = "red", tags="imageframe")
            line_east  = canvas.create_line(north_east, south_east, dash=(1, 1), fill = "red", tags="imageframe")
            line_south = canvas.create_line(south_west, south_east, dash=(1, 1), fill = "red", tags="imageframe")
            line_west  = canvas.create_line(north_west, south_west, dash=(1, 1), fill = "red", tags="imageframe")
            frameids = (line_north, line_east, line_south, line_west)
            i.set_frameids(frameids)
            dict_images[img_id] = i
            #print("   Insert into dict key: ", str(img_id), " filename: " , obj.get_filename())
            xpos += display_width
            col += 1
            if col >= self.n:
                col = 0
                row += 1
                xpos = 0
                ypos += self.row_height
        canvas.update()
        canvas.configure(scrollregion=canvas.bbox("all"))
        #for t in dict_images:
        #    f = dict_images[t].get_filename() 
        #    print("    dict_images id: ", str(t), " filename: " , f)
        return dict_images



if __name__ == "__main__":
    root = tk.Tk()
    app = ImageApp(root, m=10, n=5)  # Set m and n as desired
    root.mainloop()
