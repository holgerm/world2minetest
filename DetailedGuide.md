
The Detailed Guide - Step by step
==========
Generating a Minetest world consists of the following 4 steps. At least one of steps 1-3 is required.

 1. Generate a heightmap.
 2. Use OpenStreetMap data to add details.
 3. Add decoration (trees, bushes) using .dxf data.
 4. Create a `map.dat` file that can be read by world2minetest Mod for Minetest.


## Generating a heightmap
A heightmap can be generated using the `parse_heightmap_xyz.py` script (see `python3 parse_heightmap_xyz.py -h` for details).
First, download ASCII XYZ files and save them to the `data_sources/` directory.

For Hanover (Germany), you can use [this link](https://www.hannover.de/Leben-in-der-Region-Hannover/Verwaltungen-Kommunen/Die-Verwaltung-der-Landeshauptstadt-Hannover/Dezernate-und-Fachbereiche-der-LHH/Stadtentwicklung-und-Bauen/Fachbereich-Planen-und-Stadtentwicklung/Geoinformation/Open-GeoData/3D-Stadtmodell-und-Gel%C3%A4ndemodell/Digitales-Gel%C3%A4ndemodell-DGM1).

Then, run `parse_heightmap_xyz.py` with any files you want to convert into a heightmap:
```
$ python3 parse_heightmap_xyz.py data_sources/path/to/file1.xyz data_sources/path/to/file2.xyz ...
```
This will create a new file `parsed_data/heightmap.dat`.


## Use OpenStreetMap data
Select data using the [Overpass API](https://overpass-turbo.eu/). 
Here is an example query:
```
[out:json][timeout:25][bbox:{{bbox}}];
(
   way;
   node;
);
out body;
>;
out skel qt;
```

Copy the JSON data from the "Data" tab into a new file `data_sources/osm.json`.
Then, parse this data using `parse_features_osm.py` (see `python3 parse_features_osm.py -h` for details).
```
$ python3 parse_features_osm.py data_sources/osm.json
```
This will create a new file `parsed_data/features_osm.json`.


## Add decoration from .dxf files
For geodata saved in .dxf files, `parse_features_dxf.py` can be used (see `python3 parse_features_dxf.py -h` for details).
Currently, only trees and bushes are supported.

First, download .dxf files and save them to the `data_sources/` directory.

For Hanover (Germany), you can use [this link](https://www.hannover.de/Leben-in-der-Region-Hannover/Verwaltungen-Kommunen/Die-Verwaltung-der-Landeshauptstadt-Hannover/Dezernate-und-Fachbereiche-der-LHH/Stadtentwicklung-und-Bauen/Fachbereich-Planen-und-Stadtentwicklung/Geoinformation/Open-GeoData/Digitale-Stadtkarten/Stadtkarte-1-1000-SKH1000).

Then, run `parse_features_dxf.py` with any files you want to use.
For each decoration, you will want to specify a query for [ezdxf](https://ezdxf.readthedocs.io/en/stable/tutorials/getting_data.html#retrieve-entities-by-query-language) to get all entities representing that decoration. Currently, decorations `tree`, `leaf_tree`, `conifer`, and `bush` are available.
Example command (for Hanover's data):
```
$ python3 parse_features_dxf.py data_sources/path/to/file1.dxf data_sources/path/to/file2.dxf ... \
    --query "*[layer=='Eingemessene Bäume' & name=='S220.40']" "tree" \
    --query "*[layer=='Nutzung_ Bewuchs_ Boden' & name=='S220.41']" "leaf_tree" \
    --query "*[layer=='Nutzung_ Bewuchs_ Boden' & name=='S220.43']" "conifer" \
    --query "*[layer=='Nutzung_ Bewuchs_ Boden' & name=='S220.46']" "bush"
```
This will create a new file `parsed_data/features_dxf.json`.


## Detailed buildings with CityGML/CityJSON
CityJSON containing buildings can be used instead of buildings data from OpenStreetMap, for a higher level of detail.

If you have CityGML files, these need to be converted to CityJSON first. This can be done with [citygml-tools](https://github.com/citygml4j/citygml-tools):
```
$ ./citygml-tools to-cityjson --pretty-print data_sources/path/to/directory/with/citygml/files/
```

To obtain CityGML files for Hanover (Germany), you can use [this link](https://www.hannover.de/Leben-in-der-Region-Hannover/Verwaltungen-Kommunen/Die-Verwaltung-der-Landeshauptstadt-Hannover/Dezernate-und-Fachbereiche-der-LHH/Stadtentwicklung-und-Bauen/Fachbereich-Planen-und-Stadtentwicklung/Geoinformation/Open-GeoData/3D-Stadtmodell-und-Gel%C3%A4ndemodell/Digitales-3D-Stadtmodell).

Run `parse_cityjson.py` with any files you want to use:
```
$ python3 parse_cityjson.py data_sources/path/to/file1.json data_sources/path/to/file2.json ...
```
This will create a new file `parsed_data/buildings_cityjson.dat`.


## Putting it all together – creating `map.dat`
See `python3 generate_map.py -h` for details.
Example usage:
```
$ python3 generate_map.py \
    --heightmap=parsed_data/heightmap.dat \
    --features=parsed_data/features_osm.json \
    --features=parsed_data/features_dxf.json \
    --buildings=parsed_data/buildings_cityjson.dat
```
This will save a file `map.dat` to the world2minetest folder, which contains the Mod for Minetest.
Copy this folder to your Minetest installation's `mods/` directory (or create a symlink for convenience).<br>
To generate the map into a world, create a new world in Minetest and, *before playing it for the first time*, activate the `world2minetest` Mod.



Screenshots
===========
![](docs/screenshot_water.png)
![](docs/screenshot_trees_with_postboxes_and_buildings.png)
![](docs/screenshot_bench.png)
![](docs/screenshot_fence.png)
![](docs/screenshot_primary_road.png)
![](docs/screenshot_hochhaus_fog.png)
