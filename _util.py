import numpy as np


def to_bytes(x: int, length: int) -> bytes:
    x = [None, np.uint8, np.uint16, None, np.uint32][length](x)
    # func copied from https://github.com/Gael-de-Sailly/geo-mapgen/blob/4bacbe902e7c0283a24ee3efa35c283ad592e81c/database.py#L34
    res = x.newbyteorder("<").tobytes()
    assert len(res) == length
    return res


def from_bytes(b):
    return int.from_bytes(b, "little")



SURFACES = {
    # key: id, RGB Color for Minimap
    "default": [0, [255,239,213, 255]],

    "paving_stones": [1,[132,132,132, 255]],
    "fine_gravel": [2,[139,134,130, 255]],
    "concrete": [3,[183,183,183, 255]],
    "asphalt": [4, [40,40,40, 255]],
    "dirt": [5,[139,119,101, 255]],

    "highway": [10, [91,91,91, 255]],  # default
    "footway": [11, [139,137,137, 255]],
    "service": [12,[216,191,216, 255]],
    "cycleway": [13, [142,142,142, 255]],
    "pedestrian": [14,[255,181,197, 255]],
    "residential": [15,[205,104,137, 255]],
    "path": [16, [139,90,0, 255]],

    "leisure": [20,[255,165,0, 255]],  # default
    "park": [21, [46,139,87, 255]],
    "playground": [22,[238,64,0, 255]],
    "sports_centre": [23,[255,128,0, 255]],
    "pitch": [24,[238,64,0, 255]],

    "amenity": [30,[102,139,139, 255]] , # default
    "school": [31,[125,38,205, 255]],
    "parking": [32, [139,137,137, 255]],

    "landuse": [40,[139,76,57, 255]],  # default
    "residential_landuse": [41,[94,38,18, 255]],
    "village_green": [42, [0,238,118, 255]],

    "natural": [50,[48,128,20, 255]],  # default
    "water": [51, [99,184,255, 255]],

    "building_ground": [60, [238,233,233, 255]],

    "grass": [70, [0,205,102, 255]],
}

SURFACE_COLORS = {}

for s in SURFACES.values():
    SURFACE_COLORS[s[0]] = s[1]


DECORATIONS = {
    "none": 0,  # air

    "natural": 10,  # default
    "grass": 11,
    "tree": 12,
    "leaf_tree": 13,
    "conifer": 14,
    "bush": 15,

    # amenity
    "post_box": 21,
    "recycling": 22,
    "vending_machine": 23,
    "bench": 24,
    "telephone": 25,

    "barrier": 30,  # default
    "fence": 31,
    "wall": 32,
    "bollard": 33,
    "gate": 34,
    "hedge": 35
}



##### RELATIONS: ############

"""
The following dictionary declares which elements (parts of relations) are recognized as areas.
Keys are the tag names from OSM, values are sets of accepted tag values. If any value is ok, the 
set of values is left empty.
"""

tag_dict_area = {
    "natural": { "water", },
    "landuse": { "forest", "meadow", },
    "surface": { "grass", },
    "leisure": { "park", },
    "place": { "islet", },
}

area_tags = tag_dict_area.keys()

def is_area_relation(relation):
    try:
        tags = relation["tags"]
    except:
        return False

    for tag_name, tag_value in tags.items():
        if tag_name in area_tags:
            values = tag_dict_area.get(tag_name)
            # empty set means any tag value is accepted.
            if values == {} or tag_value in values: 
                return True
    return False


tag_dict_building = {
    "building": { }, # any building will be accepted
}

building_tags = tag_dict_building.keys()

def is_building_relation(relation):
    try:
        tags = relation["tags"]
    except:
        return false
        
    for tag_name, tag_value in tags.items():
        if tag_name in building_tags:
            values = tag_dict_building.get(tag_name)
            # empty set means any tag value is accepted.
            if values == {} or tag_value in values:
                return True
    return False

