from fastapi import FastAPI, HTTPException
from xml.etree import ElementTree as ET
import geopandas as gpd
import shapely.geometry
import requests

app = FastAPI()

@app.get("/calculate_length/")
async def calculate_length(changeset_id: int):
    url = f"https://www.openstreetmap.org/api/0.6/changeset/{changeset_id}/download"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error fetching changeset: {e}")

    try:
        xml_content = response.text
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise HTTPException(status_code=400, detail=f"Error parsing XML: {e}")

    nodes = {}
    for node in root.findall(".//node"):
        node_id = node.attrib['id']
        lat = float(node.attrib['lat'])
        lon = float(node.attrib['lon'])
        nodes[node_id] = (lon, lat)

    linestrings = []
    for way in root.findall(".//way"):
        way_nodes = []
        for nd in way.findall(".//nd"):
            ref = nd.attrib['ref']
            if ref in nodes:
                way_nodes.append(nodes[ref])
        linestring = shapely.geometry.LineString(way_nodes)
        linestrings.append(linestring)

    gdf = gpd.GeoDataFrame(geometry=linestrings).set_crs("EPSG:4326")
    gdf = gdf.to_crs(gdf.estimate_utm_crs().to_epsg())

    total_length = int(gdf.length.sum())
    return {"total_length": total_length}

