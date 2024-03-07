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
        print ("Configure> called")

class MyImage:
    def __init__(self, filename, id, image):
        self.filename = filename
        self.id = id   
        self.image = image

    def get_filename(self):
        return self.filename
    def get_id(self):
        return self.id
    def get_image(self):
        return self.image
        
class ImageApp:
    def __init__(self, root, m, n):
        self.root = root
        self.root.title("Image Canvas")
        # Fenstergröße
        screen_width  = int(root.winfo_screenwidth() * 1.0)
        screen_height = int(root.winfo_screenheight() * 1.0)
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

        self.dragged_image = None

        self.source_images = []
        self.target_images = []

        self.source_row, self.source_col = 0, 0
        self.target_row, self.target_col = 0, 0

        self.source_canvas.bind("<Button-1>", self.start_drag)
        self.target_canvas.bind("<ButtonRelease-1>", self.drop)
        #self.target_canvas.bind("<B1-Motion>", self.drop)

        self.dict_thumbnails = {}
        
    def load_images(self):
        directory = filedialog.askdirectory()
        if directory:
            image_files = [f for f in os.listdir(directory) if (f.lower().endswith(".jpg") or f.lower().endswith(".jpeg"))]
            for img_file in image_files:
                img_path = os.path.join(directory, img_file)
                #print("try to show image: " , img_path)
                img = Image.open(img_path)
                image_width_orig, image_height_orig = img.size
                faktor = min(self.row_height / image_height_orig, self.image_width / image_width_orig)
                print("Image " + img_file + " width = " + str(image_width_orig) + " height = " + str(image_height_orig) + " Faktor = " + str(faktor))
                display_width  = int(image_width_orig * faktor)
                display_height = int(image_height_orig * faktor)
                newsize = (display_width, display_height)
                r_img = img.resize(newsize, Image.Resampling.NEAREST)
                photo = ImageTk.PhotoImage(r_img)
                img_id = self.source_canvas.create_image(self.xpos, self.ypos, anchor='nw', image = photo, tags = 'images')
                i = MyImage(img_path, img_id, photo)
                self.source_images.append(i)
                self.xpos += display_width
                self.source_col += 1
                if self.source_col >= self.n:
                    self.source_col = 0
                    self.source_row += 1
                    self.xpos = 0
                    self.ypos += self.row_height
            self.source_canvas.update()
            self.source_canvas.configure(scrollregion=self.source_canvas.bbox("all"))
            self.target_canvas.configure(scrollregion=self.target_canvas.bbox("all"))


    def start_drag(self, event):
        for i, img in enumerate(self.source_images):
            if self.source_canvas.bbox(img.get_id()) and \
            self.source_canvas.bbox(img.get_id())[0] <= event.x <= self.source_canvas.bbox(img.get_id())[2] and \
            self.source_canvas.bbox(img.get_id())[1] <= event.y <= self.source_canvas.bbox(img.get_id())[3]:
                self.dragged_image = img
                print("Drag Image event: ", str(event), " Id: ", str(img.get_id()), " bbox: ", str(self.source_canvas.bbox(img.get_id())))
                break

    def drop(self, event):
        if self.dragged_image:
            print("Drop Image: " + str(self.dragged_image.get_image()))
            x, y = self.target_canvas.canvasx(event.x), self.target_canvas.canvasy(event.y)
            img = self.target_canvas.create_image(self.target_col * self.image_width, self.target_row * 200, anchor="nw", image=self.dragged_image.get_image())
            self.target_images.append(img)
            self.target_col += 1
            if self.target_col >= self.n:
                self.target_col = 0
                self.target_row += 1
            #self.dragged_image = None

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageApp(root, m=10, n=5)  # Set m and n as desired
    root.mainloop()
