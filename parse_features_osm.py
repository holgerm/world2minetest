import argparse
import json
from collections import defaultdict

from pyproj import CRS, Transformer

from _util import SURFACES, DECORATIONS

parser = argparse.ArgumentParser(description="Parse OSM data")
parser.add_argument("file", type=argparse.FileType("r", encoding="utf-8"), help="GeoJSON file with OSM data")
parser.add_argument("--output", "-o", type=argparse.FileType("w"), help="Output file. Defaults to parsed_data/features_osm.json", default="./parsed_data/features_osm.json")

args = parser.parse_args()

# transform EPSG:4326 to EPSG:25832
transform_coords = Transformer.from_crs(CRS.from_epsg(4326), CRS.from_epsg(25832)).transform
def get_nodepos(lat, lon):
    x, y = transform_coords(lat, lon)
    return int(round(x)), int(round(y))


def print_element(msg, e):
    print(msg, f"{e['id']} {e['type']}[{','.join(k+'='+v for k,v in e.get('tags', {}).items())}]")


node_id_to_blockpos = {}

def node_ids_to_node_positions(node_ids):
    x_coords = []
    y_coords = []
    for node_id in node_ids:
        x, y = node_id_to_blockpos[node_id]
        x_coords.append(x)
        y_coords.append(y)
    return x_coords, y_coords


data = json.load(args.file)


min_x = None
max_x = None
min_y = None
max_y = None

def update_min_max(x_coords, y_coords):
    global min_x, max_x, min_y, max_y
    min_x = min(x_coords) if min_x is None else min(min_x, *x_coords)
    max_x = max(x_coords) if max_x is None else max(max_x, *x_coords)
    min_y = min(y_coords) if min_y is None else min(min_y, *y_coords)
    max_y = max(y_coords) if max_y is None else max(max_y, *y_coords)


highways = []
waterways = []
buildings = []
areas = []
barriers = []
nodes = []

# sort elements by type (highway, building, area or node)
for e in data["elements"]:
    t = e["type"]
    tags = e.get("tags")
    if t == "way":
        if not tags:
            print_element("Ignored, missing tags:", e)
            continue
        if "area" in tags:
            areas.append(e)
        elif "highway" in tags:
            highways.append(e)
        elif "waterway" in tags:
            waterways.append(e)
        elif "building" in tags or "building:part" in tags:
            buildings.append(e)
        elif "barrier" in tags:
            barriers.append(e)
        else:
            areas.append(e)
    elif t == "node":
        blockpos = get_nodepos(e["lat"], e["lon"])
        node_id_to_blockpos[e["id"]] = blockpos
        if tags and ("natural" in tags or "amenity" in tags or "barrier" in tags):
            nodes.append(e)
    else:
        print(f"Ignoring element with unknown type '{t}', element: {e}")


res_areas = {
    "low": [],
    "medium": [],
    "high": []
}
res_buildings = []
res_decorations = defaultdict(list)
res_highways = []
res_waterways = []

def get_surface(area):
    tags = area["tags"]
    # print_element("processing area:", area)
    surface = None
    res_area = None

    # SURFACE tag given and usable, hence we use it:
    if "surface" in tags and tags["surface"] in SURFACES:
        match tags["surface"]:
            case "natural" | "building_ground":
                return tags["surface"], "low"   
            case "residential_landuse" | "landuse" | "leisure" | "sports_centre" | "pitch" | "amenity" | "school":
                return tags["surface"], "medium"
            case "grass" | "asphalt" | "paving_stones" | "fine_gravel" | "concrete" | "dirt" | "highway" | "footway" | "cycleway" | "pedestrian" | "path" | "park" | "playground" | "parking" | "village_green" | "water":
                return tags["surface"], "high"
            case _:
                return tags["surface"], "low"   

    if "natural" in tags:
        if tags["natural"] == "water":
            return "water", "high"
        else:
            return "natural", "low"
    elif "amenity" in tags:
        if tags["amenity"] in SURFACES:
            return tags["amenity"], "medium"
        elif tags["amenity"] == "grave_yard":
            return "village_green", "medium"
        else:
            surface = "amenity" 
            res_area = "medium"
            # not returned yet: might be overriden by better match...
    elif "leisure" in tags:
        if tags["leisure"] in SURFACES:
            return tags["leisure"], "medium"
        elif tags["leisure"] == "swimming_pool":
            return "water", "high"
        else:
            surface = "leisure"
            res_area = "high"
            # not returned yet: might be overriden by better match...
    elif "landuse" in tags:
        if tags["landuse"] == "residential":
            return "residential_landuse", "low"  
        elif tags["landuse"] == "reservoir":
            return "water", "low"
        elif tags["landuse"] == "grass" or tags["landuse"] == "meadow" or tags["landuse"] == "forest":
            return "natural", "low"
        elif tags["landuse"] in SURFACES:
            return tags["landuse"], "low"
        else:
            surface = "landuse"
            res_area = "low"
            # not returned yet: might be overriden by better match...
    return surface, "low"


print("Processing AREAS...")
for area in areas:
    surface, level = get_surface(area)
    print(f"Area {area} ==> surface: {surface}, res_area level: {level}")

    if surface is None:
        print_element("Ignored, could not determine surface:", area)
        continue
    x_coords, y_coords = node_ids_to_node_positions(area["nodes"])
    update_min_max(x_coords, y_coords)
    res_areas[level].append({"x": x_coords, "y": y_coords, "surface": surface, "osm_id": area["id"]})

def add_building_height(building, tags):
    try:
        levels = int(tags["building:levels"])
    except (KeyError, ValueError):
        levels = None
    try:
        height = int(tags["building:height"].split(' m')[0])
    except (KeyError, ValueError):
        height = None
    else:
        height = min(height, 255)

    if height is not None:
        building["height"] = height
        return

    if levels is not None:
        building["levels"] = levels
        return

    if "building" in tags:
        match tags["building"]:
            case "yes" | "bungalow":
                building["levels"] = 1
                return
            case "church" | "mosque" | "synagogue" | "temple":
                building["levels"] = 4
                return
            case "cathedral ":
                building["levels"] = 5
                return
    if "tower:type" in tags:
        match tags["tower:type"]:
            case "bell_tower":
                building["levels"] = 9
                return
    return



print("Processing BUILDINGS...")
for building in buildings:
    x_coords, y_coords = node_ids_to_node_positions(building["nodes"])
    if len(x_coords) < 2:
        print_element(f"Ignored, only {len(x_coords)} nodes:", building)
    tags = building["tags"]
    material = None
    if "building:material" in tags:
        if tags["building:material"] == "brick":
            material = "brick"
        else:
            print_element("Unrecognized building:material", building)
    is_building_part = "building:part" in tags
    b = {"x": x_coords, "y": y_coords, "is_part": is_building_part}
    add_building_height(b, tags)
    if material is not None:
        b["material"] = material
    res_buildings.append(b)




print("Processing BARRIERS...")
for barrier in barriers:
    if barrier["tags"]["barrier"] in DECORATIONS:
        deco = barrier["tags"]["barrier"]
    else:
        deco = "barrier"
        print_element("Default barrier:", barrier)
    x_coords, y_coords = node_ids_to_node_positions(barrier["nodes"])
    update_min_max(x_coords, y_coords)
    res_decorations[deco].append({"x": x_coords, "y": y_coords})


print("Processing WATERWAYS...")
for waterway in waterways:
    tags = waterway["tags"]

    if "waterway" in tags:
        surface = "water"

    layer = tags.get("layer", 0)
    try:
        layer = int(layer)
    except ValueError:
        layer = 0

    x_coords, y_coords = node_ids_to_node_positions(waterway["nodes"])
    update_min_max(x_coords, y_coords)
    res_waterways.append({"x": x_coords, "y": y_coords, "surface": surface, "layer": layer, "osm_id": waterway["id"], "type": tags["waterway"]})


print("Processing HIGHWAYS...")
for highway in highways:
    tags = highway["tags"]

    if tags["highway"] in SURFACES:
        surface = tags["highway"]
    elif "surface" in tags and tags["surface"] in SURFACES:
        surface = tags["surface"]
    else:
        surface = "highway"
        print_element("Default highway:", highway)

    layer = tags.get("layer", 0)
    try:
        layer = int(layer)
    except ValueError:
        layer = 0
    if "tunnel" in tags and tags["tunnel"] != "building_passage":
        if "layer" in tags:
            try:
                layer = int(tags["layer"])
            except ValueError:
                layer = -1
            if layer > 0:
                layer = 0
        else:
            layer = -1

    x_coords, y_coords = node_ids_to_node_positions(highway["nodes"])
    update_min_max(x_coords, y_coords)
    res_highways.append({"x": x_coords, "y": y_coords, "surface": surface, "layer": layer, "osm_id": highway["id"], "type": tags["highway"]})


# NODES
for node in nodes:
    tags = node["tags"]
    id_ = None
    height = 1
    if "natural" in tags:
        if tags["natural"] in DECORATIONS:
            deco = tags["natural"]
        else:
            print_element("Unrecognized natural node:", node)
            continue
    elif "amenity" in tags and tags["amenity"] in DECORATIONS:
        deco = tags["amenity"]
    elif "barrier" in tags:
        if tags["barrier"] in DECORATIONS:
            deco = tags["barrier"]
        else:
            deco = "barrier"
            print_element("Default barrier:", node)
    else:
        print_element("Ignored, could not determine decoration type:", node)
        continue
    x, y = get_nodepos(node["lat"], node["lon"])
    update_min_max([x], [y])
    res_decorations[deco].append({"x": x, "y": y})

print(f"\nOutput dumped to: {args.output.name}\nfrom {min_x},{min_y} to {max_x},{max_y} (size: {max_x-min_x+1},{max_y-min_y+1})")

json.dump({
    "min_x": min_x,
    "max_x": max_x,
    "min_y": min_y,
    "max_y": max_y,
    "areas": res_areas,
    "buildings": res_buildings,
    "decorations": res_decorations,
    "highways": res_highways,
    "waterways": res_waterways
}, args.output, indent=2)
