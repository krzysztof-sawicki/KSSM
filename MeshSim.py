import random
import math
import tempfile
import glob
import re
import json
import os
import subprocess
import matplotlib.pyplot as plt
import numpy as np
from MeshNode import MeshNode, NodeState, Role
import LoRaConstants
import MeshConfig

class MeshSim:
	def __init__(self, nodes_data, size = (0, 1000, 0, 1000), png_out_dir = None, messages_csv_name = 'messages.csv', nodes_csv_name = 'nodes.csv'):
		self.size = size # x_min, x_max, y_min, y_max
		self.nodes_data = nodes_data
		self.nodes = []
		self.nodes_by_id = {}
		self.messages_csv_name = messages_csv_name
		self.nodes_csv_name = nodes_csv_name
		self.current_time = 0
		self.png_out_dir = png_out_dir
		if self.png_out_dir is not None:
			os.makedirs(self.png_out_dir, exist_ok=True)

		self.create_nodes()

	def create_nodes(self):
		for n in self.nodes_data:
			role = Role.CLIENT
			lora_mode = LoRaConstants.LoRaMode.MEDIUM_FAST
			if "role" in n.keys():
				if n["role"] == 'ROUTER':
					role = Role.ROUTER
				elif n["role"] == 'CLIENT_MUTE':
					role = Role.CLIENT_MUTE
				elif n["role"] == 'ROUTER_CLIENT':
					role = Role.ROUTER_CLIENT
				elif n["role"] == 'ROUTER_LATE':
					role = Role.ROUTER_LATE
				elif n["role"] == 'REPEATER':
					role = Role.REPEATER
				# every other role is treated as client
			if "lora_mode" in n.keys():
				if n["lora_mode"] == 'MediumFast':
					lora_mode = LoRaConstants.LoRaMode.MEDIUM_FAST
				elif n["lora_mode"] == 'LongFast':
					lora_mode = LoRaConstants.LoRaMode.LONG_FAST
				elif n["lora_mode"] == 'LongSlow':
					lora_mode = LoRaConstants.LONG_SLOW
				elif n["lora_mode"] == 'VeryLongSlow':
					lora_mode = LoRaConstants.VERY_LONG_SLOW
				elif n["lora_mode"] == 'MediumSlow':
					lora_mode = LoRaConstants.MEDIUM_SLOW
				elif n["lora_mode"] == 'ShortSlow':
					lora_mode = LoRaConstants.SHORT_SLOW
				elif n["lora_mode"] == 'ShortFast':
					lora_mode = LoRaConstants.SHORT_FAST
				elif n["lora_mode"] == 'LongModerate':
					lora_mode = LoRaConstants.LONG_MODERATE
				elif n["lora_mode"] == 'ShortTurbo':
					lora_mode = LoRaConstants.SHORT_TURBO

			node_id = int(n["node_id"], 16) & 0xffffffff
			node = MeshNode(
				node_id = node_id,
				long_name = n["long_name"],
				position = n["position"],
				tx_power = n["tx_power"],
				noise_level = n["noise_level"],
				frequency = n["frequency"],
				lora_mode = lora_mode,
				hop_start = n["hop_start"],
				nodeinfo_interval = n["nodeinfo_interval"] * 1000000,
				position_interval = n["position_interval"] * 1000000,
				neighbors = self.nodes,
				debug = n["debug"],
				role = role,
				messages_csv_name = self.messages_csv_name,
				nodes_csv_name = self.nodes_csv_name
			)
			print(node)
			self.nodes.append(node)
			self.nodes_by_id[node_id] = node

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
			if self.png_out_dir is not None:
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
		png_files = glob.glob(self.png_out_dir + "/*.png")
		self.ffmpeg_input = open(self.png_out_dir + "/ffmpeg_input.txt", "w")

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
		"ffmpeg", "-f", "concat", "-safe", "0", "-i", f"{self.png_out_dir}/ffmpeg_input.txt",
		"-vsync", "vfr", "-pix_fmt", "yuv420p", "-hide_banner", "-loglevel", "error", out_name
		])

	def plot_nodes(self, time = 0):
		fig, ax = plt.subplots(figsize=((self.size[1]-self.size[0])/1000, (self.size[3]-self.size[2])/1000))

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

		ax.set_xlim(self.size[0], self.size[1])
		ax.set_ylim(self.size[2], self.size[3])
		ax.set_title(f't = {(time/1000000):.06f} s')
		ax.set_xlabel('X [m]')
		ax.set_ylabel('Y [m]')
		ax.grid(True)
		plt.draw()
		plt.savefig("{}/{:010d}.png".format(self.png_out_dir, time), dpi=96)
		plt.close()
