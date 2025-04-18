import argparse
import datetime
import os
import re
import sys
#import yaml

import unicodedata
from pyproj import CRS, Transformer

def get_args():
	parser = argparse.ArgumentParser(description="Create a minetest world based on openstreetmap data.")
	parser.add_argument('-p', '--project', help="Project name")
	parser.add_argument('-w', '--worldname', help="World name used in world.mt file")
	parser.add_argument('-d', '--minetest_dir', help="Minetest runtime directory")
	parser.add_argument('-g', '--gameid', default="minetest", help="Game Id (default: minetest)")
	parser.add_argument('-b', '--backend', default="sqlite3", help="BackEnd Database (sqlite3, leveldb)")
	parser.add_argument('-v', '--verbose', action='store_true', help="Log to console addionally to logfile.")
	parser.add_argument('-m', '--minimap', action='store_true', help="Create a minimap.png showing one rgb pixel per block surface of the generated world.")
	parser.add_argument('-q', '--query', type=argparse.FileType("r", encoding="utf-8"), nargs='?', const='project_query', help="File containing a query with Overpass QL, cf. 'https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL'")
	parser.add_argument('-r', '--reuse_query', action='store_true', help="Reuse project-specific query file.")
	parser.add_argument('-a', '--area', type=ascii, help="Decimal coordinates of two opposite corners of desired area, separated by commas: 'lat_1, long_1, lat_2, long_2'")
	parser.add_argument('-u', '--unrestricted', action='store_true', help="Unrestrcited area, i.e. all data reaching beyond area boundary is included and stretches the area")
	parser.add_argument('-s', '--start', action='store_true', help="Starts the world after creating it in server mode.")
	return parser.parse_args()

# log to console and/or file, depending on verbose flag:
def log(message):
	now = datetime.datetime.now()
	if args.verbose:
		print(f"[w2mt]: {args.project}: {message}")
	# append to logfile:
	with open(log_file, "a") as logfile:
		logfile.write(f"{now} {args.project}: {message}\n")

# convert text to valid filename:
def slugify(text):
	text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
	text = re.sub(r'[^\w\s-]', '', text.lower())
	return re.sub(r'[-\s]+', '-', text).strip('-_')

def check_project_dir():
	# create missing projects dir:
	if not os.path.isdir(project_path):
		log(f"Project dir '{project_path}‘ missing, trying to create it ...")
		os.makedirs(project_path)
		if os.path.isdir(project_path):
			log(f"Project dir '{project_path}‘ created")
		else:
			log(f"Unable to create project dir '{project_path}‘! Check rights!")
			sys.exit("Unable to create missing project dir.")

def prepare_query_file():
	query_string = ""
	if args.reuse_query:
		try:
			with open(query_path, 'r') as file:
				query_string = file.read()
			if not query_string:
				sys.exit(f"Could not reuse query file: could not open the file '{query_path}'")
		except Exception as exc:
				sys.exit(f"While trying to open the query file '{query_path}' this exception was thrown: {exc}")

		import re
		e = re.compile(r'\s*\[\s*bbox:\s*(\d*\.?\d*\s*,\s*\d*\.?\d*\s*,\s*\d*\.?\d*\s*,\s*\d*\.?\d*)\s*\]\s*')
		match = e.search(query_string)
		args.area = match.group(1)
	
	if args.area:
		# Extract and potentially correct the corners of the area as coordinates:
		stripped = args.area.strip().replace(" ", "").replace("'", "").replace("\"", "")
		corners = stripped.split(",")
		north = max(float(corners[0]), float(corners[2]))
		south = min(float(corners[0]), float(corners[2]))
		west = min(float(corners[1]), float(corners[3]))
		east = max(float(corners[1]), float(corners[3]))
		if (east - west > 180.0):
			tmp = east
			east = west
			west = tmp
		# copy the template query file in place and open it
		query_string = query_template.format(south, west, north, east)
	elif args.query:
		with open(args.query, 'r') as file:
			query_string = file.read()
			log(f"Used query file {args.query}")
	else:
		log(f"Neither query file specified (-q), nor reusing project query file (-r), nor area given (-a). E.g. '52.524023988954376, 13.390914318783942, 52.51004666633488, 13.415739884736942', i.e. South, West, North, East. You can copy these coordinates from google maps for convenience.")
		sys.exit("Area not specified.")

	if args.reuse_query:
		log(f"Query will be reused with S: {south}, W: {west}, N: {north}, E: {east}")
	else:
		try:
			# Write the file:
			with open(query_path, 'w') as file:
				file.write(query_string)
			log(f"Query file generated with S: {south}, W: {west}, N: {north}, E: {east}")
		except Exception as exc:
			sys.exit(f"While trying to write query file '{query_path}' this exception was thrown: {exc}")

	transform_coords = Transformer.from_crs(CRS.from_epsg(4326), CRS.from_epsg(25832)).transform
	x, y = transform_coords(south, west)
	minX, minY = int(round(x)), int(round(y))
	x, y = transform_coords(north, east)
	maxX, maxY = int(round(x)), int(round(y))
	log(f"Area restriction corners: {minX}, {maxX} -> {minY}, {maxY} - size: {maxX - minX}, {maxY - minY}")
	return minX, minY, maxX, maxY

def perform_query():
	# do the query and store the result in osm.json file:
	cmd = f'wget -q -O {osm_path} --post-file={query_path} "https://overpass-api.de/api/interpreter" >> {log_file}'
	log(f"Performing query: '{cmd}' ...")
	error = os.system(cmd)
	if error:
		log("... error!")
	else:
		log("... done")

# def extract_features_from_osm_json():
# 	cmd = f'python3 parse_features_osm.py {osm_path} -o {feature_path} >> {log_file}'
# 	log(f"Extracting features using this command: '{cmd}' ...")
# 	error = os.system(cmd)
# 	if error:
# 		log("... error!")
# 	else:
# 		log("... done")
		
import subprocess

def extract_features_from_osm_json():
	log(f"Extracting features from {osm_path} to {feature_path} ...")

	# Baue das Kommando als Liste
	cmd = [
		"python3", "parse_features_osm.py",
		osm_path,
		"-o", feature_path
	]

	# Rufe das Kommando auf und schreibe stdout + stderr ins Logfile
	try:
		with open(log_file, "a") as logf:
			result = subprocess.run(cmd, stdout=logf, stderr=logf, check=True)
		log("... done")
	except subprocess.CalledProcessError as e:
		log(f"... error! Exit code: {e.returncode}")
		log(f"❌ Fehler beim Ausführen von: {' '.join(cmd)}")

# def generate_map_from_features(minX, minY, maxX, maxY):
# 	map_output_dir = os.path.join(project_path, "world2minetest")
# 	if not os.path.isdir(map_output_dir):
# 		os.makedirs(map_output_dir)
# 	if os.path.isdir(map_output_dir):
# 		log(f"Project w2mt mod dir '{map_output_dir}‘ created")
# 	else:
# 		log(f"Unable to create project w2mt mod dir '{map_output_dir}‘! Check rights!")
# 		sys.exit("Unable to create missing project w2mt mod dir.")
# 	map_output_path = os.path.join(map_output_dir, "map.dat")
# 	cmd = f'python3 generate_map.py --features {feature_path} --output {map_output_path}'
# 	if not args.unrestricted:
# 		cmd += f' --minx {minX} --maxx {maxX} --miny {minY} --maxy {maxY}'
# 	if args.minimap:
# 		cmd += ' --minimap'
# 	cmd += f' >> {log_file}'
# 	log(f"Generating map using this command: '{cmd}' ...")
# 	error = os.system(cmd)
# 	if error:
# 		log("... error!")
# 	else:
# 		log("... done")

def generate_map_from_features(minX, minY, maxX, maxY):
	map_output_dir = os.path.join(project_path, "world2minetest")
	if not os.path.isdir(map_output_dir):
		os.makedirs(map_output_dir)
	if os.path.isdir(map_output_dir):
		log(f"Project w2mt mod dir '{map_output_dir}' created")
	else:
		log(f"Unable to create project w2mt mod dir '{map_output_dir}'! Check rights!")
		sys.exit("Unable to create missing project w2mt mod dir.")

	map_output_path = os.path.join(map_output_dir, "map.dat")

	# Baue Kommando als Liste (ohne Shell!)
	cmd = [
		"python3", "generate_map.py",
		"--features", feature_path,
		"--output", map_output_path
	]

	if not args.unrestricted:
		cmd += ["--minx", str(minX), "--maxx", str(maxX), "--miny", str(minY), "--maxy", str(maxY)]
	if args.minimap:
		cmd.append("--minimap")

	print(f"Generating map using this command: {' '.join(cmd)} ...")

	# Rufe subprocess ohne Shell auf und leite Output ins Logfile
	with open(log_file, "a") as logf:
		result = subprocess.run(cmd, stdout=logf, stderr=logf)

	if result.returncode != 0:
		log("... error!")
	else:
		log("... done")

def create_mod():
	# check runtime mods dir:
	if not os.path.isdir(w2mt_mod_path):
		os.makedirs(w2mt_mod_path)
		if os.path.isdir(w2mt_mod_path):
			log("Directory for world2minetest mod in minetest home did not exist, hence we created it.")
		else:
			log("Failed to create directory for world2minetest mod in minetest home. Do we have enough rights?")
			return
	#
	# copy init.lua to runtime place:
	cmd = f"cp world2minetest/init.lua \"{w2mt_mod_path}\"/"
	os.system(cmd)
	log("Copied init.lua file to mods folder in minetest home (runtime location).")
	cmd = f"cp world2minetest/mod.conf \"{w2mt_mod_path}\"/"
	os.system(cmd)
	log("Copied mod.conf file to mods folder in minetest home (runtime location).")


def copy_mod_in_project_dir():
	# check runtime worlds dir:
	w2mt_mod_dir = os.path.join(project_path, "world2minetest")
	if not os.path.isdir(w2mt_mod_dir):
		os.makedirs(w2mt_mod_dir)
		if os.path.isdir(w2mt_mod_dir):
			log("Directory for world2minetest mod in minetest home did not exist, hence we created it.")
		else:
			log("Failed to create directory for world2minetest mod in minetest home.")
			return
	#
	# copy init.lua to runtime place:
	cmd = f"cp world2minetest/init.lua \"{w2mt_mod_dir}\"/"
	os.system(cmd)
	log("Copied init.lua file to mods folder for world2minetest in minetest home (runtime location).")
	#
	# copy map.dat to runtime place:
	# cmd = f"cp world2minetest/map.dat \"{w2mt_mod_dir}\"/"
	# os.system(cmd)
	# log("Copied map.dat file to mods folder for world2minetest in minetest home (runtime location).")
	#
	# copy mod.conf to runtime place:
	cmd = f"cp world2minetest/mod.conf \"{w2mt_mod_dir}\"/"
	error = os.system(cmd)
	if error:
		log("Error! Could not copy mod.conf file to mods folder for world2minetest in minetest home (runtime location).")
	else:
		log("Copied mod.conf file to mods folder for world2minetest in minetest home (runtime location).")


def define_world_for_project():
	# define world for this project:
	world_mt_string = world_mt_template.format(args.backend, args.gameid, args.worldname)
	# Write the file:
	world_file = os.path.join(project_path, "world.mt").replace("\"", "")
	with open(world_file, 'w') as file:
		file.write(world_mt_string)
	log(f"world.mt file generated: {world_file}.")


def start_world():
	cmd = f"minetest --server --worldname {args.worldname}"
	error = os.system(cmd)
	if error:
		log(f"Could not start world {args.worldname}.")



		

######### SCRIPT EXECUTION STARTS HERE: ##############
		
def main():

	global VERSION
	VERSION = "2025-03-28-01"

	global query_template
	query_template = """[bbox: {}, {}, {}, {}]
	[out:json]
	[timeout:25]
	;
	(
		way;
		node;
		relation;
	);
	out body;
	>;
	out skel qt;"""

	global world_mt_template
	world_mt_template = """enable_damage = false
	creative_mode = true
	mod_storage_backend = sqlite3
	auth_backend = sqlite3
	backend = {}
	player_backend = sqlite3
	gameid = {}
	world_name = {}
	server_announce = false

	load_mod_travelnet = true

	load_mod_worldeditadditions_commands = true
	load_mod_worldeditadditions = true
	load_mod_worldedit = true
	load_mod_we_undo = true
	load_mod_worldedit_gui = true
	load_mod_worldedit_shortcommands = true
	load_mod_worldeditadditions_farwand = true
	load_mod_worldedit_commands = true
	load_mod_worldeditadditions_core = true
	load_mod_worldedit_brush = true

	load_mod_nature_classic = true
	load_mod_skybox = true
	load_mod_beautiflowers = true
	load_mod_unifieddyes = true
	load_mod_skinsdb = true
	load_mod_building_blocks = true
	load_mod_font_api = true
	load_mod_display_api = true
	load_mod_signs_api = false
	load_mod_basic_materials = true
	load_mod_signs_road = false
	load_mod_boards = false
	load_mod_unified_inventory = true
	load_mod_edutest_chatcommands = true
	load_mod_edutest = true

	load_mod_homedecor_windows_and_treatments = true
	load_mod_homedecor_trash_cans = true
	load_mod_homedecor_roofing = true
	load_mod_homedecor_pictures_and_paintings = true
	load_mod_homedecor_office = true
	load_mod_homedecor_laundry = true
	load_mod_homedecor_gastronomy = true
	load_mod_homedecor_furniture = true
	load_mod_homedecor_fences = true
	load_mod_homedecor_kitchen = true
	load_mod_homedecor_electronics = true
	load_mod_homedecor_electrical = true
	load_mod_homedecor_doors_and_gates = true
	load_mod_homedecor_furniture_medieval = true
	load_mod_homedecor_common = true
	load_mod_homedecor_cobweb = true
	load_mod_homedecor_climate_control = true
	load_mod_homedecor_books = true
	load_mod_homedecor_bedroom = true
	load_mod_homedecor_bathroom = true
	load_mod_homedecor_tables = true
	load_mod_homedecor_seating = true
	load_mod_homedecor_lighting = true
	load_mod_homedecor_clocks = true
	load_mod_homedecor_exterior = true
	load_mod_homedecor_3d_extras = true
	load_mod_homedecor_wardrobe = true
	load_mod_homedecor_misc = true
	load_mod_homedecor_foyer = true

	load_mod_morelights = true
	load_mod_morebricks = true
	load_mod_moreblocks = true
	load_mod_pickblock = true
	load_mod_colordcement = true
	load_mod_colored_concrete = true

	load_mod_mesecons = true
	load_mod_mesecons_delayer = true
	load_mod_mesecons_materials = true
	load_mod_mesecons_lightstone = true
	load_mod_mesecons_button = true
	load_mod_mesecons_commandblock = true
	load_mod_mesecons_detector = true
	load_mod_mesecons_doors = true
	load_mod_mesecons_noteblock = true
	load_mod_mesecons_lamp = true
	load_mod_mesecons_microcontroller = true
	load_mod_mesecons_mvps = true
	load_mod_mesecons_torch = true
	load_mod_mesecons_switch = true
	load_mod_mesecons_wires = true
	load_mod_mesecons_pressureplates = true
	load_mod_mesecons_receiver = true
	load_mod_mesecons_pistons = true
	load_mod_mesecons_gamecompat = true
	load_mod_mesecons_walllever = true
	load_mod_mesecons_extrawires = true

	load_mod_world2minetest = true"""

	global args
	args = get_args()

	# first log starts with the call to this script with all arguments as given:
	global log_file
	log_file = "w2mt.log"
	if os.path.exists(log_file):
		os.remove(log_file)
	call_string=""
	for arg in sys.argv:
		call_string += str(arg) + " "
	log("Starting w2mt.py in version " + VERSION)
	log(call_string)

	# check mandatory options:
	if not args.project:
		sys.exit("Projectname is mandatory, use -p or --project followed by projectname.")
	else:
		args.project = slugify(args.project)

	# setup worldname:
	if not args.worldname:
		args.worldname = args.project

	# setup paths:
	if not args.minetest_dir:
		if os.environ["MINETEST_GAME_PATH"]:
			args.minetest_dir = os.environ["MINETEST_GAME_PATH"]
		else:
			args.minetest_dir = os.path.join(os.getcwd(), 'copy_content_to_minetest_dir')
			log("Neither environment variable MINETEST_GAME_PATH is set nor argument -d is given. Hence we create a local temporary directory in replacement.")
	global w2mt_mod_path
	w2mt_mod_path = os.path.join(args.minetest_dir, "mods", "world2minetest")

	global project_path
	project_path = os.path.join(args.minetest_dir, "worlds", args.project)
	query_file = "query.osm";
	global query_path
	query_path = os.path.join(project_path, query_file)

	global osm_path
	osm_path = os.path.join(project_path, "osm.json")
	feature_file = "features_osm.json"
	global feature_path
	feature_path = os.path.join(project_path, feature_file)

	check_project_dir()
	global minX, minY, maxX, maxY
	minX, minY, maxX, maxY = prepare_query_file()
	if not args.reuse_query:
		perform_query()
	extract_features_from_osm_json()
	generate_map_from_features(minX, minY, maxX, maxY)
	if "MINETEST_GAME_PATH" in os.environ:
		create_mod()
		copy_mod_in_project_dir()
		define_world_for_project()
	else:
		log("Environment variable MINETEST_GAME_PATH not set. In order to manage w2mt mod and worlds you need to set it to the minetest home dir which should contain 'mods' and 'worlds' folders.")

	if args.start:
		start_world()



if __name__ == "__main__":
    main()