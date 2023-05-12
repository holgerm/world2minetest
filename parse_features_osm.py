import argparse
import json
from collections import defaultdict

from pyproj import CRS, Transformer

from _util import SURFACES, DECORATIONS

import sys


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
    return f"no element with id {id} found"


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
            return "natural", "medium"
        elif tags["landuse"] in SURFACES:
            return tags["landuse"], "low"
        else:
            surface = "landuse"
            res_area = "low"
            # not returned yet: might be overriden by better match...
    elif "place" in tags:
        if tags["place"] == "islet":
            return "default", "low"
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
            return 3
        elif tags["building"] in ["school", "college", "train_station", "transportation", "barn"]:
            return 6
        elif tags["building"] in ["hospital", "university", "barn"]:
            return 9
        elif tags["building"] in ["church", "mosque", "synagogue", "temple", "government"]:
            return 12
        elif tags["building"] in ["cathedral"]:
            return 15
    if "tower:type" in tags:
        if tags["tower:type"] in ["bell_tower"]:
            return 27
    return 2


def rel_has_only_outer_ways(relation):
    for member in relation["members"]:
        if member["type"] != "way":
            return False

        try:
            role = member["role"]
        except:
            return False

        if role == "inner":
            return False
    return True


def split_relation_in_areas_and_holes(relation, list_for_outer_areas, list_for_inner_areas, list_of_areas):
    areaNr = 0
    areaNodes = []
    for member in relation["members"]:
        try:
            role = member["role"]
        except:
            continue

        if member["type"] == "way":
            if rel_has_only_outer_ways(relation):
                area_collection = list_of_areas
                if member['ref'] == 59683400:
                    sys.stderr.write("INNER 59683400 used as AREA.")
            elif role == "inner":
                if is_area_relation(member):
                    if member['ref'] == 59683400:
                        sys.stderr.write("INNER 59683400 LEFT OUT.")
                    continue # leave inner areas out when they are areas in their own right: they will be taken care of later
                else:
                    area_collection = list_for_inner_areas # an inner empty area
                    if member['ref'] == 59683400:
                        sys.stderr.write("INNER 59683400 used as INNER.")
            else: 
                area_collection = list_for_outer_areas
                if member['ref'] == 59683400:
                    sys.stderr.write("INNER 59683400 used as OUTER.")

            way = find_element(member.get('ref'))
            try:
                myNodes = way['nodes'].copy()
            except:
                continue

            nodesCount = len(myNodes)
            if len(areaNodes) == 0:
                print(f"xxx #0 Start ({nodesCount})")
                areaNodes = myNodes
            elif myNodes[-1] == areaNodes[0]: 
                # new way should sit in front of collected area
                myNodes.pop(-1)
                myNodes.extend(areaNodes)
                areaNodes = myNodes
                print(f"xxx #1 Prepend ({nodesCount} => {len(areaNodes)})")
            elif areaNodes[0] == myNodes[0]: 
                # new way has same head as collected area, hence we reverse it and prepend it
                reverseNodes = myNodes[len(myNodes):0:-1] # gets all but the first in reverse order
                reverseNodes.extend(areaNodes)
                areaNodes = reverseNodes
                print(f"xxx #2 Prepend reversed ({nodesCount}) => {len(areaNodes)}")
            elif areaNodes[-1] == myNodes[0]:
                # new way joins after collected area
                areaNodes.pop(-1)
                areaNodes.extend(myNodes)
                print(f"xxx #3 Extend ({nodesCount}) => {len(areaNodes)}")
            elif areaNodes[-1] == myNodes[-1]:
                # new way has same tail as collected area, hence we reverse it and extend it at end
                reverseNodes = myNodes[len(myNodes)-1::-1] # gets all but the last in reverse order
                areaNodes.extend(reverseNodes)
                print(f"xxx #4 Extend reversed ({nodesCount}) => {len(areaNodes)}")
            else:
                print(f"xxx WARNING: way {way['id']} does not fit in relation {relation['id']}, hence we ignore it.")

            # check if area is complete, i.e. path of nodes is closed:
            if role == "outer":
                areaTags = relation["tags"]
            else: 
                areaTags = { "empty_area" : "yes", }
            if areaNodes[0] == areaNodes[-1]:
                area_collection.append({
                    "id": f"{relation['id']}.{role}#{areaNr}",
                    "nodes": areaNodes,
                    "tags": areaTags,
                })
                print(f"xxx Relation {relation['id']}.{role}#{areaNr} COMPLETE and added to our areas with #{len(areaNodes)} nodes")
                areaNodes = []
                areaNr += 1
            else:
                print(f"xxx Relation {relation['id']} has #{len(areaNodes)} nodes but is still incomplete, hence we keep collecting parts ...")

    return



###################################################### START ACTION: #########################

outer_areas = []
inner_empty_areas = [] # aka holes
areas = [] # normal areas made up from ways
highways = []
waterways = []
buildings = []
barriers = []
nodes = []

from _util import is_area_relation, is_building_relation

# sort elements by type (highway, building, area or node)
for e in data["elements"]:
    t = e["type"]
    tags = e.get("tags")
    if tags and "boundary" in tags.keys():
        continue # ignore boundaries
    if t == "node":
        blockpos = get_nodepos(e["lat"], e["lon"])
        node_id_to_blockpos[e["id"]] = blockpos
        if tags and ("natural" in tags or "amenity" in tags or "barrier" in tags):
            nodes.append(e)
            continue
    elif t == "relation" or t == "multipolygon":
        if not tags:
            print_element(f"Ignored relation {e.get('id')}, missing tags:", e)
            continue
        members = e.get("members")
        if not members:
            print_element(f"Ignored relation {e.get('id')}, missing members:", e)
            continue
        if is_area_relation(e):
            print(f"Area from relation added. ID: {e.get('id')}")
            split_relation_in_areas_and_holes(e, outer_areas, inner_empty_areas, areas)
            continue
        elif is_building_relation(e):
            print(f"Building from relation added. ID: {e.get('id')}")
            split_relation_in_areas_and_holes(e, buildings, buildings, buildings)
            continue
    elif t == "way":
        if not tags:
            print_element("Ignored, missing tags:", e)
            continue
        elif "area" in tags:
            areas.append(e)
            continue
        elif "highway" in tags:
            highways.append(e)
            continue
        elif "waterway" in tags:
            if tags['waterway'] in { "ditch", "drain", "stream"}:
                waterways.append(e)
            continue
        elif "building" in tags or "building:part" in tags:
            buildings.append(e)
            continue
        elif "barrier" in tags:
            barriers.append(e)
            continue
        else:
            areas.append(e)
            continue
    else:
        print(f"Ignoring element {e.get('id')} with unknown type {t}")
        continue


res_areas = {
    "outer": [],
    "inner": [],
    "low": [],
    "medium": [],
    "high": [],
}
res_buildings = []
res_decorations = defaultdict(list)
res_highways = []
res_waterways = []

############# PHASE 2: ##############


print("Processing OUTER_AREAS...")
for area in outer_areas:
    surface, level = get_surface(area)
    level = "outer"

    if surface is None:
        print_element("Ignored, could not determine surface:", area)
        continue

    x_coords, y_coords = node_ids_to_node_positions(area["nodes"])
    update_min_max(x_coords, y_coords)
    res_areas[level].append({"x": x_coords, "y": y_coords, "surface": surface, "osm_id": area["id"]}) # TODO add holes (inner elements)
    print(f"Added outer area to res_area #{area['id']} surface: {surface}, level: {level}")

print("Processing INNER EMPTY AREAS ...")
for hole in inner_empty_areas:
    surface = "default"
    level = "inner"

    try:
        myNodes = hole["nodes"]
    except:
        continue

    x_coords, y_coords = node_ids_to_node_positions(hole["nodes"])
    update_min_max(x_coords, y_coords)
    res_areas[level].append({"x": x_coords, "y": y_coords, "surface": surface, "osm_id": hole["id"]}) # TODO add holes (inner elements)
    print(f"Added hole to res_area #{hole['id']} surface: {surface}, level: {level}, now we have {len(res_areas['inner'])} inner areas.")


print("Processing AREAS...")
for area in areas:
    surface, level = get_surface(area)

    if surface is None:
        print_element("Ignored, could not determine surface:", area)
        continue

    x_coords, y_coords = node_ids_to_node_positions(area["nodes"])
    update_min_max(x_coords, y_coords)
    res_areas[level].append({"x": x_coords, "y": y_coords, "surface": surface, "osm_id": area["id"]}) # TODO add holes (inner elements)
    print(f"Added res_area #{area['id']} surface: {surface}, level: {level}")

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

size_x = max_x-min_x+1
size_y = max_y-min_y+1
print(f"\nOutput dumped to: {args.output.name}\nfrom {min_x},{min_y} to {max_x},{max_y}: (size: {size_x},{size_y})")

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
