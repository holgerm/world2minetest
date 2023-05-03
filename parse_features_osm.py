import argparse
import json
from collections import defaultdict

from pyproj import CRS, Transformer

from _util import SURFACES, DECORATIONS


parser = argparse.ArgumentParser(description="Parse OSM data")
parser.add_argument("file", type=argparse.FileType("r", encoding="utf-8"), help="GeoJSON file with OSM data")
parser.add_argument("--output", "-o", type=argparse.FileType("w"), help="Output file. Defaults to parsed_data/features_osm.json", default="./parsed_data/features_osm.json")

args = parser.parse_args()

# TODO OPTIMIZE: create (once) and use (often) hashmap! Check for doubles during creation. 
# Maybe we can even optimize the osm.json data export by smarter use of the query language.
def find_element(id):
    for e in data["elements"]:
        try:
            if e["id"] == id:
                return e
        except:
            continue



def print_element(msg, e):
    print(msg, f"{e.get('id', 0)} {e.get('type', 'undefined')}[{','.join(k+'='+v for k,v in e.get('tags', {}).items())}]")


transform_coords = Transformer.from_crs(CRS.from_epsg(4326), CRS.from_epsg(25832)).transform
def get_nodepos(lat, lon):
    x, y = transform_coords(lat, lon)
    return int(round(x)), int(round(y))


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

def get_surface(area):
    tags = area["tags"]
    # print_element("processing area:", area)
    surface = None
    res_area = None

    # SURFACE tag given and usable, hence we use it:
    if "surface" in tags and tags["surface"] in SURFACES:
        if tags["surface"] in ["natural", "building_ground"] :
            return tags["surface"], "low"   
        elif tags["surface"] in ["residential_landuse", "landuse", "leisure", "sports_centre", "pitch", "amenity", "school"]:
            return tags["surface"], "medium"
        elif tags["surface"] in ["grass", "asphalt", "paving_stones", "fine_gravel", "concrete", "dirt", "highway", "footway", "cycleway", "pedestrian", "path", "park", "playground", "parking", "village_green", "water"]:
            return tags["surface"], "high"
        else:
            return tags["surface"], "low"   

    if "natural" in tags:
        if tags["natural"] == "water":
            return "water", "medium"
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

def building_height(tags):
    # is only called when there was no "height" tag.
    try:
        levels = int(tags["building:levels"])
    except (KeyError, ValueError):
        levels = 0
    
    try:
        roof_levels = int(tags["roof:levels"])
    except (KeyError, ValueError):
        roof_levels = 0

    levels += roof_levels
    if levels > 0:
        return 3 * levels

    # we have no levels, since we guess height by type of building:

    if "building" in tags:
        if tags["building"] in ["yes", "bungalow", "toilets"]:
            return 1
        elif tags["building"] in ["school", "college", "train_station", "transportation", "barn"]:
            return 2
        elif tags["building"] in ["hospital", "university", "barn"]:
            return 3
        elif tags["building"] in ["church", "mosque", "synagogue", "temple", "government"]:
            return 4
        elif tags["building"] in ["cathedral"]:
            return 5
    if "tower:type" in tags:
        if tags["tower:type"] in ["bell_tower"]:
            return 9
    return 1

def outer_element_nodes_of_relation(element):
    outerAreas = []
    outerAreaNodes = []
    for member in element.get("members"):
        if member.get("type") == "way" and member.get("role") == "outer":
            way = find_element(member.get('ref'))
            myNodes = way.get('nodes').copy()
            if myNodes != None:
                if len(outerAreaNodes) == 0:
                    outerAreaNodes = myNodes
                elif myNodes[-1] == outerAreaNodes[0]: 
                    # new way should sit in front of collected area
                    myNodes.pop(-1)
                    myNodes.extend(outerAreaNodes)
                    outerAreaNodes = myNodes
                elif outerAreaNodes[0] == myNodes[0]: 
                    # new way has same head as collected area, hence we reverse it and prepend it
                    reverseNodes = myNodes[3:0:-1] # gets all but the first in reverse order
                    reverseNodes.extend(outerAreaNodes)
                    outerAreaNodes = reverseNodes
                elif outerAreaNodes[-1] == myNodes[0]:
                    # new way joins after collected area
                    outerAreaNodes.pop(-1)
                    outerAreaNodes.extend(myNodes)
                elif outerAreaNodes[-1] == myNodes[-1]:
                    # new way has same tail as collected area, hence we reverse it and extend it at end
                    reverseNodes = myNodes[2::-1] # gets all but the last in reverse order
                    outerAreaNodes.extend(reverseNodes)
                else:
                    print(f"WARNING: way {way['id']} does not fit in relation {element['id']}, hence we ignore it.")

                # check if area is complete, i.e. path is closed:
                if outerAreaNodes[0] == outerAreaNodes[-1]:
                    outerAreas.append(outerAreaNodes)
                    outerAreaNodes = []
                else:
                    print(f"WARNING: relation {element['id']} remains INCOMPLETE, hence we ignore it.")

    return outerAreas


def append_elements_for_relation(collection, tag_key, tag_value):
    # create the outer areas by collecting (area, building etc.) the nodes of all outer ways:
    for outerNr, outerArea in enumerate(outer_element_nodes_of_relation(e)):
        collection.append({
            "id": f"{e.get('id')}.outer#{outerNr+1}",
            "nodes": outerArea,
            "tags": {
                tag_key: tag_value,
            }
        })


###################################################### START ACTION: #########################


highways = []
waterways = []
buildings = []
areas = []
barriers = []
nodes = []

from _util import is_area_relation, is_building_relation

# sort elements by type (highway, building, area or node)
for e in data["elements"]:
    t = e["type"]
    tags = e.get("tags")
    if tags and "boundary" in tags.keys():
        continue # ignore boundaries
    if t == "relation" or t == "multipolygon":
        if not tags:
            print_element(f"Ignored relation {e.get('id')}, missing tags:", e)
            continue
        for tname, tvalue in tags.items():
            if e['id'] == 6306415:
                print(f"Element from relation found 6306415. tname: {tname}, tvalue: {tvalue}")
            if is_area_relation(tname, tvalue):
                print(f"Area from relation added. ID: {e.get('id')}")
                append_elements_for_relation(areas, tname, tvalue)
                break # we only use one tag / value
            elif is_building_relation(tname, tvalue):
                print(f"Building from relation added. ID: {e.get('id')}")
                append_elements_for_relation(buildings, tname, tvalue)
                break # we only use one tag / value
    elif t == "way":
        if not tags:
            print_element("Ignored, missing tags:", e)
            continue
        if "boundary" in tags:
            continue # ignore boundaries
        elif "area" in tags:
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
        print(f"Ignoring element {e.get('id')} with unknown type {t}")


res_areas = {
    "low": [],
    "medium": [],
    "high": []
}
res_buildings = []
res_decorations = defaultdict(list)
res_highways = []
res_waterways = []

print("Processing AREAS...")
for area in areas:
    surface, level = get_surface(area)

    if surface is None:
        print_element("Ignored, could not determine surface:", area)
        continue

    x_coords, y_coords = node_ids_to_node_positions(area["nodes"])
    update_min_max(x_coords, y_coords)
    res_areas[level].append({"x": x_coords, "y": y_coords, "surface": surface, "osm_id": area["id"]})

print("Processing BUILDINGS...")
for building in buildings:
    if building['id'] == "1607046":
        print(f"Building from relation: 1607046 in buildings.")
    x_coords, y_coords = node_ids_to_node_positions(building["nodes"])
    if len(x_coords) < 2:
        print_element(f"Ignored, only {len(x_coords)} nodes:", building)
        continue
    tags = building["tags"]
    material = None
    if "building:material" in tags:
        if tags["building:material"] == "brick":
            material = "brick"
        else:
            print_element("Unrecognized building:material", building)
    is_building_part = "building:part" in tags
    b = {"x": x_coords, "y": y_coords, "is_part": is_building_part, "osm_id": building.get("id")}
    try:
        height = int(tags["building:height"].split(' m')[0])
    except:
        height = building_height(tags)
    else:
        height = min(height, 255)
    finally:
        b["height"] = height
    
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
