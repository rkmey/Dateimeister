import os
import tkinter as tk
from tkinter.constants import *
from tkinter import filedialog
from tkinter import messagebox
from tkinter.font import Font
from PIL import Image, ImageTk
import Tooltip as TT
from datetime import datetime, timezone
import hashlib
import re
import Undo_Redo as UR


from enum import Enum
class action(Enum):
    PRESS   = 1
    RELEASE = 2
class dragposition(Enum):
    BEFORE  = 1
    BEHIND  = 2
    
class pt(Enum):
    DROP_FROM_SOURCE  = 1
    DROP_FROM_TARGET  = 2
    COPY_SELECTED     = 3
    COPY_SINGLE       = 4
    DELETE_SELECTED   = 5
    DELETE_SINGLE     = 6


class ScrollableCanvas(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<Configure>", self.on_configure)
        self.select_ctr = 0

    def on_configure(self, event):
        self.configure(scrollregion=self.bbox("all"))
        #print ("<Configure> called")

class MyImage:
    def __init__(self, filename, canvas, tag):
        self.filename = filename
        self.tag = tag
        self.canvas = canvas
        self.selected = 0
        self.was_selected = False
        
    def get_filename(self):
        return self.filename
    def get_image(self):
        return Diatisch.dict_filename_images[Diatisch.idx_akt][self.filename]
    def get_ctr(self):
        return self.selected
    def select(self, canvas, ctr):
        #print("  find with tag ", self.tag, ": ", str(self.canvas.find_withtag(self.tag)))
        for i in self.canvas.find_withtag(self.tag):
            self.canvas.itemconfigure(i, state = 'normal')
        if not self.is_selected(): 
            changed = True
        else:
            changed = False
        self.selected = ctr
        return changed # True if prior state was not selected, False otherwise
    def unselect(self, canvas):
        for i in self.canvas.find_withtag(self.tag):
            self.canvas.itemconfigure(i, state = 'hidden')
        if not self.is_selected(): 
            changed = False
        else:
            changed = True
        self.selected = 0
        return changed # True if prior state was selected, False otherwise
    def is_selected(self):
        if self.selected > 0:
            return True
        else:
            return False
    def get_tag(self):
        return self.tag

     
class Diatisch:
    line_width = 5
    line_color = "red"
    # 20240813 we want to store images only once per canvas not in every MyImage-object, access is via filename which is stored in MyImage object
    #  we need dict as a "global" class variable because we want to access it also from methods of MyImage-objects.
    idx_high = 0 # Index into dict, incrementented by each call to load_images
    idx_akt  = 0 # current index into dict according to history (undo / redo)
    dict_filename_images = {}
    dict_filename_images[idx_akt] = {} # Filename -> MyImage contains all source filenames which is sufficient as target files are a subset of source files
    def __init__(self, root = None, list_imagefiles = None, list_result = None, callback = None): # if called from own main root will be initialized there
        if root is None:
            self.root = tk.Toplevel()
        else:
            self.root = root
        self.root.title("Diatisch")
        print("List Imagefiles is: " + str(list_imagefiles))
        # Fenstergröße
        physical_width  = self.root.winfo_screenwidth()
        physical_height = self.root.winfo_screenheight()
        screen_width  = int(self.root.winfo_screenwidth() * .75) # adjust as needed
        screen_height = int(self.root.winfo_screenheight() * .5) # adjust as needed
        print("Bildschirm ist " + str(screen_width) + " x " + str(screen_height) + " physical: " + str(physical_width) + " x " + str(physical_height))
        v_dim=str(screen_width)+'x'+str(screen_height)
        self.root.geometry(v_dim)

        self.m, self.n = 10, 5
        self.image_width = 1500  # Adjust as needed
        self.row_height  = 200
        self.xpos = 0
        self.ypos = 0

        self.root.bind("<Configure>", self.on_configure) # we want to know if size changes
        self.width  = 0
        self.height = 0
        self.text_font = Font(family="Helvetica", size=8)

        self.frame_labels_height = 0.04 # needed for calculation of font size
        self.label_height = 0.9 # needed for calculation of font size
        self.Frame_labels = tk.Frame(self.root)
        self.Frame_labels.place(relx=.01, rely=0.00, relheight=self.frame_labels_height, relwidth=0.98)
        self.Frame_labels.configure(relief='groove')
        self.Frame_labels.configure(borderwidth="2")
        self.Frame_labels.configure(relief="groove")
        self.Frame_labels.configure(background="#d9d9d9")
        self.Frame_labels.configure(highlightbackground="#d9d9d9")
        self.Frame_labels.configure(highlightcolor="black")

        self.Label_source_ctr = tk.Label(self.Frame_labels)
        self.Label_source_ctr.place(relx=0.0, rely=0.0, relheight=self.label_height, relwidth=0.3)
        self.Label_source_ctr.configure(anchor=tk.NW)
        self.Label_source_ctr.configure(background="#d9d9d9")
        self.Label_source_ctr.configure(font=self.text_font)
        self.Label_source_ctr.configure(text='Num Images Source: 0')

        self.Label_process_id = tk.Label(self.Frame_labels)
        self.Label_process_id.place(relx=0.35, rely=0.0, relheight=self.label_height, relwidth=0.3)
        self.Label_process_id.configure(anchor=tk.NW)
        self.Label_process_id.configure(background="#d9d9d9")
        self.Label_process_id.configure(font=self.text_font)
        self.Label_process_id.configure(text='Process ID: 0')

        self.Label_target_ctr = tk.Label(self.Frame_labels)
        self.Label_target_ctr.place(relx=.6, rely=0.0, relheight=self.label_height, relwidth=0.3)
        self.Label_target_ctr.configure(anchor=tk.NE)
        self.Label_target_ctr.configure(background="#d9d9d9")
        self.Label_target_ctr.configure(font=self.text_font)
        self.Label_target_ctr.configure(text='Num Images Target: 0')


        self.Frame_source = tk.Frame(self.root)
        self.Frame_source.place(relx=.01, rely=0.05, relheight=0.85, relwidth=0.48)
        self.Frame_source.configure(relief='groove')
        self.Frame_source.configure(borderwidth="2")
        self.Frame_source.configure(relief="groove")
        self.Frame_source.configure(background="#d9d9d9")
        self.Frame_source.configure(highlightbackground="#d9d9d9")
        self.Frame_source.configure(highlightcolor="black")

        self.Frame_target = tk.Frame(self.root)
        self.Frame_target.place(relx=.51, rely=0.05, relheight=0.85, relwidth=0.48)
        self.Frame_target.configure(relief='groove')
        self.Frame_target.configure(borderwidth="2")
        self.Frame_target.configure(relief="groove")
        self.Frame_target.configure(background="#d9d9d9")
        self.Frame_target.configure(highlightbackground="#d9d9d9")
        self.Frame_target.configure(highlightcolor="black")

        self.Frame_source_ctl = tk.Frame(self.root)
        self.Frame_source_ctl.place(relx=.01, rely=0.92, relheight=0.05, relwidth=0.48)
        self.Frame_source_ctl.configure(relief='groove')
        self.Frame_source_ctl.configure(borderwidth="2")
        self.Frame_source_ctl.configure(relief="groove")
        self.Frame_source_ctl.configure(background="#d9d9d9")
        self.Frame_source_ctl.configure(highlightbackground="#d9d9d9")
        self.Frame_source_ctl.configure(highlightcolor="black")

        self.Frame_target_ctl = tk.Frame(self.root)
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
        buttonpos_target += relwidth_target
        self.button_undo = tk.Button(self.Frame_target_ctl, text="Undo", command=self.button_undo_h)
        self.button_undo.place(relx=buttonpos_target, rely=0.01, relheight=0.98, relwidth=relwidth_target)
        buttonpos_target += relwidth_target
        self.button_redo = tk.Button(self.Frame_target_ctl, text="Redo", command=self.button_redo_h)
        self.button_redo.place(relx=buttonpos_target, rely=0.01, relheight=0.98, relwidth=relwidth_target)

        self.button_undo.config(state = tk.DISABLED)
        self.button_redo.config(state = tk.DISABLED)
        self.root.bind('<Control-z>', lambda event: self.process_undo(event))
        self.root.bind('<Control-y>', lambda event: self.process_redo(event))


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
        self.st = TT.ToolTip(self.source_canvas, "no images available", delay=0, follow = True)
        self.tt = TT.ToolTip(self.target_canvas, "no images available", delay=0, follow = True)

        # temporary storage of dragged images while dragging
        self.list_dragged_images = []

        # dict and list of source / target images, to be historized
        self.dict_source_images = {} # ID -> MyImage
        self.dict_target_images = {} # ID -> MyImage
        self.list_source_images = []
        self.list_target_images = []
        self.list_result = list_result  # reference given from caller
        self.callback = None
        if callback:
            self.callback = callback
        
        # Undo /Redo control
        self.UR = UR.Undo_Redo_Diatisch()
        self.dict_processid_histobj = {} # key processid to be applied value: histobj
        # historize initial state
        self.historize_process()
        # Undo /Redo control end

        self.event = None

        # Create the context menues
        self.context_menu_source = tk.Menu(self.source_canvas, tearoff=0)
        self.context_menu_source.add_command(label="Show"   , command=self.canvas_image_show)    
        self.context_menu_source.add_command(label="Copy Selected"   , command=self.copy_selected_source_images)    
        self.context_menu_source.add_command(label="Copy "   , command=self.copy_single_source_image)    
        self.context_menu_target = tk.Menu(self.target_canvas, tearoff=0)
        self.context_menu_target.add_command(label="Show"   , command=self.canvas_image_show)  
        self.context_menu_target.add_command(label="Delete Selected"   , command=self.delete_selected_target_images)    
        self.context_menu_target.add_command(label="Delete "   , command=self.delete_single_target_image)    

        self.timestamp = datetime.now() 
        self.image_press = None
        self.image_release = None
        
        self.root.protocol("WM_DELETE_WINDOW", self.close_handler)
        
        # the following two change attributes are for a transaction of press / release. 
        # They are set to false in start_drag, changed in selection() and used in drop to decide about rebuild canvas and historization
        self.canvas_target_rebuild_required = False
        self.selection_changed = False
        self.dist_frame = 20 # distance of dotted select frame from border in Pixels
        self.single_image_to_copy   = None # name of single image selected by menuitem to copy from source to target
        self.single_image_to_delete = None # name of single image selected by menuitem to delete from target
        if list_imagefiles:
            self.load_images(list_imagefiles)

    def on_configure(self, event):
        x = str(event.widget)
        if x == ".": # . is toplevel window
            if (self.width != event.width):
                self.width = event.width
                #print(f"The width of Toplevel is {self.width}")        
            if (self.height != event.height):
                self.height = event.height
                self.Label_source_ctr.update()
                l_height = self.Label_source_ctr.winfo_height()
                fontsize_use = int(.8 * min(12.0, l_height * .75))
                print(f"The height of Toplevel is {self.height}, label height is {l_height} set fontsize to {fontsize_use}")
                self.text_font.configure(size=fontsize_use)                
                

    def load_images(self, p_imagefiles = None):
        self.list_source_images = []
        self.dict_source_images = {}
        self.list_target_images = []
        self.dict_target_images = {}
        self.source_canvas.delete("all")
        self.target_canvas.delete("all")
        Diatisch.idx_high += 1
        Diatisch.idx_akt = Diatisch.idx_high
        Diatisch.dict_filename_images[Diatisch.idx_akt] = {}
        #self.UR.reset()
        tag_prefix = 'P'
        tag_no = 0
        directory = None
        if p_imagefiles: # imagefiles given by caller
            image_files = p_imagefiles
        else:
            directory = filedialog.askdirectory()
            if directory:
                image_files = [f for f in os.listdir(directory) if (f.lower().endswith(".jpg") or f.lower().endswith(".jpeg"))]
            else:
                messagebox.showerror("Open", "unable to open: " + directory, parent = self.root)
                return False
        for img_file in image_files:
            tag_no += 1
            if directory:
                filename = os.path.join(directory, img_file)
            else:
                filename = img_file
            # get image
            img = Image.open(filename)
            image_width_orig, image_height_orig = img.size
            faktor = min(self.row_height / image_height_orig, self.image_width / image_width_orig)
            #print("Image " + filename + " width = " + str(image_width_orig) + " height = " + str(image_height_orig) + " Faktor = " + str(faktor))
            display_width  = int(image_width_orig * faktor)
            display_height = int(image_height_orig * faktor)
            newsize = (display_width, display_height)
            r_img = img.resize(newsize, Image.Resampling.NEAREST)
            photo = ImageTk.PhotoImage(r_img)
            # insert into self.list_source_images
            i = MyImage(filename, self.source_canvas, tag_prefix + str(tag_no))
            self.list_source_images.append(i)
            Diatisch.dict_filename_images[Diatisch.idx_akt][filename] = photo
            
        self.dict_source_images = self.display_image_objects(self.list_source_images, self.source_canvas, self.Label_source_ctr)
        self.unselect_all(self.dict_source_images, self.source_canvas)
        self.source_canvas.configure(scrollregion=self.source_canvas.bbox("all")) # update scrollregion
        print("LOAD ", directory)
        self.historize_process()
        self.root.lift()

    def show_context_menu_source(self, event):
        # event has to be stored because some functions require x, y
        self.event = event
        text = "no image available"
        # falls wir keine anzeigbare Datei haben, müssen wir show-Item disablen
        canvas_x = self.source_canvas.canvasx(event.x)
        canvas_y = self.source_canvas.canvasy(event.y)
        if (closest := self.source_canvas.find_closest(self.source_canvas.canvasx(event.x), self.source_canvas.canvasy(event.y))):
            image_id = closest[0]
            img      = self.dict_source_images[image_id]
            text     = img.get_filename()
            self.context_menu_source.entryconfig(0, label = "Show " + text)
            self.context_menu_source.entryconfig(2, label = "Copy " + text)
            self.single_image_to_copy = img # will be set to None in update_target_canvas after copying
            selected = False
            for i in self.list_source_images:
                if i.is_selected():
                    selected = True
                    break
            if selected: # at least one selected
                self.context_menu_source.entryconfig(1, state = tk.NORMAL)
            else:
                self.context_menu_source.entryconfig(1, state = tk.DISABLED)
            self.context_menu_source.post(event.x_root, event.y_root)
    
    def show_context_menu_target(self, event):
        # event has to be stored because some functions require x, y
        self.event = event
        text = "no image available"
        # falls wir keine anzeigbare Datei haben, müssen wir show-Item disablen
        canvas_x = self.target_canvas.canvasx(event.x)
        canvas_y = self.target_canvas.canvasy(event.y)
        if (closest := self.target_canvas.find_closest(self.target_canvas.canvasx(event.x), self.target_canvas.canvasy(event.y))):
            image_id = closest[0]
            img      = self.dict_target_images[image_id]
            text     = img.get_filename()
            self.context_menu_target.entryconfig(0, label = "Show " + text)
            self.context_menu_target.entryconfig(2, label = "Delete " + text)
            self.single_image_to_delete = img # will be set to None in delete_target_canvas after delete
            selected = False
            for i in self.list_target_images:
                if i.is_selected():
                    selected = True
                    break
            if selected: # at least one selected
                self.context_menu_target.entryconfig(1, state = tk.NORMAL)
            else:
                self.context_menu_target.entryconfig(1, state = tk.DISABLED)
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
            if image_id in self.dict_source_images:
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
            if image_id in self.dict_target_images:
                img      = self.dict_target_images[image_id]
                text     = img.get_filename()
                if text != self.tooltiptext_tt:
                    self.tt.update(text)
                    self.tooltiptext_tt = text
                       
    def canvas_image_show(self):
        # placeholder for call full screen display of image
        print("Context menu show")
        #self.canvas_show(self.event)


    def start_drag(self, event):
        # as we have a transaction of 2 steps (press / release) we have to keep the change attributes as member variables
        self.canvas_target_rebuild_required = False
        self.selection_changed = False
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
        if self.image_press is None: # no selection possible
            return
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
            c = self.unselect_all(dict_images, canvas)
            self.selection_changed = self.check_changed(self.selection_changed, c)
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
                c = self.select_image(img, canvas) # select because unselect all has unselected this image
                self.selection_changed = self.check_changed(self.selection_changed, c)
            else: # action.RELEASE:
            # unselect only if actual image is the same as before
                print("SyR")
                if same:
                    print("SyRSy")
                    if img.was_selected:
                        print("SyRSyWy")
                        c = self.unselect_image(img, canvas)
                        self.selection_changed = self.check_changed(self.selection_changed, c)
                    else:
                        print("SyRSyWn")
                        img.was_selected = True
                        c = self.select_image(img, canvas) # select because unselect all has unselected this image
                        self.selection_changed = self.check_changed(self.selection_changed, c)
                else:
                    print("SyRSn")
                    c = self.select_image(img, canvas)
                    self.selection_changed = self.check_changed(self.selection_changed, c)
                    self.canvas_target_rebuild_required = True # drop image requires action

        else: # not selected
            print("Sn")
            if action == action.PRESS:
                print("SnP")
                c = self.select_image(img, canvas)
                self.selection_changed = self.check_changed(self.selection_changed, c)
                img.was_selected = False
            else: # action.RELEASE:
            # unselect only if actual image is the same as before
                print("SnR")
                if same:
                    print("SnRSy")
                    if img.was_selected:
                        print("SnRSyWy")
                        c = self.unselect_image(img, canvas)
                        self.selection_changed = self.check_changed(self.selection_changed, c)
                    else:
                        print("SnRSyWn")
                        img.was_selected = True
                        c = self.select_image(img, canvas) # select because unselect all has unselected this image
                        self.selection_changed = self.check_changed(self.selection_changed, c)
                else:
                    print("SnRSn")
                    c = self.select_image(img, canvas)
                    self.selection_changed = self.check_changed(self.selection_changed, c)
                    self.canvas_target_rebuild_required = True # drop image requires action
        return
    
    def check_changed(self, s, c):
        # if 1st arg is False, set to True is 2nd arg is true. Purpose: never reset a True value to False
        sret = s
        if s == False:
            if c == True:
                sret = True
        return sret

    
    # event handlers for context menus
    def copy_selected_source_images(self): # copy selected images from source to target
        # find last selected target image
        self.drag_started_in = "source" # must be set for the following functions
        self.file_at_dragposition = self.find_last_selected_target_image(self.list_target_images)
        target_rect = self.get_root_coordinates_for_widget(self.target_canvas)
        changed = self.update_target_canvas(None, self.dict_source_images, target_rect, pt.COPY_SELECTED)
        if changed:
            self.historize_process()        
    def copy_single_source_image(self): # copy image under context menuitem select... from source to target
        # find last selected target image
        self.drag_started_in = "source" # must be set for the following functions
        self.file_at_dragposition = self.find_last_selected_target_image(self.list_target_images)
        target_rect = self.get_root_coordinates_for_widget(self.target_canvas)
        changed = self.update_target_canvas(None, self.dict_source_images, target_rect, pt.COPY_SINGLE)
        if changed:
            self.historize_process()        
    def delete_selected_target_images(self): # delete selected images from target
        self.delete_target_canvas(self.dict_target_images, pt.DELETE_SELECTED)
        self.historize_process()        
    def delete_single_target_image(self): # delete image under context menuitem delete... from target
        self.delete_target_canvas(self.dict_target_images, pt.DELETE_SINGLE)
        self.historize_process()        

    def find_last_selected_target_image(self, list_images): # helper function for finding last selected target (as insert point for copy)
        # find last selected target image
        ii = 0
        filename_of_last_selected = ""
        index = -1 # index of selected Image, the last will and shall win
        for i in list_images:
            if i.is_selected():
                filename_of_last_selected = i.get_filename()
                print("find selected target images, is_selected: ", filename_of_last_selected)
                index = ii
            ii += 1
        print("find selected target images, index of last selected = ", str(index))
        return filename_of_last_selected

    def drop(self, event):
        # check if mouse is on target canvas
        #print("Drop")
        target_rect = self.get_root_coordinates_for_widget(self.target_canvas)
        source_rect = self.get_root_coordinates_for_widget(self.source_canvas)
        #print("Target rect is: ", str(target_rect))
        self.image_release = None
        changed = False
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
                changed = self.update_target_canvas(event, self.dict_source_images, target_rect, pt.DROP_FROM_SOURCE)
            elif self.drag_started_in == "target": # move images within target
                # unselect image if it was selected and drop event is on saved image clicked (self.image_clicked)
                self.selection(event, self.target_canvas, self.dict_target_images, action.RELEASE) 
                print("canvas_target_rebuild_required = ", str(self.canvas_target_rebuild_required))
                if self.canvas_target_rebuild_required:
                    changed = self.update_target_canvas(event, self.dict_target_images, target_rect, pt.DROP_FROM_TARGET)
            else: # do nothing
                print("no image found in source canvas, action = RELEASE")
                
            print("Drag Done.")
                
        elif (self.check_event_in_rect(event, source_rect)): # finish drag and drop mode
            print("Drop Event in source")
            img_closest_id, dist_event_left, dist_event_right = self.find_closest_item(event, source_rect, self.source_canvas, self.dict_source_images)
            if img_closest_id > 0:
                self.image_release = self.dict_source_images[img_closest_id]
                print("image found in source canvas, action = RELEASE: ", self.image_release.get_filename())
                self.selection(event, self.source_canvas, self.dict_source_images, action.RELEASE)
            else: # do nothing
                print("no image found in source canvas, action = PRESS")
                
        else:
            print("Drop-Event not in target canvas")

        if  changed or self.selection_changed: 
            self.historize_process()
        self.drag_started_in = ""

    def update_target_canvas(self, event, dict_images, target_rect, proctype):
        old_list_target_filenames = [] # for checking if list is changed
        new_list_target_filenames = [] # for checking if list is changed
        for i in self.list_target_images:
            old_list_target_filenames.append(i.get_filename()) 
        changed = False  # init to false
            
        # we want to know if filename of dragged images from source_canvas already exist. If so we don't want to drag them
        # may be in the future we will allow this but we have to rename them because Diatisch relies on uniqueness of filenames
        set_target_filenames = set() # create an empty set
        set_target_filenames.clear()
        if proctype == pt.DROP_FROM_SOURCE or proctype == pt.COPY_SELECTED:
            for i in self.list_target_images:
                set_target_filenames.add(i.get_filename())

        list_dragged_images = []
        if proctype == pt.DROP_FROM_SOURCE or proctype == pt.COPY_SELECTED:
            for i in dict_images:
                img = dict_images[i]
                if img.is_selected():
                    if img.get_filename() not in set_target_filenames: # skip if already exists
                        newcopy = MyImage(img.get_filename(), self.target_canvas, img.get_tag()) # make a copy of the original source image because we need some independent attributes like selected 
                        newcopy.selected = img.selected
                        t = newcopy
                        #print("new image", " orig: ", str(img), " copy: ", str(t), " selected: ", str(t.is_selected()))
                        list_dragged_images.append(t)
                        print("appended to list_dragged_images: ", t.get_filename(), " selected: ", str(t.is_selected())) 
                    else:
                        print("Dragged image: ", img.get_filename(), " skipped because it already exists")
        elif proctype == pt.DROP_FROM_TARGET:
            for i in dict_images:
                img = dict_images[i]
                if img.is_selected():
                    if img.get_filename() not in set_target_filenames: # skip if already exists
                        t = img
                        list_dragged_images.append(t)
                        print("appended to list_dragged_images: ", t.get_filename(), " selected: ", str(t.is_selected())) 
                    else:
                        print("Dragged image: ", img.get_filename(), " skipped because it already exists")

        elif proctype == pt.COPY_SINGLE:
            if self.single_image_to_copy is None:
                messagebox.showerror(str(proctype), "Internal error single image to copy is None.", parent = self.root)
                return
            img = self.single_image_to_copy
            if img.get_filename() not in set_target_filenames: # skip if already exists
                newcopy = MyImage(img.get_filename(), self.target_canvas, img.get_tag()) # make a copy of the original source image because we need some independent attributes like selected 
                newcopy.selected = img.selected
                t = newcopy
                #print("new image", " orig: ", str(img), " copy: ", str(t), " selected: ", str(t.is_selected()))
                list_dragged_images.append(t)
                print("appended to list_dragged_images: ", t.get_filename(), " selected: ", str(t.is_selected())) 
            else:
                print("Dragged image: ", img.get_filename(), " skipped because it already exists")
            self.single_image_to_copy = None # reset because update_target_canvas checks if None

        if list_dragged_images:# true when not empty
            
            dragpos = dragposition.BEFORE
            set_dragged_filenames = set() # create an empty set
            no_target_image = False
            if event is not None: # event from mouse release
                # get id, distances of image under drop event
                img_closest_id, dist_event_left, dist_event_right = self.find_closest_item(event, target_rect, self.target_canvas, self.dict_target_images)
                if img_closest_id > 0:
                    img_closest = self.dict_target_images[img_closest_id]
                    file_at_dragposition = img_closest.get_filename()
                    if dist_event_left > dist_event_right:
                        dragpos = dragposition.BEHIND # insert BEHIND hit image
                    print("closest Target Image has ID: ", img_closest_id, " Filename: " + file_at_dragposition, \
                    " dist left: ", str(dist_event_left), " dist right: ", str(dist_event_right), " dragposition: ", str(dragpos))
                else: # no closest image, append dragged images to existing list
                    print("No closest Target")
                    no_target_image = True
                    dragpos = dragposition.BEHIND
            else: # no event, call is from copy_selected_source_images(Button copy selected)
                file_at_dragposition = self.file_at_dragposition
                if file_at_dragposition == "": # no target image selected, append
                    no_target_image = True
                dragpos = dragposition.BEHIND

            # now insert list of dragged images in target list, before or behind file_at_dragposition
            for i in self.list_target_images:
                print("Before Target Image: ", i.get_filename(), " In list_dragged_images: ", str(i in list_dragged_images), " selected: ", str(i.is_selected()))
            list_dragged_images.sort(key=lambda a: int(a.selected))
            #print("list dragged images: " + str(list_dragged_images))
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
            if self.list_target_images == []: #initial drag from source
                for i in list_dragged_images:
                    self.list_target_images.append(i)
            elif no_target_image: # drop outside images: start with all images not in list_dragged_images, followed by list_dragged images
                list_temp = []
                for i in self.list_target_images:
                    thisfile = i.get_filename()
                    if thisfile not in set_dragged_filenames:
                        list_temp.append(i)
                for j in list_dragged_images:
                    list_temp.append(j)
                self.list_target_images = list_temp    
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
            #print("list_target_images: ", str(self.list_target_images))
            # rebuild target canvas, refresh dicts
            for i in self.list_target_images:
                new_list_target_filenames.append(i.get_filename()) 
            changed = self.lists_equal(new_list_target_filenames, old_list_target_filenames)
            if changed:
                self.dict_target_images = self.display_image_objects(self.list_target_images, self.target_canvas, self.Label_target_ctr)
                #for t in self.dict_target_images:
                #    print("dict_target_images id: ", t, " Filename: ", self.dict_target_images[t].get_filename())
                # now select all dragged images
                for i in self.list_target_images:
                    # for convenience we select all dragged images and unselect all others
                    thisfile = i.get_filename()
                    print("After Target Image: ", thisfile, " In list_dragged_images: ", str(i in list_dragged_images), " sected: ", str(i.is_selected()))
                    if thisfile in set_dragged_filenames: # select
                        self.select_image(i, self.target_canvas)
                        print("thisfile: ", thisfile, " sected: ", str(i.is_selected()), " select_ctr: ", str(self.target_canvas.select_ctr))
                    else:
                        self.unselect_image(i, self.target_canvas)
            else:
                print ("list target images has not changed")
                #print("list old: ", str(old_list_target_filenames))
                #print("list new: ", str(new_list_target_filenames))
        self.file_at_dragposition = ""
        return changed # o historization if false

    def delete_target_canvas(self, dict_images, proctype):
        # delete 1 single or all selected Images from target_canvas
        self.list_target_images = [] 
        for i in dict_images:
            img = dict_images[i]
            if proctype == pt.DELETE_SELECTED: # we insert all images which are not selected (because we wish to delete all which are selected)
                if not img.is_selected():
                    self.list_target_images.append(img)
            elif proctype == pt.DELETE_SINGLE: # we insert all images which are not image_to_delete (because we wish to delete all which are selected)
                if self.single_image_to_delete is None:
                    messagebox.showerror(str(proctype), "Internal error single image to delete is None.", parent = self.root)
                    return
                if img.get_filename() != self.single_image_to_delete.get_filename():
                    self.list_target_images.append(img)
        # rebuild target canvas, refresh dicts
        self.dict_target_images = self.display_image_objects(self.list_target_images, self.target_canvas, self.Label_target_ctr)
        # now select / unselect, remember: display image objects always shows selecttion frame because it is drawn last!
        for i in self.list_target_images:
            # we selected all images which were selected before the delete action and unselect the others
            if i.is_selected(): # select
                self.select_image(i, self.target_canvas)
            else:
                self.unselect_image(i, self.target_canvas)
        self.single_image_to_delete = None

    def lists_equal(self, l1, l2):
        changed = False
        if len(l1) != len(l2):
            changed = True
        else:
            length = len(l1)
            for i in range(length):
                if l1[i] != l2[i]:
                    changed = True
                    break
        return changed

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
                #print("Hit!")
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
        changed = self.select_all(self.list_source_images, self.source_canvas)
        if changed:
            self.historize_process()

    def delete_selected(self):
        print("Delete Selected Pressed")

    def unselect_all(self, dict_images, canvas):
        changed = False
        for i in dict_images:
            image = dict_images[i]
            #print("Unselect: ", str(image.get_filename()))
            c = image.unselect(canvas)
            changed = self.check_changed(changed, c)
        #reset counter
        canvas.select_ctr = 0
        return changed
    
    def select_all(self, list_images, canvas):
        changed = False
        for i in list_images:
            if not i.is_selected():
                canvas.select_ctr += 1
                c = i.select(canvas, canvas.select_ctr)
                changed = self.check_changed(changed, c)
        return changed

    def select_image(self, image, canvas):
        changed = False
        if not image.is_selected():
            canvas.select_ctr += 1
            print ("--- SELECT CALL")
            changed = image.select(canvas, canvas.select_ctr)
        return changed

    def toggle_selection(self, image, canvas):
        if image.is_selected():
            image.unselect(canvas)
        else: 
            canvas.select_ctr += 1
            image.select(canvas, canvas.select_ctr)

    def unselect_image(self, image, canvas):
        changed = False
        changed = image.unselect(canvas)
        return changed

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

    def display_image_objects(self, list_obj, canvas, label_ctr): # display list of images on canvas, use already converted photos in objects, better performance
        xpos = 0
        ypos = 0
        row  = 0
        col  = 0
        ctr  = 0
        canvas.delete("all")
        dict_images = {}
        for i in list_obj:
            filename = i.get_filename()
            #print("try to show image: " , filename)
            photo = i.get_image()
            img_id = canvas.create_image(xpos, ypos, anchor='nw', image = photo, tags = 'images')
            display_width, display_height = photo.width(), photo.height()
            # draw rect consisting of 4 dotted lines because create rectagle does not support dotted lines
            north_west = (xpos + self.dist_frame, ypos + self.dist_frame)
            north_east = (xpos + display_width - self.dist_frame, ypos + self.dist_frame)
            south_west = (xpos + self.dist_frame, ypos + display_height - self.dist_frame)
            south_east = (xpos + display_width - self.dist_frame, ypos + display_height - self.dist_frame)
            line_north = canvas.create_line(north_west, north_east, dash=(1, 1), fill = Diatisch.line_color, width = Diatisch.line_width, tags=i.get_tag())
            line_east  = canvas.create_line(north_east, south_east, dash=(1, 1), fill = Diatisch.line_color, width = Diatisch.line_width, tags=i.get_tag())
            line_south = canvas.create_line(south_west, south_east, dash=(1, 1), fill = Diatisch.line_color, width = Diatisch.line_width, tags=i.get_tag())
            line_west  = canvas.create_line(north_west, south_west, dash=(1, 1), fill = Diatisch.line_color, width = Diatisch.line_width, tags=i.get_tag())
            dict_images[img_id] = i
            #print("   Insert into dict key: ", str(img_id), " filename: " , obj.get_filename())
            ctr += 1
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
        labeltext = label_ctr.cget('text')
        labeltext = re.sub(r"\d+$", f"{str(ctr)}", labeltext) # replace single backslash by slash
        label_ctr.config(text = labeltext)
        return dict_images

    # Undo /Redo functions
    def process_undo(self, event):
        print("ctrl_z pressed.")
        rc, p_now, p_before = self.UR.process_undo()
        if not rc: # undo was not possible
            messagebox.showinfo("UNDO", "no further processes which can be undone", parent = self.root)
        else:
            self.apply_process_id(p_now, p_before)
            self.endis_buttons()

    def process_redo(self, event):
        print("ctrl_y pressed.")
        rc, p_now, p_before = self.UR.process_redo()
        if not rc:
            messagebox.showinfo("REDO", "no further processes which can be redone", parent = self.root)
        else:
            self.apply_process_id(p_now, p_before)
            self.endis_buttons()

    def button_undo_h(self, event = None):
        print("Button Undo pressed")
        self.process_undo(event)
        
    def button_redo_h(self, event = None):
        print("Button Redo pressed")
        self.process_redo(event)

    def endis_buttons(self): # disable / enable buttons depending on processids
        rc_undo, rc_redo = self.UR.endis_buttons()
        if rc_undo:
            self.button_undo.config(state = NORMAL)
        else:
            self.button_undo.config(state = DISABLED)
        if rc_redo:
            self.button_redo.config(state = NORMAL)
        else:
            self.button_redo.config(state = DISABLED)


    def apply_process_id(self, process_id, processid_predecessor):
        print("apply_process_id, id to apply is: ", str(process_id), " processid was: ", str(processid_predecessor))
        
        h = self.dict_processid_histobj[process_id]
        Diatisch.idx_akt = h.idx_akt            
        list_obj_source = h.list_source_images
        list_obj_target = h.list_target_images
        source_new = False
        target_new = False
        if h.str_hashsum_source_filenames != self.dict_processid_histobj[processid_predecessor].str_hashsum_source_filenames:
            # rebuild list of source images
            self.list_source_images = []
            self.dict_source_images = {}
            for i in list_obj_source:
                self.list_source_images.append(i)
            self.dict_source_images = self.display_image_objects(self.list_source_images, self.source_canvas, self.Label_source_ctr)
            source_new = True
 
        if h.str_hashsum_target_filenames != self.dict_processid_histobj[processid_predecessor].str_hashsum_target_filenames:
            # rebuild list of target images
            self.list_target_images = []
            self.dict_target_images = {}
            for i in list_obj_target:
                self.list_target_images.append(i)
            self.dict_target_images = self.display_image_objects(self.list_target_images, self.target_canvas, self.Label_target_ctr)
            target_new = True

        # restore the select counters for sequence of selection
        self.source_canvas.select_ctr = h.source_select_ctr
        self.target_canvas.select_ctr = h.target_select_ctr
        # apply selection if canvas has changed or hashsums for selection are not equal
        if source_new or h.str_hashsum_source_selection != self.dict_processid_histobj[processid_predecessor].str_hashsum_source_selection:
            # list_obj and self.list_source_images have same structure, so we can use an index to access the elements of self.list_source_images
            ii = 0
            for i in list_obj_source:
                # print("* H SOURCE Filename / select_ctr / selected / tag: ", i.filename, ' / ' , i.selected, ' / ', str(i.is_selected()), ' / ', i.tag)
                if i.is_selected():
                    self.list_source_images[ii].select(self.source_canvas, i.get_ctr())
                else:
                    self.list_source_images[ii].unselect(self.source_canvas)
                ii += 1
        if target_new or h.str_hashsum_target_selection != self.dict_processid_histobj[processid_predecessor].str_hashsum_target_selection:
            # list_obj and self.list_target_images have same structure, so we can use an index to access the elements of self.list_source_images
            ii = 0
            for i in list_obj_target:
                #print("* H TARGET Filename / select_ctr / selected / tag: ", i.filename, ' / ' , i.selected, ' / ', str(i.is_selected()), ' / ', i.tag)
                if i.is_selected():
                    self.list_target_images[ii].select(self.target_canvas, i.get_ctr())
                else:
                    self.list_target_images[ii].unselect(self.target_canvas)
                ii += 1
        labeltext = self.Label_process_id.cget('text')
        labeltext = re.sub(r"\d+$", f"{str(process_id)}", labeltext) # replace num by processid
        self.Label_process_id.config(text = labeltext)
        
    def historize_process(self):
        h = HistObj()
        # for quick compare if lists of two historized states is equal we need the checksums
        hashsum_source_filenames = hashlib.md5()
        hashsum_target_filenames = hashlib.md5()
        hashsum_source_selection = hashlib.md5()
        hashsum_target_selection = hashlib.md5()
        str_source_selection = ""
        str_target_selection = ""
        for i in self.list_source_images:
            #print("* H Filename / select_ctr / selected / tag: ", i.filename, ' / ' , i.selected, ' / ', str(i.is_selected()), ' / ', i.tag)
            newcopy = MyImage(i.get_filename(), i.canvas, i.tag) # make a copy of the original source image because we need some independent attributes like selected 
            newcopy.selected = i.selected
            h.list_source_images.append(newcopy)
            hashsum_source_filenames.update(i.filename.encode(encoding = 'UTF-8', errors = 'strict'))
            str_source_selection += str(i.selected)
        for i in self.list_target_images:
            newcopy = MyImage(i.get_filename(), i.canvas, i.tag) # make a copy of the original source image because we need some independent attributes like selected 
            newcopy.selected = i.selected
            h.list_target_images.append(newcopy)
            hashsum_target_filenames.update(i.filename.encode(encoding = 'UTF-8', errors = 'strict'))
            str_target_selection += str(i.selected)
        #for i in self.dict_source_images:
        #    h.dict_source_images[i] = self.dict_source_images[i]
        #for i in self.dict_target_images:
        #    h.dict_target_images[i] = self.dict_target_images[i]
        
        h.source_select_ctr = self.source_canvas.select_ctr
        h.target_select_ctr = self.target_canvas.select_ctr
        
        # historize hashsums
        h.str_hashsum_source_filenames = hashsum_source_filenames.hexdigest()
        h.str_hashsum_target_filenames = hashsum_target_filenames.hexdigest()

        hashsum_source_selection.update(str_source_selection.encode(encoding = 'UTF-8', errors = 'strict'))
        h.str_hashsum_source_selection = hashsum_source_selection.hexdigest()
        hashsum_target_selection.update(str_target_selection.encode(encoding = 'UTF-8', errors = 'strict'))
        h.str_hashsum_target_selection = hashsum_target_selection.hexdigest()
        print("Hashsum source Filenames is: ", h.str_hashsum_source_filenames, " Hashsum target Filenames is: ", h.str_hashsum_target_filenames)
        print("Hashsum source Selection is: ", h.str_hashsum_source_selection, "(", str_source_selection, ")", " Hashsum target Selection is: ", h.str_hashsum_target_selection, "(", str_target_selection, ")")
        h.idx_akt = Diatisch.idx_akt
        
        self.UR.historize_process()
        self.dict_processid_histobj[self.UR.get_processid_akt()] = h
        self.endis_buttons()
        labeltext = self.Label_process_id.cget('text')
        labeltext = re.sub(r"\d+$", f"{str(self.UR.get_processid_akt())}", labeltext) # replace num by processid
        self.Label_process_id.config(text = labeltext)

    # Ende undo /redo-Funktionen


    def close_handler(self): #calles when window is closing
        print("Diatisch: call callback when window is closed")
        if self.callback:
            for i in self.list_target_images:
                #print(i)
                self.list_result.append(i.get_filename())
            self.callback()
        self.root.destroy()

class HistObj:
    def __init__(self):

        # dict and list of source / target images, to be historized
        self.dict_source_images = {}
        self.dict_target_images = {}
        self.list_source_images = []
        self.list_target_images = []
        self.source_select_ctr = 0
        self.target_select_ctr = 0
        self.str_hashsum_source_filenames = ""
        self.str_hashsum_target_filenames = ""
        self.str_hashsum_source_selection = ""
        self.str_hashsum_target_selection = ""
        idx_akt = 0 # Index into Diatisch.dict


if __name__ == "__main__":
    root = tk.Tk()
    app = Diatisch(root, False, False, False)  # when run as main we have no list of image files and no result list, no callback
    root.mainloop()
