import argparse
import os
import sys

parser = argparse.ArgumentParser(description="Start a minetest world made with w2mt as server.")
parser.add_argument('-p', '--project', help="Project name, i.e. directory of the world")
parser.add_argument('-w', '--worldname', help="World name as used in world.mt file")
parser.add_argument('-d', '--minetest_dir', help="Minetest runtime directory")
args = parser.parse_args()

if not args.project:
	print(f"Argument project missing. E.g. -p myworld_dir")
	sys.exit("Cannot start minetest server without world directory name.")

if not args.worldname:
	print(f"No argument worldname given, hence we will use the project name {args.project} as worldname.")
	args.worldname = args.project

if not args.minetest_dir:
	if os.environ["MINETEST_GAME_PATH"]:
		args.minetest_dir = os.environ["MINETEST_GAME_PATH"]
	else:
		args.minetest_dir = os.path.join(os.getcwd(), 'copy_content_to_minetest_dir')
		print("Neither environment variable MINETEST_GAME_PATH is set nor argument -d is given.")
		sys.exit(f'Hence we cannot start minetest server.')

mapdat_source = os.path.join(args.minetest_dir, "worlds", args.project, "world2minetest", "map.dat")
if not os.path.isfile(mapdat_source):
	print(f'Could not find w2mt map file at {mapdat_source}. Please provide valid project name, i.e. world directory.')
	sys.exit('Hence we cannot start the server.')
mapdat_target_dir = os.path.join(args.minetest_dir, "mods", "world2minetest")
if not os.path.isdir(mapdat_target_dir):
	os.makedirs(mapdat_target_dir)
	if os.path.isdir(mapdat_target_dir):
		log("Directory for world2minetest mod in minetest home did not exist, hence we created it.")
	else:
		log("Failed to create directory for world2minetest mod in minetest home.")
		sys.exit(f'Failed to create directory for world2minetest mod in minetest home, hence we cannot start minetest server.')

mapdat_target = os.path.join(mapdat_target_dir, "map.dat")
cmd = f'cp {mapdat_source} {mapdat_target}'
error = os.system(cmd)
if error:
	print(f"... error while trying: {cmd}!")

cmd = f'minetest --server --worldname {args.worldname}'
error = os.system(cmd)
if error:
	print("... error!")
else:
	print("... server finished")

