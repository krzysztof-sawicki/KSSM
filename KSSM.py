#!/usr/bin/env python3

import getopt
import sys
import json
import MeshConfig
from MeshSim import MeshSim

if __name__ == "__main__":

	nodes_data = None
	nodes_data_file = None
	simulation_time = MeshConfig.SIMULATION_TIME
	time_resolution = MeshConfig.SIMULATION_INTERVAL
	slowmo_factor = MeshConfig.SLOWMO_FACTOR
	mp4_out_name = None
	messages_csv_name = 'kssm-messages.csv'
	nodes_csv_name = 'kssm-nodes.csv'
	png_out_dir = None

	try:
		opts, args = getopt.getopt(sys.argv[1:], "", ["nodes_data=", "simulation_time=", "time_resolution=", "png_out_dir=", "mp4_name=", "slowmo_factor=", "messages_csv_name=", "nodes_csv_name="])
	except getopt.GetoptError as err:
		print(str(err))
		sys.exit(2)

	for opt, arg in opts:
		if opt == '--nodes_data':
			nodes_data_file = arg
		elif opt == '--png_out_dir':
			png_out_dir = arg
		elif opt == '--simulation_time':
			simulation_time = int(arg)
		elif opt == '--time_resolution':
			time_resolution = int(arg)
		elif opt == '--mp4_name':
			mp4_out_name = arg
		elif opt == '--slowmo_factor':
			slowmo_factor = int(arg)
		elif opt == '--messages_csv_name':
			messagess_csv_name = arg
		elif opt == '--nodes_csv_name':
			nodes_csv_name = arg
	
	with open(nodes_data_file, 'r') as f:
		nodes_data = json.load(f)
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
		
		mesh_sim = MeshSim(nodes_data, size = (x_min, x_max, y_min, y_max), png_out_dir = png_out_dir, messages_csv_name = messages_csv_name, nodes_csv_name = nodes_csv_name)
		if png_out_dir is not None:
			mesh_sim.plot_nodes()
		for t in range((simulation_time * 1000000)//time_resolution):
			mesh_sim.time_advance(time_resolution)
		mesh_sim.print_summary()
		if mp4_out_name is not None and png_out_dir is not None:
			mesh_sim.make_video(mp4_out_name, slowmo_factor)
