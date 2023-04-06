import argparse
import datetime
import os
import re
import sys
import unicodedata

query_template = """[bbox: {}, {}, {}, {}]
[out:json]
[timeout:25]
;
(
	way;
	node;
);
out body;
>;
out skel qt;"""

world_mt_template = """enable_damage = false
creative_mode = true
mod_storage_backend = sqlite3
auth_backend = sqlite3
backend = {}
player_backend = sqlite3
gameid = antigrief
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
load_mod_signs_api = true
load_mod_basic_materials = true
load_mod_signs_road = true
load_mod_boards = true
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


def get_args():
	parser = argparse.ArgumentParser(description="Create a minetest world based on openstreetmap data.")
	parser.add_argument('-p', '--project', help="Project name")
	parser.add_argument('-w', '--worldname', help="World name used in world.mt file")
	parser.add_argument('-d', '--minetest_dir', help="Minetest runtime directory")
	parser.add_argument('-b', '--backend', default="sqlite3", help="BackEnd Database (sqlite3, leveldb)")
	parser.add_argument('-v', '--verbose', action='store_true', help="Log to console addionally to logfile.")
	parser.add_argument('-q', '--query', type=argparse.FileType("r", encoding="utf-8"), nargs='?', const='project_query', help="File containing a query with Overpass QL, cf. 'https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL'")
	parser.add_argument('-r', '--reuse_query', action='store_true', help="Reuse project-specific query file.")
	parser.add_argument('-a', '--area', type=ascii, help="Decimal coordinates of two opposite corners of desired area, separated by commas: 'lat_1, long_1, lat_2, long_2'")
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
		with open(query_path, 'r') as file:
			query_string = file.read()
			log(f"Reused project QUERY file {query_path}")
	elif args.query:
		with open(args.query, 'r') as file:
			query_string = file.read()
			log(f"Used query file {args.query}")
	elif args.area:
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
		log(f"Query file generated with S: {south}, W: {west}, N: {north}, E: {east}")
	else:
		log(f"Neither query file specified (-q), nor reusing project query file (-r), nor area given (-a). E.g. '52.524023988954376, 13.390914318783942, 52.51004666633488, 13.415739884736942', i.e. South, West, North, East. You can copy these coordinates from google maps for convenience.")
		sys.exit("Area not specified.")
	# Write the file:
	with open(query_path, 'w') as file:
		file.write(query_string)

def perform_query():
	# do the query and store the result in osm.json file:
	cmd = f'wget -q -O {osm_path} --post-file={query_path} "https://overpass-api.de/api/interpreter" >> {log_file}'
	log(f"Performing query: '{cmd}' ...")
	error = os.system(cmd)
	if error:
		log("... error!")
	else:
		log("... done")

def extract_features_from_osm_json():
	cmd = f'python3 parse_features_osm.py {osm_path} -o {feature_path} >> {log_file}'
	log(f"Extracting features using this command: '{cmd}' ...")
	error = os.system(cmd)
	if error:
		log("... error!")
	else:
		log("... done")

def generate_map_from_features():
	map_output_dir = os.path.join(project_path, "world2minetest")
	if not os.path.isdir(map_output_dir):
		os.makedirs(map_output_dir)
	if os.path.isdir(map_output_dir):
		log(f"Project w2mt mod dir '{map_output_dir}‘ created")
	else:
		log(f"Unable to create project w2mt mod dir '{map_output_dir}‘! Check rights!")
		sys.exit("Unable to create missing project w2mt mod dir.")
	map_output_path = os.path.join(map_output_dir, "map.dat")
	cmd = f'python3 generate_map.py --features={feature_path} --output={map_output_path} --createimg >> {log_file}'
	log(f"Generating map using this command: '{cmd}' ...")
	error = os.system(cmd)
	if error:
		log("... error!")
	else:
		log("... done")


def copy_mod_in_project_dir():
	# check runtime mods dir:
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
	world_mt_string = world_mt_template.format(args.backend, args.worldname)
	# Write the file:
	world_file = os.path.join(project_path, "world.mt").replace("\"", "")
	with open(world_file, 'w') as file:
		file.write(world_mt_string)
	log(f"world.mt file generated: {world_file}.")


######### SCRIPT EXECUTION STARTS HERE: ##############

args = get_args()

# first log starts with the call to this script with all arguments as given:
log_file = "w2mt.log"
if os.path.exists(log_file):
	 os.remove(log_file)
call_string=""
for arg in sys.argv:
	call_string += str(arg) + " "
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
project_path = os.path.join(args.minetest_dir, "worlds", args.project)
query_file = "query.osm";
query_path = os.path.join(project_path, query_file)
osm_path = os.path.join(project_path, "osm.json")
feature_file = "features_osm.json"
feature_path = os.path.join(project_path, feature_file)

check_project_dir()
prepare_query_file()
perform_query()
extract_features_from_osm_json()
generate_map_from_features()
if os.environ["MINETEST_GAME_PATH"]:
	copy_mod_in_project_dir()
	define_world_for_project()
else:
	log("Environment variable MINETEST_GAME_PATH not set. In order to manage w2mt mod and worlds you need to set it to the minetest home dir which should contain 'mods' and 'worlds' folders.")

