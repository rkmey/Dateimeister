import os
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk

class ScrollableCanvas(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.bind("<Configure>", self.on_configure)

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
        self.Frame_source.place(relx=.01, rely=0.05, relheight=0.9, relwidth=0.48)
        self.Frame_source.configure(relief='groove')
        self.Frame_source.configure(borderwidth="2")
        self.Frame_source.configure(relief="groove")
        self.Frame_source.configure(background="#d9d9d9")
        self.Frame_source.configure(highlightbackground="#d9d9d9")
        self.Frame_source.configure(highlightcolor="black")

        self.Frame_target = tk.Frame(root)
        self.Frame_target.place(relx=.51, rely=0.05, relheight=0.9, relwidth=0.48)
        self.Frame_target.configure(relief='groove')
        self.Frame_target.configure(borderwidth="2")
        self.Frame_target.configure(relief="groove")
        self.Frame_target.configure(background="#d9d9d9")
        self.Frame_target.configure(highlightbackground="#d9d9d9")
        self.Frame_target.configure(highlightcolor="black")

        # canvas source with scrollbars
        self.source_canvas = ScrollableCanvas(self.Frame_source, bg="yellow")
        self.source_canvas.place(relx=0.01, rely=0.01, relheight=.95, relwidth=.95)

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
        self.target_canvas.place(relx=0.01, rely=0.01, relheight=.95, relwidth=.95)

        self.V_target = tk.Scrollbar(self.Frame_target, orient = tk.VERTICAL)
        self.V_target.config(command=self.target_canvas.yview)
        self.target_canvas.config(yscrollcommand=self.V_target.set)  
        self.V_target.place(relx = 1, rely = 0,     relheight = 0.98, relwidth = 0.02, anchor = tk.NE)        

        self.H_target = tk.Scrollbar(self.Frame_target, orient = tk.HORIZONTAL)
        self.H_target.config(command=self.target_canvas.xview)
        self.target_canvas.config(xscrollcommand=self.H_target.set)
        self.H_target.place(relx = 0, rely = 1, relheight = 0.02, relwidth = 0.98, anchor = tk.SW)
        
        self.load_button = tk.Button(root, text="Load Images", command=self.load_images)
        self.load_button.pack()

        self.list_dragged_images = []

        self.dict_source_images = {}
        self.dict_target_images = {}
        self.dict_id_index = {}

        self.source_row, self.source_col = 0, 0
        self.target_row, self.target_col = 0, 0
        self.drag_started_in = ""

        #self.source_canvas.bind("<ButtonPress-1>", self.start_drag)
        #self.target_canvas.bind("<ButtonRelease-1>", self.drop)
        #self.target_canvas.bind("<B1-Motion>", self.on_motion)

        self.root.bind("<ButtonPress-1>", self.start_drag)
        self.root.bind("<ButtonRelease-1>", self.drop)

        self.list_source_imagefiles = []
        self.list_target_images = []
        self.select_ctr = 0 # to keep track of sequence of selection in order to drop images to target in order of selection
       
    def load_images(self):
        self.list_source_imagefiles = []
        directory = filedialog.askdirectory()
        if directory:
            image_files = [f for f in os.listdir(directory) if (f.lower().endswith(".jpg") or f.lower().endswith(".jpeg"))]
            for img_file in image_files:
                img_path = os.path.join(directory, img_file)
                self.list_source_imagefiles.append(img_path)
            self.display_images(self.list_source_imagefiles, self.dict_source_images, self.source_canvas)
        self.source_canvas.configure(scrollregion=self.source_canvas.bbox("all")) # update scrollregion

    def start_drag(self, event):
        # check where mouse is 
        source_rect = self.get_root_coordinates_for_widget(self.source_canvas)
        target_rect = self.get_root_coordinates_for_widget(self.target_canvas)
        #print ("source_canvas: ", str(source_rect))
        #print ("target_canvas: ", str(target_rect))
        #print ("event: ", " x_root: ", str(event.x_root), " y_root: ", str(event.y_root), " x: ", str(event.x), " y: ", str(event.y))
        #print ("Source canvasx: ", str(self.source_canvas.canvasx(event.x)), "canvasy: ", str(self.source_canvas.canvasy(event.y)))
        if (self.check_event_in_rect(event, source_rect)): # select Image(s)
            #print("Event in source_canvas")
            self.drag_started_in = "source"
            self.selection(event, self.source_canvas, self.dict_source_images)
        elif (self.check_event_in_rect(event, target_rect)):
            #print("Event in target_canvas")
            self.drag_started_in = "target"
            self.selection(event, self.target_canvas, self.dict_target_images)
        else:
            #print("Event not in canvas")
            self.drag_started_in = ""
            True

    def on_motion(self, event):
        pass
    
    def selection(self, event, canvas, dict_images):#select / unselect image(s)rom mouse click
        if (closest := canvas.find_closest(canvas.canvasx(event.x), canvas.canvasy(event.y))):
            image_id = closest[0]
            img      = dict_images[image_id]
            #print("closest Image has ID: ", image_id, " closest: ", str(closest))
            if event.state & 0x4: # ctrl-key is pressed : select image and don't unselect all others
                self.toggle_selection(img, canvas) # toggle selection
            else: # unselect all and toggle selection for this image
                if img.is_selected():
                    selected = True
                else:
                    selected = False
                self.unselect_all(dict_images, canvas)
                # print("Selected = ", selected)
                if selected:
                    self.unselect_image(img, canvas)
                else:
                    self.select_image(img, canvas)
        else:
            #print("no closest image")
            True
    
    def drop(self, event):
        # check if mouse is on target canvas
        #print("Drop")
        target_rect = self.get_root_coordinates_for_widget(self.target_canvas)
        source_rect = self.get_root_coordinates_for_widget(self.source_canvas)
        print("Target rect is: ", str(target_rect))
        index = 0
        if (self.check_event_in_rect(event, target_rect)): # there could be image(s) to drag
            print("*** Drop Event in target_canvas")
            print ("Drop event: ", " x_root: ", str(event.x_root), " y_root: ", str(event.y_root), " x: ", str(event.x), " y: ", str(event.y))
            print ("Target canvasx: ", str(self.target_canvas.canvasx(event.x)), "canvasy: ", str(self.target_canvas.canvasy(event.y)))
            if self.drag_started_in == "source": # drop images from source
                #for t in self.list_target_images:
                #    print("Before Target image: ", t.get_filename())
                # fill list of dragged images by checking if selected
                self.update_target_canvas(event, self.dict_source_images, target_rect)
                print("Drag Done.")
            elif self.drag_started_in == "target": # move images within target
                True
                
        elif (self.check_event_in_rect(event, source_rect)): # finish drag and drop mode
            print("Drop Event in source")
            if self.list_dragged_images: #true when not empty
                #print("Release 1 Source: " + str(self.dragged_image.get_image()))
                self.list_dragged_images = [] # do not drop more than once
                
        else:
            print("Drop-Event not in target canvas")

    def update_target_canvas(self, event, dict_images, target_rect):
        self.list_dragged_images = []
        for i in dict_images:
            img = dict_images[i]
            if img.is_selected():
                self.list_dragged_images.append(img)
        if self.list_dragged_images: #true when not empty
            
            # get id, distances of image under drop event
            img_closest_id, dist_event_left, dist_event_right = self.find_closest_item(event, target_rect, self.target_canvas, self.dict_target_images)
            
            if img_closest_id > 0:
                img_closest = self.dict_target_images[img_closest_id]
                index = self.dict_id_index[img_closest_id]
                print("closest Target Image has ID: ", img_closest_id, " Index: ", str(index), \
                  " Filename: " + img_closest.get_filename(), " dist left: ", str(dist_event_left), " dist right: ", str(dist_event_right))
            else: # no closest image, append dragged images to existing list
                print("No closest Target")
                index = 0
                
            # now insert list of dragged images in target list. Index is in dict_id_index
            self.list_dragged_images.sort(key=lambda a: int(a.selected))
            # append dragged images to list_target_images
            if dist_event_left > dist_event_right:
                index += 1 # insert BEHIND hit image
            self.list_target_images[index:index] = self.list_dragged_images
            # rebuild target canvas, refresh dicts
            self.dict_target_images, self.dict_id_index = self.display_image_objects(self.list_target_images, self.target_canvas)
            self.list_dragged_images = [] # do not drop more than once
            #for t in self.list_target_images:
            #    print("After Target image: ", t.get_filename())


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
            print("Dict Id: ", id, " BBOX: ", str(canvas.bbox(id)))
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

    def unselect_all(self, dict_images, canvas):
        for i in dict_images:
            image = dict_images[i]
            image.unselect(canvas)
        #clear list 
        self.list_dragged_images = []
        #reset counter
        self.select_ctr = 0
    
    def select_all(self, dict_images, canvas):
        for i in dict_images:
            image = dict_images[i]
            self.select_ctr += 1
            image.select(canvas, self.select_ctr)

    def select_image(self, image, canvas):
        self.select_ctr += 1
        image.select(canvas, self.select_ctr)

    def toggle_selection(self, image, canvas):
        if image.is_selected():
            image.unselect(canvas)
        else: 
            self.select_ctr += 1
            image.select(canvas, self.select_ctr)

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

    def display_images(self, list_imagefiles, list_images, canvas): # display list of images on canvas
        xpos = 0
        ypos = 0
        row  = 0
        col  = 0
        canvas.delete("all")
        for img_path in list_imagefiles:
            #print("try to show image: " , img_path)
            img = Image.open(img_path)
            image_width_orig, image_height_orig = img.size
            faktor = min(self.row_height / image_height_orig, self.image_width / image_width_orig)
            #print("Image " + img_path + " width = " + str(image_width_orig) + " height = " + str(image_height_orig) + " Faktor = " + str(faktor))
            display_width  = int(image_width_orig * faktor)
            display_height = int(image_height_orig * faktor)
            newsize = (display_width, display_height)
            r_img = img.resize(newsize, Image.Resampling.NEAREST)
            photo = ImageTk.PhotoImage(r_img)
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
            i = MyImage(img_path, photo, canvas, frameids)
            list_images[img_id] = i
            
            
            xpos += display_width
            col += 1
            if col >= self.n:
                col = 0
                row += 1
                xpos = 0
                ypos += self.row_height
        canvas.update()
        canvas.configure(scrollregion=canvas.bbox("all"))
        #self.select_all(list_images, canvas)

    def display_image_objects(self, list_obj, canvas): # display list of images on canvas, use already converted photos in objects, better performance
        xpos = 0
        ypos = 0
        row  = 0
        col  = 0
        canvas.delete("all")
        dict_images = {}
        dict_id_index = {} # for inserting images we have to know which inex in list_obj belongs to id of the image
        index = 0
        for obj in list_obj:
            #print("try to show image: " , obj.get_filename())
            photo = obj.get_image()
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
            i = MyImage(obj.get_filename(), photo, canvas, frameids)
            dict_images[img_id] = i
            #print("   Insert into dict key: ", str(img_id), " filename: " , i.get_filename())
            xpos += display_width
            col += 1
            if col >= self.n:
                col = 0
                row += 1
                xpos = 0
                ypos += self.row_height
            dict_id_index[img_id] = index
            index += 1
        canvas.update()
        canvas.configure(scrollregion=canvas.bbox("all"))
        #for t in dict_images:
        #    f = dict_images[t].get_filename() 
        #    print("    dict_images id: ", str(t), " filename: " , f)
        #self.select_all(list_images, canvas)
        return dict_images, dict_id_index


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageApp(root, m=10, n=5)  # Set m and n as desired
    root.mainloop()
