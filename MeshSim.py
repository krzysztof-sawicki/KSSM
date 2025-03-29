import random
import math
import tempfile
import glob
import re
import json
import os
import subprocess
import matplotlib.pyplot as plt
import multiprocessing as mp
import numpy as np
from MeshNode import MeshNode, NodeState, Role
import LoRaConstants
import MeshConfig
from KSSMconfig import KSSMconfig

class MeshSim:
	def __init__(self, nodes_data, size = (0, 1000, 0, 1000), results_dir = '.', generate_png = False, generate_mp4 = False, plot_dpi = 200):
		self.size = size # x_min, x_max, y_min, y_max
		self.nodes_data = nodes_data
		self.nodes = []
		self.nodes_by_id = {}
		self.results_dir = results_dir
		self.generate_mp4 = generate_mp4
		self.generate_png = generate_png
		self.messages_csv_name = self.results_dir + "/messages.csv"
		self.nodes_csv_name = self.results_dir + "/nodes.csv"
		self.backoff_csv_name = self.results_dir + "/backoff.csv"
		self.current_time = 0
		self.dpi = plot_dpi
		self.config = KSSMconfig()

		self.create_nodes()
		self.plot_nodes(name = self.results_dir + "/nodes_map.png")

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
				text_message_min_interval = n["text_message_min_interval"] * 1000000,
				text_message_max_interval = n["text_message_max_interval"] * 1000000,
				neighbors = self.nodes,
				debug = n["debug"],
				role = role,
				messages_csv_name = self.messages_csv_name,
				nodes_csv_name = self.nodes_csv_name,
				backoff_csv_name = self.backoff_csv_name
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

		if changedState or self.config.plot_every_n_microseconds_if_state_not_changed > 0 and self.current_time % self.config.plot_every_n_microseconds_if_state_not_changed == 0:
			print("{:12d} ".format(self.current_time), end='')
			for n in self.nodes:
				print("{:14s} ".format(str(n.state)), end='')
			print()
			if self.generate_png:
				self.plot_nodes(self.current_time)

	def make_summary(self):
		node_names = []
		known_nodes = {'known_nodes': []}
		messages_heard = {'messages_heard': []}
		tx_stat = {
			'tx_origin': [],
			'tx_done': [],
			'forwarded': [],
			'collisions_caused': [],
		}
		air_stat = {
			'air_util': [],
			'tx_util': []
		}
		rx_stat = {
			'rx_success': [],
			'rx_fail': [],
			'rx_dups': [],
			'rx_unicast': [],
		}

		for n in self.nodes:
			print(n.summarize())
			node_names.append(f"0x{n.node_id:08x}\n{n.long_name}")
			messages_heard["messages_heard"].append(len(n.messages_heard))
			known_nodes["known_nodes"].append(len(n.known_nodes))
			tx_stat["tx_origin"].append(n.tx_origin)
			tx_stat["tx_done"].append(n.tx_done)
			tx_stat["forwarded"].append(n.forwarded)
			tx_stat["collisions_caused"].append(n.collisions_caused)
			air_stat["air_util"].append(n.air_util)
			air_stat["tx_util"].append(n.tx_util)
			rx_stat["rx_success"].append(n.rx_success)
			rx_stat["rx_fail"].append(n.rx_fail)
			rx_stat["rx_dups"].append(n.rx_dups)
			rx_stat["rx_unicast"].append(n.rx_unicast)

		self.plot_stats(node_names, known_nodes, 'known_nodes', 'Number of known nodes')
		self.plot_stats(node_names, messages_heard, 'messages_heard', 'Number of unique messages heard')
		self.plot_stats(node_names, tx_stat, 'tx_stat', 'Number of transmitted messages')
		self.plot_stats(node_names, air_stat, 'air_stat', 'Air statistics')
		self.plot_stats(node_names, rx_stat, 'rx_stat', 'RX statistics')
		
		self.plot_air_util()
		
		self.plot_messages_success_rate()

	def plot_air_util(self):
		x_coords = [node.position[0] for node in self.nodes]
		y_coords = [node.position[1] for node in self.nodes]
		air_utils = [node.air_util for node in self.nodes]
		tx_utils = [node.tx_util for node in self.nodes]

		print(x_coords)
		print(y_coords)
		print(air_utils)
		print(tx_utils)
		
		for name, data in [('air_util', air_utils), ('tx_util', tx_utils)]:
			fig, ax = plt.subplots(figsize=((self.size[1]-self.size[0])/1000, (self.size[3]-self.size[2])/1000))
			plt.grid()
			ax.set_xlim(self.size[0], self.size[1])
			ax.set_ylim(self.size[2], self.size[3])
			base_size = (self.size[1] - self.size[0]) * 0.005
			for i, v in enumerate(data):
				if v < 0.05:
					color = 'green'
				elif v < 0.1: 
					color = 'yellow'
				else:
					color = 'red'
				ax.scatter(x_coords[i], y_coords[i], s=100*v*base_size, c=color, alpha=0.9)
				ax.annotate(f"{self.nodes[i].long_name}\n0x{self.nodes[i].node_id:08x}\n{v*100:.1f}%", (x_coords[i], y_coords[i]), fontsize=self.config.plot_node_font_size)
			ax.set_title(name)
			plt.savefig(self.results_dir + "/" + name + ".png", dpi=self.dpi, bbox_inches='tight')

	def plot_stats(self, node_names, data, filename, title):
		x = np.arange(len(node_names))
		width = 1 / (len(data)+2)
		multiplier = 1
		fig, ax = plt.subplots(layout='constrained', figsize=(len(node_names), 5))

		for attribute, measurement in data.items():
			offset = width * multiplier
			rects = ax.bar(x + offset, measurement, width, label=attribute)
			ax.bar_label(rects, padding=3)
			multiplier += 1

		#ax.set_ylabel('Number')
		ax.set_title(title)
		ax.set_xticks(x + width, node_names)
		ax.legend(bbox_to_anchor=(0.5, -0.15), loc='upper center')
		plt.savefig(self.results_dir + "/" + filename + ".png", dpi=self.dpi, bbox_inches='tight')
		
	def plot_messages_success_rate(self):
		for node in self.nodes:
			fig, ax = plt.subplots(figsize=((self.size[1]-self.size[0])/1000, (self.size[3]-self.size[2])/1000))
			plt.grid()
			plt.title(f'Messages from 0x{node.node_id:08x} success rate')
			ax.set_xlim(self.size[0], self.size[1])
			ax.set_ylim(self.size[2], self.size[3])
			base_size = (self.size[1] - self.size[0]) * 0.001
			tx_origin = len(node.tx_origin_list)
			if tx_origin == 0:
				plt.close()
				continue
			for nodedest in self.nodes:
				if node.node_id != nodedest.node_id:
					msgs_received = 0
					hops_away = 0
					for tx_msg_id in node.tx_origin_list:
						if tx_msg_id in nodedest.messages_heard:
							msgs_received += 1
							hops_away += nodedest.messages_heard[tx_msg_id]["hops_away"]
					success_rate = msgs_received / tx_origin
					if msgs_received > 0:
						hops_away_avg = hops_away / msgs_received
						size = base_size * 100 * success_rate
						ax.scatter(nodedest.position[0], nodedest.position[1], s=size, c='red', alpha=0.9)
						ax.annotate(f"{nodedest.long_name}\n0x{nodedest.node_id:08x}\nReceived: {msgs_received} msgs ({(success_rate*100):.1f}%)\nAvg hops away: {hops_away_avg:.1f}", (nodedest.position[0], nodedest.position[1]), fontsize=self.config.plot_node_font_size)
					else:
						ax.scatter(nodedest.position[0], nodedest.position[1], s=base_size * 5, c='red', alpha=0.9)
						ax.annotate(f"{nodedest.long_name}\n0x{nodedest.node_id:08x}\nReceived: 0 msgs", (nodedest.position[0], nodedest.position[1]), fontsize=self.config.plot_node_font_size)
				else:
					ax.scatter(node.position[0], node.position[1], s=base_size * 100, c='green', alpha=0.9)
					ax.annotate(f"{node.long_name}\n0x{node.node_id:08x}\nSent: {tx_origin} messages", (node.position[0], node.position[1]), fontsize=self.config.plot_node_font_size)
			plt.savefig(self.results_dir + f"/success_rate_{node.node_id:08x}" + ".png", dpi=self.dpi, bbox_inches='tight')
			plt.close()


	def make_video(self, slowmo_factor):
		def extract_us(filename):
			match = re.search(r'(\d{8,10})\.png$', filename)
			if match:
				return int(match.group(1))
			return 0
		png_files = glob.glob(self.results_dir + "/png/*.png")
		self.ffmpeg_input = open(self.results_dir + "/png/ffmpeg_input.txt", "w")

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
		"ffmpeg", "-f", "concat", "-safe", "0", "-i", f"{self.results_dir}/png/ffmpeg_input.txt",
		"-vf", 'pad=width=ceil(iw/2)*2:height=ceil(ih/2)*2',
		"-vsync", "vfr", "-pix_fmt", "yuv420p", "-hide_banner", "-loglevel", "error", f"{self.results_dir}/result.mp4"
		])
	
	def save_plot_async(self, fig, filename, **kwargs):
		def _save_fig(fig_copy, filename, kwargs):
			fig_copy.savefig(filename, **kwargs)
			plt.close(fig_copy)
		
		# Create a process for saving the figure
		process = mp.Process(
			target=_save_fig,
			args=(fig, filename, kwargs)
		)
		process.start()
		
		return process

	def plot_nodes(self, time = 0, name = None):
		fig, ax = plt.subplots(figsize=((self.size[1]-self.size[0])/1000, (self.size[3]-self.size[2])/1000))

		# Draw nodes and ranges
		for node in self.nodes:
			x, y = node.position[0], node.position[1]

			# Draw a point representing the node
			ax.scatter(x, y, color=node.color_from_state(), s = (node.tx_power + 10)**2)
			ax.annotate("{}".format(node), (x, y-200), fontsize=self.config.plot_node_font_size)

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
			elif node.state == NodeState.TX_BUSY and self.config.plot_range_circles:
				distance = node.calculate_theoretical_range(minimal_rx_rssi = self.config.plot_range_circles_minimal_rssi)
				color = 'red'
				if self.config.plot_range_circles_color_from_message_id:
					color = "#{:06x}".format(node.msg_tx_buffer.message_id & 0x00ffffff)
				circle = plt.Circle((node.position[0], node.position[1]), distance,
					color=color,
					fill=True,
					facecolor='blue',
					alpha=0.3,
					linestyle='--',
					linewidth=1)
				ax.add_artist(circle)

		ax.set_xlim(self.size[0], self.size[1])
		ax.set_ylim(self.size[2], self.size[3])
		ax.set_title(f't = {(time/1000000):.06f} s')
		ax.set_xlabel('X [m]')
		ax.set_ylabel('Y [m]')
		ax.grid(True)
		if name is None:
			name = "{}/png/{:010d}.png".format(self.results_dir, time)
		save_process = self.save_plot_async(fig, name, dpi=self.dpi, bbox_inches='tight')
