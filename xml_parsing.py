import bs4 as bs
import requests


def parse_capabilities_xml(url):
    try:
        response=requests.get(f"{url}?service=WFS&request=GetCapabilities", timeout=10000)
        soup=bs.BeautifulSoup(response.content, "xml")
        return soup
    except Exception as e:
        print(f"Wystąpił błąd {e}")


def get_names(parsed_xml):
    names={}
    items = parsed_xml.find_all("FeatureType")
    for item in items:
        name=item.find("Name").text
        title=item.find("Title").text
        names[title] = name
    return names

def get_version(parsed_xml):
    root = parsed_xml.find("wfs:WFS_Capabilities")
    version=root.get("version")
    return version


