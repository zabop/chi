from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from xml.etree import ElementTree as ET
import geopandas as gpd
import shapely.geometry
import urllib.parse
import requests

app = FastAPI()

origins = [
    "https://zabop.github.io",
    # "*" # local dev
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)


@app.get("/calculate_length/")
async def calculate_length(changeset_id: int):
    url = f"https://www.openstreetmap.org/api/0.6/changeset/{changeset_id}/download"

    root = ET.fromstring(requests.get(url).text)

    way_ids = []
    create_blocks = root.findall(".//create")
    for create in create_blocks:
        for way in create.findall(".//way"):
            way_ids.append(way.get("id"))

    OVERPASS_URL = "http://overpass-api.de/api/interpreter"

    query = "".join([f"way({way_id});" for way_id in way_ids])
    query = "[out:json][timeout:25];(" + query + ");out body;>;out skel qt;"

    resp = requests.post(OVERPASS_URL, data={"data": query}).json()

    nodes = {
        e["id"]: (e["lon"], e["lat"]) for e in resp["elements"] if e["type"] == "node"
    }

    ways = []
    for element in resp["elements"]:
        if element["type"] == "way":
            ways.append(
                shapely.geometry.LineString(
                    [nodes[node_id] for node_id in element["nodes"]]
                )
            )

    lengths = []
    for way in ways:
        s = gpd.GeoSeries(way).set_crs("4326")
        crs = s.estimate_utm_crs()
        lengths.append(s.to_crs(crs).length.sum())

    encoded_geojson = urllib.parse.quote(
        gpd.GeoDataFrame(geometry=ways).set_crs("4326").to_json()
    )
    geojsonio_url = f"https://geojson.io/#data=data:application/json,{encoded_geojson}"

    return {"total_length": int(sum(lengths)), "geojsonio_url": geojsonio_url}
