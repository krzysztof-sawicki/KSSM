#!/usr/bin/env python3
import random
import math
import tempfile
import sys
import getopt
import glob
import re
import subprocess
import matplotlib.pyplot as plt
import numpy as np
from MeshNode import MeshNode, NodeState
import MeshConfig


class MeshSim:
	def __init__(self, nodes_data, width=5000, height=5000, csv_out_name = 'out.csv'):
		self.width = width
		self.height = height
		self.nodes_data = nodes_data
		self.nodes = []
		self.nodes_by_id = {}
		self.csv_out_name = csv_out_name
		self.current_time = 0
		self.temp_directory = tempfile.mkdtemp(prefix='kssm')
		
		self.create_nodes()

	def create_nodes(self):
		for n in self.nodes_data:
			node = MeshNode(
				node_id = n["node_id"],
				position = n["position"],
				tx_power = n["tx_power"],
				neighbors = self.nodes,
				debug = n["debug"],
				csv_out_name = self.csv_out_name
			)
			print(node)
			self.nodes.append(node)
			self.nodes_by_id[n["node_id"]] = node

	def time_advance(self, step_interval = 1000): #step interval in microseconds
		self.current_time += step_interval
		changedState = False
		for n in self.nodes:
			n.time_advance(step_interval)
			if n.state_was_changed():
				changedState = True

		if changedState or self.current_time % 100000 == 0:
			print("{:6d} ".format(self.current_time), end='')
			for n in self.nodes:
				print("{:12s} ".format(str(n.state)), end='')
			print()
			self.plot_nodes(self.current_time)

	def print_summary(self):
		for n in self.nodes:
			print(n.summarize())

	def make_video(self, out_name, slowmo_factor):
		def extract_us(filename):
			match = re.search(r'(\d{8,10})\.png$', filename)
			if match:
				return int(match.group(1))
			return 0
		png_files = glob.glob(self.temp_directory + "/*.png")
		self.ffmpeg_input = open(self.temp_directory + "/ffmpeg_input.txt", "w")

		png_files.sort(key=extract_us)
		frames = []

		durations = []
		times = [extract_us(file) for file in png_files]

		for i in range(len(times)-1):
			duration = times[i+1] - times[i]
			if duration < 1000:
				duration = 1000
			else:
				duration *= slowmo_factor
			durations.append(duration)
		durations.append(1000)

		for i in range(len(png_files)):
			self.ffmpeg_input.write(f"file {png_files[i]}\nduration {durations[i]/1000000}\n")
		self.ffmpeg_input.close()

		subprocess.call([
		"ffmpeg", "-f", "concat", "-safe", "0", "-i", f"{self.temp_directory}/ffmpeg_input.txt",
		"-vsync", "vfr", "-pix_fmt", "yuv420p", out_name
		])

	def plot_nodes(self, time = 0):
		fig, ax = plt.subplots(figsize=(10, 10))

		# Draw nodes and ranges
		for node in self.nodes:
			x, y = node.position[0], node.position[1]

			# Draw a point representing the node
			ax.scatter(x, y, color=node.color_from_state(), s = (node.tx_power + 10)**2)
			ax.annotate("{}".format(node), (x, y-200), fontsize=7)

		for node in self.nodes:
			if node.state == NodeState.RX_BUSY:
				for n_id, rx in node.currently_receiving.items():
					ax.annotate(
						'',
						xy=(node.position[0], node.position[1]),
						xytext=(self.nodes_by_id[n_id].position[0], self.nodes_by_id[n_id].position[1]),
						color='gray',
						arrowprops=dict(
							facecolor='gray',
							shrink=0.05,
							width=1,
							headwidth=5,
							headlength=5
						)
					)
				if len(node.currently_receiving) > 1:
					ax.text(node.position[0], node.position[1], 'x', color='red', fontsize=20, ha='center', va='center')
			elif node.state == NodeState.TX_BUSY:
				distance = node.calculate_theoretical_range()
				circle = plt.Circle((node.position[0], node.position[1]), distance,
					color='red',
					fill=True,
					facecolor='blue',
					alpha=0.1,
					linestyle='--',
					linewidth=1)
				ax.add_artist(circle)

		ax.set_xlim(0, self.width)
		ax.set_ylim(0, self.height)
		ax.set_title(f't = {(time/1000000):.06f} s')
		ax.set_xlabel('X [m]')
		ax.set_ylabel('Y [m]')
		ax.grid(True)
		plt.draw()
		plt.savefig("{}/{:010d}.png".format(self.temp_directory, time), dpi=96)
		plt.close()


nodes_data = [
	{"node_id": 0xdeadbeef, "position": (1000, 1000, 10), "tx_power": 12, "debug": True},
	{"node_id": 0xcafebabe, "position": (2000, 2500, 10), "tx_power": 12, "debug": True},
	{"node_id": 0x10101010, "position": (1000, 3000, 10), "tx_power": 12, "debug": True},
	{"node_id": 0xaaaaaaaa, "position": (3000, 4000, 10), "tx_power": 12, "debug": True},
	{"node_id": 0xc0c0c0c0, "position": (4000, 5000, 10), "tx_power": 12, "debug": True},
	{"node_id": 0xab00ab00, "position": (5500, 5500, 10), "tx_power": 12, "debug": True},
	{"node_id": 0xb22ff000, "position": (1000,  500, 10), "tx_power": 12, "debug": True},
	{"node_id": 0x82ab92aa, "position": (4000, 2000, 10), "tx_power": 12, "debug": True},
	{"node_id": 0x10005000, "position": (1000, 5000, 10), "tx_power": 14, "debug": True},
]


if __name__ == "__main__":

	simulation_time = MeshConfig.SIMULATION_TIME
	time_resolution = MeshConfig.SIMULATION_INTERVAL
	slowmo_factor = MeshConfig.SLOWMO_FACTOR
	out_name = 'kssm.mp4'
	csv_out_name = 'kssm.csv'

	try:
		opts, args = getopt.getopt(sys.argv[1:], "", ["simulation_time=", "time_resolution=", "out_name=", "slowmo_factor=", "csv_name="])
	except getopt.GetoptError as err:
		print(str(err))
		sys.exit(2)

	for opt, arg in opts:
		if opt == '--simulation_time':
			simulation_time = int(arg)
		elif opt == '--time_resolution':
			time_resolution = int(arg)
		elif opt == '--out_name':
			out_name = arg
		elif opt == '--slowmo_factor':
			slowmo_factor = int(arg)
		elif opt == '--csv_name':
			csv_out_name = arg

	mesh_sim = MeshSim(nodes_data, width=6000, height=6000, csv_out_name = csv_out_name)
	mesh_sim.plot_nodes()
	for t in range((simulation_time * 1000000)//time_resolution):
		mesh_sim.time_advance(time_resolution)
	mesh_sim.print_summary()
	mesh_sim.make_video(out_name, slowmo_factor)
