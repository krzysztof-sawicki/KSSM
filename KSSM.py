#!/usr/bin/env python3

import getopt
import sys
import json
import os
import shutil
from kssmlib import MeshConfig
from kssmlib.MeshSim import MeshSim

if __name__ == "__main__":

	nodes_data = None
	nodes_data_file = None
	simulation_time = MeshConfig.SIMULATION_TIME
	time_resolution = MeshConfig.SIMULATION_INTERVAL
	slowmo_factor = MeshConfig.SLOWMO_FACTOR
	results_dir = f"./kssm/"
	generate_mp4 = False
	generate_png = False
	messages_csv_name = results_dir + 'messages.csv'
	nodes_csv_name = results_dir + 'nodes.csv'
	config_file = 'kssm.json'
	plot_dpi = 200

	options = ["nodes_data=", "simulation_time=", "time_resolution=", "results_dir=", "png", "mp4", "slowmo_factor=", "dpi=", "config=", "help"]

	try:
		opts, args = getopt.getopt(sys.argv[1:], "", options)
	except getopt.GetoptError as err:
		print(str(err))
		sys.exit(2)

	for opt, arg in opts:
		if opt == '--nodes_data':
			nodes_data_file = arg
		elif opt == '--results_dir':
			results_dir = arg
		elif opt == '--simulation_time':
			simulation_time = int(arg)
		elif opt == '--time_resolution':
			time_resolution = int(arg)
		elif opt == '--png':
			generate_png = True
		elif opt == '--mp4':
			generate_mp4 = True
			generate_png = True
		elif opt == '--slowmo_factor':
			slowmo_factor = int(arg)
		elif opt == '--dpi':
			plot_dpi = int(arg)
		elif opt == '--config':
			config_file = arg
		elif opt == '--help':
			for o in options:
				print(f"--{o}")
			sys.exit(0)

	if nodes_data_file is None:
		print("--nodes_data=file.json is required")
		sys.exit(-1)
	
	os.makedirs(results_dir, exist_ok = True)
	os.makedirs(results_dir + "/png/", exist_ok = True)
	messages_csv_name = results_dir + 'messages.csv'
	nodes_csv_name = results_dir + 'nodes.csv'

	with open(nodes_data_file, 'r') as f:
		nodes_data = json.load(f)
		shutil.copy(nodes_data_file, results_dir + "/input.json")
		x_min, x_max, y_min, y_max = None, None, None, None
		for n in nodes_data:
			if "position" not in n.keys():
				n["position"] = (0,0,0)
			if x_min is None or x_min > n["position"][0]:
				x_min = n["position"][0]
			if x_max is None or x_max < n["position"][0]:
				x_max = n["position"][0]
			if y_min is None or y_min > n["position"][1]:
				y_min = n["position"][1]
			if y_max is None or y_max < n["position"][1]:
				y_max = n["position"][1]
		x_r = x_max - x_min
		y_r = y_max - y_min
		x_min -= int(0.2*x_r)
		x_max += int(0.2*x_r)
		y_min -= int(0.2*y_r)
		y_max += int(0.2*y_r)

		mesh_sim = MeshSim(nodes_data, config_file = config_file, size = (x_min, x_max, y_min, y_max), results_dir = results_dir, plot_dpi = plot_dpi, generate_png = generate_png, generate_mp4 = generate_mp4)
		if generate_png:
			mesh_sim.plot_nodes()
		for t in range((simulation_time * 1000000)//time_resolution):
			mesh_sim.time_advance(time_resolution)
		mesh_sim.make_summary()
		if generate_mp4:
			mesh_sim.make_video(slowmo_factor)
		mesh_sim.make_html(simulation_time = simulation_time, time_resolution = time_resolution)
