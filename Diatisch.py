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
    def __init__(self, filename, id, image, canvas, frameids):
        self.filename = filename
        self.id = id   
        self.image = image
        self.frameids = frameids
        self.canvas = canvas
        self.selected = False
        self.unselect(canvas)
    def get_filename(self):
        return self.filename
    def get_id(self):
        return self.id
    def get_image(self):
        return self.image
    def select(self, canvas):
        for frameid in self.frameids:
            self.canvas.itemconfigure(frameid, state = 'normal')
        self.selected = True
    def unselect(self, canvas):
        for frameid in self.frameids:
            self.canvas.itemconfigure(frameid, state = 'hidden')
        self.selected = False
    def toggle_selection(self, canvas):
        if self.selected:
            self.unselect(canvas)
        else:
            self.select(canvas)
    def is_selected(self):
        return self.selected

     
class ImageApp:
    def __init__(self, root, m, n):
        self.root = root
        self.root.title("Image Canvas")
        # Fenstergröße
        screen_width  = int(root.winfo_screenwidth() * .5) # adjust as needed
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

        self.source_row, self.source_col = 0, 0
        self.target_row, self.target_col = 0, 0

        #self.source_canvas.bind("<ButtonPress-1>", self.start_drag)
        #self.target_canvas.bind("<ButtonRelease-1>", self.drop)
        #self.target_canvas.bind("<B1-Motion>", self.on_motion)

        self.root.bind("<ButtonPress-1>", self.start_drag)
        self.root.bind("<ButtonRelease-1>", self.drop)

        self.dict_thumbnails = {}
        self.list_source_imagefiles = []
        self.list_target_imagefiles = []
       
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
        print ("source_canvas: ", str(source_rect))
        print ("target_canvas: ", str(target_rect))
        print ("event: ", " x: ", str(event.x_root), " y: ", str(event.y_root))
        print ("Source canvasx: ", str(self.source_canvas.canvasx(event.x)), "canvasy: ", str(self.source_canvas.canvasy(event.y)))
        if (self.check_event_in_rect(event, source_rect)): # select Image(s)
            print("Event in source_canvas")
            # find image closest to event. For this we have to use the corresponding canvasx / canvasy coordibates instead of original event coordinates
            if (closest := self.source_canvas.find_closest(self.source_canvas.canvasx(event.x), self.source_canvas.canvasy(event.y))):
                image_id = closest[0]
                img      = self.dict_source_images[image_id]
                print("closest Image has ID: ", image_id, " closest: ", str(closest))
                if event.state & 0x4: # ctrl-key is pressed : select image and don't unselect all others
                    img.toggle_selection(self.source_canvas) # toggle selection
                else: # unselect all and toggle selection for this image
                    if img.is_selected():
                        selected = True
                    else:
                        selected = False
                    self.unselect_all(self.dict_source_images, self.source_canvas)
                    # print("Selected = ", selected)
                    if selected:
                        img.unselect(self.source_canvas)
                    else:
                        img.select(self.source_canvas)
            else:
                print("no closest image")
        elif (self.check_event_in_rect(event, target_rect)):
            print("Event in target_canvas")
        else:
            print("Event not in canvas")

    def on_motion(self, event):
        pass
    
    def drop(self, event):
        # check if mouse is on target canvas
        print("Drop")
        target_rect = self.get_root_coordinates_for_widget(self.target_canvas)
        source_rect = self.get_root_coordinates_for_widget(self.source_canvas)
        if (self.check_event_in_rect(event, target_rect)): # there could be image(s) to drag
            print("Drop Event in target_canvas")
            # fill list of dragged images by checking if selected
            self.list_dragged_images = []
            for i in self.dict_source_images:
                img = self.dict_source_images[i]
                if img.is_selected():
                    self.list_dragged_images.append(img)
            #print("List of dragged images: ", str(self.list_dragged_images))
            if self.list_dragged_images: #true when not empty
                for img in self.list_dragged_images:
                    filename = img.get_filename()
                    #print("Drop Image: " + filename)
                    self.list_target_imagefiles.append(filename)
                    self.display_images(self.list_target_imagefiles, self.dict_target_images, self.target_canvas)
                    self.list_dragged_images = [] # do not drop more than once
                
        elif (self.check_event_in_rect(event, source_rect)): # finish drag and drop mode
            print("Drop Event in source")
            if self.list_dragged_images: #true when not empty
                #print("Release 1 Source: " + str(self.dragged_image.get_image()))
                self.list_dragged_images = [] # do not drop more than once
                
        else:
            print("Drop-Event not in target canvas")

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
            print("Image " + img_path + " width = " + str(image_width_orig) + " height = " + str(image_height_orig) + " Faktor = " + str(faktor))
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
            i = MyImage(img_path, img_id, photo, canvas, frameids)
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

    def unselect_all(self, dict_images, canvas):
        for i in dict_images:
            image = dict_images[i]
            image.unselect(canvas)
        #clear list 
        self.list_dragged_images = []
    
    def select_all(self, dict_images, canvas):
        for i in dict_images:
            image = dict_images[i]
            image.select(canvas)


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageApp(root, m=10, n=5)  # Set m and n as desired
    root.mainloop()
