import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkintermapview
import geocoder
from geopy.geocoders import Nominatim
import json
import requests
import bs4 as bs
import threading
from scripts.map_utils import *
import sys
from PIL import Image, ImageTk
import concurrent.futures
import sys
import os


if getattr(sys, 'frozen', False): 
    base_path = sys._MEIPASS  
else:  
    base_path = os.path.abspath(".")


image_path = os.path.join(base_path, 'assets/ikona.jpg')
json_path=os.path.join(base_path, 'wfs_services.json')

               
class PagePolygons(ttk.Frame):
    """
    A class to represent the main frame for loading and displaying polygons on a map.

    Attributes:
        markers (list): A list to store map markers.
        photo (ImageTk.PhotoImage): The image icon for the application.
        polygons (list): A list to store polygon objects.
        map_widget (CustomMapView): The map widget for displaying the map.
        adres (ttk.StringVar): A variable to store the selected address.
        dzialki (ttk.StringVar): A variable to store the information about added plots.
    """
    def __init__(self, parent, controller):
        """
        Initializes the PagePolygons frame.

        Args:
            parent: The parent widget.
            controller: The controller widget.
        """
        super().__init__(parent)
        self.markers=[]
        ico = Image.open(image_path).resize((100, 100))
        self.photo = ImageTk.PhotoImage(ico)
        self.polygons = []
        frame_top = ttk.Frame(self, padding=10)
        frame_top.pack(fill=X)
        frame_main = ttk.Frame(self)
        frame_main.pack(fill=BOTH, expand=True)
        
        frame_map = ttk.Frame(frame_main)
        frame_map.pack(fill=BOTH, expand=True, side=LEFT, padx=10, pady=10)
        
        frame_right = ttk.Frame(frame_main, padding=10, bootstyle="light")
        frame_right.pack(fill=Y, side=RIGHT, padx=10, pady=10)

        
        tytul = ttk.Label(frame_top, text="Aplikacja do wczytywania poligonów", font=("Arial", 20))
        tytul.pack()
        
        self.map_widget = CustomMapView(frame_map, width=700, height=400, corner_radius=10)
        self.map_widget.pack(padx=20, pady=20, expand=True, fill=BOTH)
        self.map_widget.add_left_click_map_command(self.left_click_event)
        self.map_widget.add_right_click_menu_command(label="Dodaj róg boudingbox",command=self.add_marker_event, pass_coords=True)
        self.adres = ttk.StringVar()
        ttk.Label(frame_map, text="Wybrany adres:", font=("Arial", 12, "bold")).pack(anchor=W, padx=10, pady=5)
        ttk.Label(frame_map, textvariable=self.adres, font=("Arial", 10)).pack(anchor=W, padx=10)
        
        self.dzialki = ttk.StringVar()
        image_label = ttk.Label(frame_right, image=self.photo)
        image_label.pack(side="top")  
        self.dzialki.set("Kliknij na mapę, aby dodać działki!")
        ttk.Label(frame_right, text="Dodano działkę:", font=("Arial", 15, "bold")).pack()
        ttk.Label(frame_right, textvariable=self.dzialki, font=("Arial", 12)).pack()
        frame_progress=ttk.Frame(frame_right, bootstyle="light")
        frame_progress.pack()
        frame_upload = ttk.Frame(frame_right, bootstyle="light")
        frame_upload.pack(pady=50)

        self.frame_buttons = ttk.Frame(frame_right)
        self.frame_buttons.pack(pady=30)
        
        
        
        self.progress = ttk.Progressbar(frame_progress, length=300, mode="indeterminate")
        self.progress.pack_forget()

        ttk.Button(frame_upload, text="Wczytaj do AutoCAD", command=self.polygons_to_acad, bootstyle="success",width=40).pack(pady=(20,5), side="top")
        self.show_wfs=ttk.Button(frame_upload, text="Otwórz panel usług WFS", command=self.show_frame ,width=40)
        self.show_wfs.pack(pady=5, side="top")
        #opcje
        ttk.Button(frame_upload, text="Cofnij", command=self.delete_last_polygon, bootstyle="warning", width=40).pack(pady=5, side="top")
        ttk.Button(frame_upload, text="Wyczyść wszystkie", command=self.delete_all_polygons, bootstyle="danger", width=40).pack(pady=5, side="top", padx=5)
        
       

       #serwisy
        wfs_label = ttk.Label(self.frame_buttons, text="Panel wfs", font=("Arial", 15)).pack(pady=(30,20))
        serwisy = ttk.Label(self.frame_buttons, text="Dostępne serwery:", font=("Arial", 10)).pack()
        self.prechoosed()
        self.options = list(self.nazwy)
        self.servicecb =ttk.Combobox(self.frame_buttons, values=self.options)
        self.servicecb.set(self.options[0])
        self.servicecb.pack(pady=10)
        
        #warstwy
    
        dostepne = ttk.Label(self.frame_buttons, text="Dostępne warstwy:", font=("Arial", 10)).pack(pady=(30,0))
        self.layers=[]
        self.layerscb =ttk.Combobox(self.frame_buttons, values=self.layers)
        self.layerscb.pack(pady=10)
        self.servicecb.bind("<<ComboboxSelected>>", lambda event: self.get_layers())
        ttk.Button(self.frame_buttons, text="Usuń boundingbox", command=self.delete_bb, bootstyle="danger", width=20).pack(pady=5, side="top")
        ttk.Button(self.frame_buttons, text="Pobierz warstwy", command=self.get_gml, width=20).pack(pady=5, side="top")
        ttk.Button(self.frame_buttons, text="Zamknij", command= self.hide_frame, bootstyle="secondary", width=40).pack()
        self.frame_buttons.pack_forget()


    def prechoosed(self):
        """
        Loads the predefined WFS services from the JSON file.
        """
        with open(json_path, mode="r", encoding="utf-8") as read_file:
            data = json.load(read_file)

        self.nazwy = [service['nazwa'] for service in data['services']]
        self.url = {service['nazwa']: service['url'] for service in data['services']}

    def get_layers(self):
        """
        Retrieves the available layers for the selected WFS service.
        """
        self.nazwa = self.servicecb.get()
        wybrany_url = self.url[self.nazwa]
        soap = parse_capabilities_xml(wybrany_url)
        self.layers = get_names(soap)
        self.layerscb["values"] = list(self.layers.keys())
        self.layerscb.set(list(self.layers.keys())[0])
        
    def get_polygon_data(self, map_coords):
        """
        Retrieves polygon data based on the given map coordinates.

        Args:
            map_coords (tuple): The coordinates of the clicked point on the map.
        """
        self.progress.pack()
        self.progress.start()
        url = form_url(map_coords)
        coords2180, id = retrieve_coords_id(url)
        coords4326 = coords2180to4326(coords2180)
        self.after(0, lambda: self.add_polygon_to_map(coords4326, id))
        self.progress.stop()
        self.progress.pack_forget()

    def add_polygon_to_map(self, coords, id):
        """
        Adds a polygon to the map based on the given coordinates.

        Args:
            coords (list): The coordinates of the polygon.
            id (str): The ID of the polygon.
        """
        if not hasattr(self, "polygons"):
            self.polygons = []
    
        polygon = self.map_widget.set_polygon(
            coords,
            fill_color='red',
            name=f'{id}')
        
        self.polygons.append(polygon)
        self.after(0, lambda: self.dzialki.set(f"{polygon.name}\n"))

    def left_click_event(self, coordinates_tuple):
        """
        Handles the left-click event on the map.

        Args:
            coordinates_tuple (tuple): The coordinates of the clicked point.
        """
        threading.Thread(target=get_address, args=(coordinates_tuple, self.update_output)).start()
        threading.Thread(target=self.get_polygon_data, args=(coordinates_tuple,), daemon=True).start()

    def update_output(self, address):
        """
        Updates the address label with the given address.

        Args:
            address (str): The address to display.
        """
        print(f"Aktualizacja adresu: {address}")
        self.after(0, lambda: self.adres.set(f"{address}\n"))
        print(f'{address}')


    def polygons_to_acad(self):
        """
        Exports the drawn polygons to AutoCAD.
        """
        self.progress.pack()
        self.progress.start()
        acadDoc = acad_connect()
        for polygon in self.polygons:
            draw_in_acad(acadDoc, polygon.position_list)
        self.map_widget.delete_all_polygon()
        self.progress.stop()
        self.progress.pack_forget()

    def delete_last_polygon(self):
        """
        Deletes the last added polygon from the map.
        """
        if self.polygons:
            last_polygon = self.polygons.pop()
            last_polygon.delete()

    def delete_all_polygons(self):
        """
        Deletes all polygons from the map.
        """
        self.map_widget.delete_all_polygon()
        for polygon in self.polygons:
            polygon.delete()

    def get_gml(self):
        """
        Fetches GML data for the selected layer and bounding box.
        """
        def fetch_gml():
            try:
                print(self.layers)
                self.layer = self.layers[self.layerscb.get()]
                self.service = self.servicecb.get()
                self.requestsurl = self.url[self.service]

                self.xmin = self.bb.position_list[0][0]
                self.xmax = self.bb.position_list[1][0]
                self.ymin = self.bb.position_list[0][1]
                self.ymax = self.bb.position_list[2][1]
        
                response = requests.get(f'{self.requestsurl}?VERSION=1.1&SERVICE=WFS&REQUEST=GetFeature&TYPENAME={self.layer}&bbox={self.xmin},{self.ymin},{self.xmax},{self.ymax}')
                response.raise_for_status()
                print(response.text)
                self.data = get_gml_data(response.text)
            
                if self.data:
                    for i in self.data:
                        coords = list(i.coords)
                        self.after(0, lambda: self.add_polygon_to_map(coords, id="polygon_id"))
                    self.delete_bb()

            except requests.RequestException as e:
                print(f"Error fetching GML: {e}")

        threading.Thread(target=fetch_gml, daemon=True).start()

    def add_marker_event(self, coords):
        """
        Adds a marker to the map at the given coordinates.

        Args:
            coords (tuple): The coordinates where the marker should be placed.
        """
        if len(self.markers) < 2:   
            print("Add marker:", coords)
            new_marker = self.map_widget.set_marker(coords[0], coords[1])
            self.markers.append(new_marker)
        
            if len(self.markers) == 2:
                self.draw_bounding_box()

        else:
            print("Bounding box already drawn!")

    def draw_bounding_box(self):
        """
        Draws a bounding box on the map based on the two markers.
        """
        self.marker1=self.markers[0]
        self.marker2=self.markers[1]

        if self.marker1.position[0]<self.marker2.position[0]:
            self.leftx=self.marker1.position[0]
            self.rightx=self.marker2.position[0]
        else:
            self.rightx=self.marker1.position[0]
            self.leftx=self.marker2.position[0]

        if self.marker1.position[1]<self.marker2.position[1]:
            self.topy=self.marker1.position[1]
            self.lowy=self.marker2.position[1]
        else:
            self.lowy=self.marker1.position[1]
            self.topy=self.marker2.position[1]
            
        top_left = (self.leftx, self.topy) 
        bottom_right = (self.rightx, self.lowy)
        top_right = (self.rightx, self.topy) 
        bottom_left = (self.leftx, self.lowy)

        coordinates = [top_left, top_right, bottom_right, bottom_left]

        self.bb=self.map_widget.set_polygon(coordinates, fill_color='blue', outline_color='red')
        print(self.bb.position_list)
    
    def delete_bb(self):
        """
        Deletes the bounding box and its markers from the map.
        """
        self.map_widget.delete_all_marker()
        self.bb.delete()
        self.markers=[]

    def show_frame(self):
        """
        Shows the WFS services frame.
        """
        self.show_wfs.pack_forget()
        self.frame_buttons.pack(pady=20, expand=True)

    def hide_frame(self):
        """
        Hides the WFS services frame.
        """
        self.frame_buttons.pack_forget()
        self.show_wfs.pack()


class MainApp(ttk.Window):
    """
    A class to represent the main application window.

    Attributes:
        frames (dict): A dictionary to store the frames of the application.
    """
    def __init__(self):
        """
        Initializes the MainApp window.
        """
        super().__init__(themename="cosmo")
        self.title("AutoCAD plot loader")
        self.geometry("900x600")
        ico = Image.open(image_path)
        photo = ImageTk.PhotoImage(ico)
        self.wm_iconphoto(False, photo)
        self.iconphoto(False, photo) 
        
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        self.frames = {}
        frame = PagePolygons(container, self)
        self.frames[PagePolygons] = frame
        frame.grid(row=0, column=0, sticky="nsew")
        
        self.show_frame(PagePolygons)
    
    def show_frame(self, page):
        """
        Raises the specified frame to the top.

        Args:
            page: The frame to be displayed.
        """
        frame = self.frames[page]
        frame.tkraise()


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()