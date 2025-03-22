import geocoder
from geopy.geocoders import Nominatim
from pyproj import Proj, transform
import requests
from shapely import wkb, wkt
import win32com
from win32com.client import Dispatch
import win32com.client
import pythoncom
import bs4 as bs
import tkintermapview


class CustomMapView(tkintermapview.TkinterMapView):
    """
    A custom map view that zooms to the user's IP location on initialization.
    """
    def __init__(self, *args, **kwargs):
        """
        Initializes the CustomMapView and zooms to the user's IP location.
        """
        super().__init__(*args, **kwargs)
        self.zoom_to_ip()

    def zoom_to_ip(self):
        """
        Zooms the map to the user's current IP location.
        """
        coords = geocoder.ip('me').latlng
        self.set_position(coords[0], coords[1])
        self.set_zoom(15)


def get_address(coords, callback):
    """
    Retrieves the address for the given coordinates.

    Args:
        coords (tuple): The coordinates to get the address for.
        callback (function): The callback function to handle the address.
    """
    geolocator = Nominatim(user_agent='http')
    location = geolocator.reverse(f"{str(coords[0])}, {str(coords[1])}")
    address = location.address if location else "Adres nieznany"
    callback(address)


def get_user_location():
    """
    Retrieves the user's current location based on their IP address.
    """
    location = geocoder.ip('me')
    coords = location.latlng

def form_url(coords):
    """
    Forms a URL to retrieve parcel data based on the given coordinates.

    Args:
        coords (tuple): The coordinates to form the URL for.

    Returns:
        str: The formed URL.
    """
    print(coords)
    proj_2180 = Proj(init='epsg:2180')
    proj_4326 = Proj(init='epsg:4326')
    y4326, x4326 = coords
    longitude, latitude = transform(proj_4326, proj_2180, x4326, y4326)
    url=f'https://uldk.gugik.gov.pl/?request=GetParcelByXY&xy={longitude},{latitude}&result=geom_wkb,id'
    return url

def retrieve_coords_id(url):
    """
    Retrieves the coordinates and ID from the given URL.

    Args:
        url (str): The URL to retrieve data from.

    Returns:
        tuple: A tuple containing the coordinates and ID.
    """
    response=requests.get(url)

    coords=response.text.split('|')[0]
    id=response.text.split('|')[1][:-1]

    wkt = wkb.loads(bytes.fromhex(coords[1:]))
    coords = list(wkt.exterior.coords)
    return coords, id


def coords2180to4326(coords):
    """
    Converts coordinates from EPSG:2180 to EPSG:4326.

    Args:
        coords (list): The coordinates to convert.

    Returns:
        list: The converted coordinates.
    """
    proj_2180 = Proj(init='epsg:2180')
    proj_4326 = Proj(init='epsg:4326')
    transformed=[]

    for i, point in enumerate(coords):
        x2180, y2180 = point
        longitude, latitude = transform(proj_2180, proj_4326, x2180, y2180)
        transformed.append((latitude, longitude))
    return transformed


def acad_connect():
    """
    Connects to the AutoCAD application.

    Returns:
        object: The active AutoCAD document.
    """
    acadApp=Dispatch("AutoCAD.Application.25")
    acadApp.Visible=1 
    acadDoc = acadApp.ActiveDocument
    return acadDoc

def coords4326to2180(coords):
    """
    Converts coordinates from EPSG:4326 to EPSG:2180.

    Args:
        coords (list): The coordinates to convert.

    Returns:
        list: The converted coordinates.
    """
    proj_2180 = Proj(init='epsg:2180')
    proj_4326 = Proj(init='epsg:4326')
    transformed=[]

    for i, point in enumerate(coords):
        x4326, y4326 = point
        x,y  = transform(proj_2180, proj_4326, x4326, y4326)
        transformed.append((y, x))
    return transformed


def list_to_variant(lista):
    """
    Converts a list of coordinates to a variant array.

    Args:
        lista (list): The list of coordinates.

    Returns:
        object: The variant array.
    """
    lista = [item for tup in lista for item in tup]
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (lista))

def draw_in_acad(acadDoc, list):
    """
    Draws a polygon in AutoCAD based on the given coordinates.

    Args:
        acadDoc (object): The active AutoCAD document.
        list (list): The list of coordinates to draw.
    """
    try:
        acadDoc.ModelSpace.AddLightWeightPolyline(list_to_variant(coords4326to2180(list)))
        acadDoc.SendCommand("_.ZOOM _E ")
    except:
        print(f"Wystąpił błąd")

def parse_capabilities_xml(url):
    """
    Parses the capabilities XML from the given WFS service URL.

    Args:
        url (str): The URL of the WFS service.

    Returns:
        object: The parsed XML soup.
    """
    try:
        response=requests.get(f"{url}?service=WFS&request=GetCapabilities", timeout=10000)
        soup=bs.BeautifulSoup(response.content, "xml")
        return soup
    except Exception as e:
        print(f"Wystąpił błąd {e}")
    return soup

def get_names(parsed_xml):
    """
    Retrieves the names and titles of the available layers from the parsed XML.

    Args:
        parsed_xml (object): The parsed XML soup.

    Returns:
        dict: A dictionary of layer titles and names.
    """
    titles={}
    items = parsed_xml.find_all("FeatureType")
    for item in items:
        name=item.find("Name").text
        title=item.find("Title").text
        titles[title] = name
    return titles

import re

def extract_geometry(xml_string):
    """
    Extracts geometry data from the given XML string.

    Args:
        xml_string (str): The XML string to extract geometry from.

    Returns:
        list: A list of extracted polygons.
    """
    polygon_pattern = r'POLYGON\s*\(\((.*?)\)\)'
    polygons = re.finditer(polygon_pattern, xml_string)
    
    return polygons

def extract_coordinates(wkt_string):
    """
    Extracts coordinates from the given WKT string.

    Args:
        wkt_string (str): The WKT string to extract coordinates from.

    Returns:
        list: A list of extracted coordinates.
    """
    print(wkt_string)
    
    pattern = r"POLYGON \(\((.*?)\)\)"
    
    match = re.search(pattern, wkt_string)
    
    if match:
        coords_str = match.group(1)  
        
        coords = coords_str.split(", ")
        
        coordinates = []
        for coord in coords:
            lat, lon = map(float, coord.split())
            coordinates.append((lat, lon))
        
        return coordinates
    else:
        raise ValueError("Invalid WKT format")

def get_gml_data(gml):
    """
    Retrieves GML data from the given GML string.

    Args:
        gml (str): The GML string to extract data from.

    Returns:
        list: A list of extracted polygons.
    """
    results = extract_geometry(gml)
    
    polygons = []
    for result in results:
        coords = result.group(1).strip() 

        coord_list = coords.split(',')
        first_point = coord_list[0].strip()
        last_point = coord_list[-1].strip()
        
        coords = ', '.join(coord_list)
        wkt_geom = f"LINESTRING({coords})"
        
        print(f"WKT: {wkt_geom}")
        
        polygons.append(wkt.loads(wkt_geom))
        
    return polygons