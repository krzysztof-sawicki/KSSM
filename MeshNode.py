import random
import enum
import math
import queue
import copy
import os
import numpy.random
from functools import cache
from MeshMessage import MeshMessage, MessageType
import MeshConfig
from LoRaConstants import *
from MeshLogger import MeshLogger

"""
Node Role, values taken from:
https://github.com/meshtastic/protobufs/blob/14ec205865592fcfa798065bb001a549fc77b438/meshtastic/config.proto#L21
"""
class Role(enum.Enum):
	CLIENT = 0
	CLIENT_MUTE = 1
	ROUTER = 2
	ROUTER_CLIENT = 3
	REPEATER = 4
	TRACKER = 5
	SENSOR = 6
	TAK = 7
	CLIENT_HIDDEN = 8
	LOST_AND_FOUND = 9
	TAK_TRACKER = 10
	ROUTER_LATE = 11

class NodeState(enum.Enum):
	IDLE = 0
	RX_BUSY = 1
	WAITING_TO_TX = 2
	TX_BUSY = 3

	def __str__(self):
		return self.name

class MeshNode:
	def __init__(self, node_id: int = None, long_name: str = None, 
				role: Role = Role.CLIENT, position: tuple[float, float, float] = (0, 0, 10),
				tx_power: int = 10, noise_level: float = -100,
				frequency: float = 869.525e6, lora_mode: LoRaMode = LoRaMode.MEDIUM_FAST, hop_start = 3,
				position_interval: int = 600000000, nodeinfo_interval: int = 600000000,
				text_message_min_interval: int = 2000000, text_message_max_interval: int = 12000000,
				neighbors = None, debug = False, messages_csv_name = 'messages.csv', nodes_csv_name = 'nodes.csv'):
		"""
		Initialize a Meshtastic network node

		:param node_id: 32-bit node identifier (randomly generated if None)
		:param long_name: Node long name, node's hexadecimal id if not provided
		:param role: Node role in network (default CLIENT)
		:param position: Tuple (x, y, z) with coordinates in meters
		:param tx_power: Transmission power in dBm (default 10)
		:param noise_level: background noise level in dBm (default -100)
		:param frequency: Operating frequency in Hz (default 869525000)
		:param lora_mode: LoRa modem operation mode (default MediumFast)
		:param hop_start: default hop_start value for generated messages
		:param position_interval: Position packet broadcast interval in µs
		:param nodeinfo_interval: NodeInfo packet broadcast interval in µs
		:param text_message_min_interval: minimal time before new text message is generated in µs
		:param text_message_max_interval: maximal time before new text message is generated in µs
		:param neighbors: List of other nodes in the simulated environment
		"""
		# Generate random 32-bit node ID if not provided
		if node_id is None:
			self.node_id = random.randint(0, 0xFFFFFFFF)
		else:
			self.node_id = node_id & 0xFFFFFFFF  # Ensure 32-bit value
		
		if long_name is None:
			self.long_name = f"!{self.node_id:08x}"
		else:
			self.long_name = str(long_name)

		self.role = role
		self.position = position
		self.tx_power = tx_power
		self.noise_level = noise_level
		self.frequency = frequency
		self.lora_mode = lora_mode
		self.position_interval = position_interval
		self.nodeinfo_interval = nodeinfo_interval
		self.debugMask = debug
		self.hop_start = hop_start
		if self.hop_start < 0 or self.hop_start > 7:
			self.hop_start = 3
		self.ModemPreset = ModemPreset.params[int(self.lora_mode)]
		self.minimal_snr = -20 #I should do it better in the future :-)
		
		if self.nodeinfo_interval > 0:
			self.last_nodeinfo_time = random.randint(0, self.nodeinfo_interval)
		else:
			self.last_nodeinfo_time = 0
		if self.position_interval > 0:
			self.last_position_time = random.randint(0, self.position_interval)
		else:
			self.last_position_time = 0
		
		self.text_message_min_interval = text_message_min_interval
		self.text_message_max_interval = text_message_max_interval
		self.last_text_time = 0

		self.current_time = 0

		self.state = NodeState.IDLE
		self.state_changed = False

		self.message_queue = queue.Queue(maxsize = 20)

		self.neighbors = neighbors

		self.msg_tx_buffer = None

		self.backoff_time = 0
		self.tx_time = 0

		self.currently_receiving = {}
		self.messages_heard = {}	#list of received messages, with counter of duplicates
		self.known_nodes = []		#list of unique message.sender_addr in received frames
		self.rx_success = 0			#successfuly received messages
		self.rx_fail = 0			#messages failed during receiving
		self.rx_dups = 0			#received duplicates
		self.rx_unicast = 0			#received messages with dest_addr == self.node_id
		self.tx_done = 0			#transmitted messages
		self.forwarded = 0			#forwarded messages
		self.collisions_caused = 0	#number of collisions caused
		self.tx_time_sum = 0		#time spent on tx
		self.rx_time_sum = 0 		#time spent on rx
		self.backoff_time_sum = 0	#time spent on backoff
		self.tx_origin = 0			#number of messages generated by this node
		self.tx_origin_list = []	#list of message id generated by this node
		
		self.tx_util = 0.0			# tx_time_sum / current_time
		self.air_util = 0.0 		# (tx_time_sum + rx_time_sum) / current_time

		self.tx_start_time = None
		self.rx_start_time = None
		self.backoff_start_time = None

		self.logger = MeshLogger(message_file_path = messages_csv_name, nodes_file_path = nodes_csv_name)

	def find_node_by_id(self, node_id):
		for n in self.neighbors:
			if n.node_id == node_id:
				return n
		return None

	def valmap(self, value, istart, istop, ostart, ostop):
		if value > istop:
			value = istop
		elif value < istart:
			value = istart
		return int(round(ostart + (ostop - ostart) * ((value - istart) / (istop - istart)), 0))

	@cache
	def calculate_slot_time(self):
		# https://github.com/meshtastic/firmware/blob/1e4a0134e6ed6d455e54cd21f64232389280781b/src/mesh/RadioInterface.cpp#L594
		sum_propagation_turnaround_MAC_time = (0.2 + 0.4 + 7)*1000
		symbol_time = 1000000 * (2**self.ModemPreset["SF"]/self.ModemPreset["BW"])
		return 2.5 * symbol_time + sum_propagation_turnaround_MAC_time;
	
	def calculate_cwsize_from_snr(self, SNR):
		# https://github.com/meshtastic/firmware/blob/1e4a0134e6ed6d455e54cd21f64232389280781b/src/mesh/RadioInterface.cpp#L259
		return self.valmap(SNR, -20, 10, MeshConfig.CWmin, MeshConfig.CWmax);
	
	def calculate_backoff_time(self, rebroadcast = True, SNR = 0):
		"""
		Calculates the contention window (backoff time) regarding to:
		- source of the message (we are the source or we just rebroadcasting the message),
		- SNR of the received message,
		- node role (CLIENT, ROUTER etc.),
		- channel utilization
		"""
		slot_time = self.calculate_slot_time()
		
		if rebroadcast == False:
			# https://github.com/meshtastic/firmware/blob/1e4a0134e6ed6d455e54cd21f64232389280781b/src/mesh/RadioInterface.cpp#L247
			CWsize = self.valmap(int(self.air_util*100), 0, 100, MeshConfig.CWmin, MeshConfig.CWmax);
			return random.randint(0, 2**CWsize) * slot_time
		else:
			# https://github.com/meshtastic/firmware/blob/1e4a0134e6ed6d455e54cd21f64232389280781b/src/mesh/RadioInterface.cpp#L279
			CWsize = self.calculate_cwsize_from_snr(SNR)
			if self.role in [Role.ROUTER, Role.REPEATER]:
				return random.randint(0, 2 * CWsize) * slot_time
			else:
				return (2 * MeshConfig.CWmax * slot_time) + random.randint(0, 2**CWsize) * slot_time;

	def update_position(self, new_position: tuple[float, float, float]):
		"""Update node coordinates"""
		self.position = new_position  # Update the position tuple
		self.x, self.y, self.z = new_position  # Update individual coordinates

	def set_lora_config(self, mode: LoRaMode):
		"""Change LoRa modem configuration"""
		self.lora_mode = mode

	def set_role(self, new_role: Role):
		"""Modify node's network role"""
		self.role = new_role

	def set_node_id(self, new_id: int):
		"""Set a new 32-bit node identifier"""
		self.node_id = new_id & 0xFFFFFFFF  # Ensure 32-bit value

	def set_noise_level(self, noise_level: float):
		"""Set background noise level in dBm"""
		self.noise_level = noise_level

	def validate_settings(self):
		"""Verify configuration validity"""
		if self.tx_power < -10 or self.tx_power > 30:
			raise ValueError("Invalid TX power (range -10..30 dBm)")
		if self.frequency < 150 or self.frequency > 960:
			raise ValueError("Invalid frequency (range 150-960 MHz)")
		if not (0 <= self.node_id <= 0xFFFFFFFF):
			raise ValueError("Invalid node_id (must be a 32-bit integer)")
	
	def is_unconditional_forwarder(self):
		return (self.role in [Role.ROUTER, Role.REPEATER, Role.ROUTER_CLIENT, Role.ROUTER_LATE])

	def change_state(self, new_state):
		#self.debug("change state: {} -> {}".format(self.state, new_state))
		if self.state == NodeState.IDLE:
			if new_state == NodeState.RX_BUSY:
				self.rx_time_start = self.current_time
			elif new_state == NodeState.WAITING_TO_TX:
				self.backoff_start_time = self.current_time
			self.state = new_state
			self.state_changed = True
		elif self.state == NodeState.WAITING_TO_TX and new_state == NodeState.TX_BUSY:
			self.backoff_time_sum += self.current_time - self.backoff_start_time
			self.tx_start_time = self.current_time
			self.state = new_state
			self.state_changed = True
		elif self.state == NodeState.TX_BUSY and new_state == NodeState.IDLE:
			self.tx_time_sum += self.current_time - self.tx_start_time
			self.state = new_state
			self.state_changed = True
		elif self.state == NodeState.WAITING_TO_TX and new_state == NodeState.RX_BUSY:
			self.backoff_time_sum += self.current_time - self.backoff_start_time
			self.rx_time_start = self.current_time
			self.state = new_state
			self.state_changed = True
		elif self.state == NodeState.WAITING_TO_TX and new_state == NodeState.IDLE:	#dropped forwarded message because heard at least twice
			self.backoff_time_sum += self.current_time - self.backoff_start_time
			self.state = new_state
			self.state_changed = True
		elif self.state == new_state: # RX_BUSY -> RX_BUSY due to collision
			self.state_changed = True
		elif self.state == NodeState.RX_BUSY and (new_state == NodeState.IDLE or new_state == NodeState.WAITING_TO_TX):
			self.rx_time_sum += self.current_time - self.rx_time_start
			if new_state == NodeState.WAITING_TO_TX:
				self.backoff_start_time = self.current_time
			self.state = new_state
			self.state_changed = True
		else:
			raise Exception("Can't change the node state")

	def state_was_changed(self):
		if self.state_changed:
			self.state_changed = False
			return True
		else:
			return False

	def calculate_node_distance(self, node):
		return math.sqrt((self.position[0] - node.position[0])**2 + (self.position[1] - node.position[1])**2 + (self.position[2] - node.position[2])**2)

	@cache
	def calculate_urban_path_loss(self, distance: float) -> float:
		path_loss_db = 20 * math.log10(self.frequency) + 30 * math.log10(distance) - 147.56
		return round(path_loss_db, 2)
	@cache
	def calculate_theoretical_range(self, minimal_rx_rssi = -120):
		exponent = (self.tx_power - minimal_rx_rssi + 147.56 - 20 * math.log10(self.frequency)) / 30
		distance = 10 ** exponent
		return distance

	def inform_neighbors(self, step_interval):
		if self.state == NodeState.TX_BUSY and self.msg_tx_buffer is not None:
			for n in self.neighbors:
				if n.node_id != self.node_id:
					n.inform(self, self.msg_tx_buffer, step_interval)

	def inform(self, informing_node, message, step_interval):
		distance = self.calculate_node_distance(informing_node)
		signal_rssi = informing_node.tx_power - self.calculate_urban_path_loss(distance)
		signal_snr = signal_rssi - self.noise_level
		#self.debug(f"inform distance: {distance}\tsignal_rssi: {signal_rssi}\tsignal_snr: {signal_snr}")
		if self.state == NodeState.IDLE or self.state == NodeState.WAITING_TO_TX or self.state == NodeState.RX_BUSY:
			if signal_snr > self.minimal_snr: # I am in the range of the transmitted message
				#self.debug("informed by {:08x} about msg {:08x} distance: {:.2f} rssi {:.2f}".format(informing_node.node_id, message.message_id, distance, signal_rssi))
				if informing_node.node_id in self.currently_receiving.keys(): # already in the queue
					self.currently_receiving[informing_node.node_id]["rx_time"] += step_interval
					self.currently_receiving[informing_node.node_id]["last_heard"] = self.current_time
				else: # new message, adding to the queue
					if len(self.currently_receiving) != 0: #new message, but still during receiving another one
						self.find_node_by_id(informing_node.node_id).blame_collision()
					self.currently_receiving[informing_node.node_id] = {"rx_time": step_interval, "message": message, "last_heard": self.current_time, "collision": 0}
					self.change_state(NodeState.RX_BUSY)

				if len(self.currently_receiving) > 1: # collision
					for n in self.currently_receiving.keys():
						self.currently_receiving[n]["collision"] += step_interval
					self.debug("collision of rx from: {}".format(self.currently_receiving.keys()))

				if self.currently_receiving[informing_node.node_id]["rx_time"] >= message.tx_time: #the message was heard for the whole tx_time
					self.debug("RX end node: {:8x} message_id: {:8x}".format(informing_node.node_id, message.message_id))
					if self.currently_receiving[informing_node.node_id]["collision"] == 0: # the message was successfuly received
						self.rx_success += 1
						if self.currently_receiving[informing_node.node_id]["message"].sender_addr not in self.known_nodes: #new node to the list of known nodes
							self.known_nodes.append(self.currently_receiving[informing_node.node_id]["message"].sender_addr)
						self.logger.log_message(self.currently_receiving[informing_node.node_id]["message"], informing_node.node_id, self.node_id, self.current_time, signal_rssi, signal_snr, 0, 1)
						self.process_received_message(copy.deepcopy(self.currently_receiving[informing_node.node_id]["message"]), signal_rssi, signal_snr)
					else: # the collision happened during message receiving
						self.logger.log_message(self.currently_receiving[informing_node.node_id]["message"], informing_node.node_id, self.node_id, self.current_time, signal_rssi, signal_snr, 1, 1)
						self.rx_fail += 1
					del self.currently_receiving[informing_node.node_id]
					if len(self.currently_receiving) == 0:
						if self.backoff_time > 0: #RX happened during backoff
							self.change_state(NodeState.WAITING_TO_TX)
						else:
							self.change_state(NodeState.IDLE)
		elif self.state == NodeState.TX_BUSY:
			#self.debug("during TX, informed by {:08x} about msg {:08x} distance: {:.2f} rssi {:.2f}".format(informing_node.node_id, message.message_id, distance, signal_rssi))
			pass
		else:
			self.debug("unknown state, informed by {:08x} about msg {:08x} distance: {:.2f} rssi {:.2f}".format(informing_node.node_id, message.message_id, distance, signal_rssi))

	def blame_collision(self):
		self.collisions_caused += 1

	def process_received_message(self, message, rssi = 0, snr = 0):
		if message.message_id in self.messages_heard: #duplicate
			self.messages_heard[message.message_id]["count"] += 1
			self.rx_dups += 1
			self.debug(f"message {message.message_id:08x} duplicated")
			if not self.is_unconditional_forwarder() and self.msg_tx_buffer is not None and self.msg_tx_buffer.message_id == message.message_id and self.backoff_time > 0: #drop the frame from sending queue
				"""
				https://github.com/meshtastic/firmware/blob/1e41c994b3ec9395c1c9fb2aae25947ec6306060/src/mesh/FloodingRouter.cpp#L37
				"""
				self.backoff_time = 0
				self.msg_tx_buffer = None

		elif message.sender_addr == self.node_id: #ignore echo of my own message
			pass
		else: # heard for the first time
			self.messages_heard[message.message_id] = {"count": 1, "rssi": rssi, "snr": snr, "sender_addr": message.sender_addr, "hops_away": message.hop_start - message.hop_limit}
			if message.dest_addr == self.node_id: # we are the destination
				self.rx_unicast += 1
			elif message.hop_limit > 0:
				message.hop_limit -= 1
				try:
					self.message_queue.put(message, block = False)
					self.debug(f"message {message.message_id:08x} put to the tx queue with hop_limit {message.hop_limit}")
				except:
					self.debug("queue full, message dropped instead of forwarding")
			else:
				self.debug(f"message {message.message_id:08x} not forwarding, hop_limit = 0")

	def message_generator(self):
		if self.state == NodeState.IDLE:
			message = None
			if self.nodeinfo_interval > 0 and (self.last_nodeinfo_time is None or self.current_time > self.last_nodeinfo_time + self.nodeinfo_interval):
				l = random.randint(MeshConfig.NODEINFO_MIN_LEN, MeshConfig.NODEINFO_MAX_LEN)
				message = MeshMessage(l, message_type = MessageType.NODEINFO, sender_addr = self.node_id, ModemPreset = self.ModemPreset, hop_start = self.hop_start)
				self.debug("NODEINFO generated")
			elif self.position_interval > 0 and (self.last_position_time is None or self.current_time > self.last_position_time + self.position_interval):
				l = random.randint(MeshConfig.POSITION_MIN_LEN, MeshConfig.POSITION_MAX_LEN)
				message = MeshMessage(l, message_type = MessageType.POSITION, sender_addr = self.node_id, ModemPreset = self.ModemPreset, hop_start = self.hop_start)
				self.debug("POSITION generated")
			if message:
				try:
					self.message_queue.put(message, block = False)
					self.debug("message {:08x} added to the queue".format(message.message_id))
					self.tx_origin += 1
					self.tx_origin_list.append(message.message_id)
				except:
					self.debug("queue full, message dropped")
		#Generate text messages only if text_message_min_interval < text_message_max_interval and text_message_max_interval != 0
		if self.text_message_min_interval < self.text_message_max_interval and self.text_message_max_interval != 0:
			if self.last_text_time == 0:
				self.last_text_time = random.randint(self.text_message_min_interval, self.text_message_max_interval)
			if self.current_time > self.last_text_time:
				message = MeshMessage(random.randint(MeshConfig.TEXT_MIN_LEN, MeshConfig.TEXT_MAX_LEN), message_type = MessageType.TEXT, sender_addr = self.node_id, ModemPreset = self.ModemPreset, hop_start = self.hop_start)
				self.last_text_time += random.randint(self.text_message_min_interval,self.text_message_max_interval)
				self.debug("TEXT generated")
				try:
					self.message_queue.put(message, block = False)
					self.tx_origin += 1
					self.tx_origin_list.append(message.message_id)
					self.debug("message {:08x} added to the queue".format(message.message_id))
				except:
					self.debug("queue full, message dropped")

	def time_advance(self, step_interval = 1): #step interval in microseconds
		self.current_time += step_interval

		self.message_generator()

		if self.state == NodeState.IDLE and self.msg_tx_buffer is None:
			try:
				self.msg_tx_buffer = self.message_queue.get(block=False)
				rebroadcast = (self.msg_tx_buffer.sender_addr == self.node_id)
				r_snr = 0
				if self.msg_tx_buffer.message_id in self.messages_heard:
					r_snr = self.messages_heard[self.msg_tx_buffer.message_id]["snr"]
				if self.msg_tx_buffer.sender_addr != self.node_id:
					self.forwarded += 1
				self.backoff_time = self.calculate_backoff_time(rebroadcast = rebroadcast, SNR = r_snr)
				self.change_state(NodeState.WAITING_TO_TX)
				self.debug(f"Backoff: {self.backoff_time} µs")
			except queue.Empty:
				pass
		elif self.state == NodeState.WAITING_TO_TX and self.msg_tx_buffer is not None:
			self.backoff_time -= step_interval
			if self.backoff_time <= 0:
				self.backoff_time = 0
				if len(self.currently_receiving) == 0:
					self.tx_time = self.msg_tx_buffer.tx_time
					if (not self.is_unconditional_forwarder()) and self.msg_tx_buffer.message_id in self.messages_heard and self.messages_heard[self.msg_tx_buffer.message_id]["count"] > 1:
						"""
						https://github.com/meshtastic/firmware/blob/1e41c994b3ec9395c1c9fb2aae25947ec6306060/src/mesh/FloodingRouter.cpp#L37
						"""
						self.debug(f"message {self.msg_tx_buffer.message_id:08x} dropped, because heard {self.messages_heard[self.msg_tx_buffer.message_id]['count']} times")
						self.msg_tx_buffer = None
						self.change_state(NodeState.IDLE)
					else:
						self.change_state(NodeState.TX_BUSY)
					#self.debug("TX start, msg_id = {:8x} tx_time = {} ms".format(self.msg_tx_buffer.message_id, self.tx_time))
		elif self.state == NodeState.TX_BUSY:
			self.tx_time -= step_interval
			self.inform_neighbors(step_interval)
			if self.tx_time <= 0:
				self.change_state(NodeState.IDLE)
				#self.debug("TX end,   msg_id = {:8x}".format(self.msg_tx_buffer.message_id))
				if self.msg_tx_buffer.message_type == MessageType.NODEINFO:
					self.last_nodeinfo_time = self.current_time
				elif self.msg_tx_buffer.message_type == MessageType.POSITION:
					self.last_position_time = self.current_time
				self.msg_tx_buffer = None
				self.tx_done += 1
		elif self.state == NodeState.RX_BUSY: # Check if we have any partially received messages that could be removed from the queue after a timeout
			r_id = []
			for n_id in self.currently_receiving:
				if self.currently_receiving[n_id]["last_heard"] < self.current_time - (MeshConfig.RX_TIMEOUT * step_interval):
					self.debug("Removing rx message from the queue after timeout; from 0x{:08x}".format(n_id))
					self.logger.log_message(self.currently_receiving[n_id]["message"], n_id, self.node_id, self.current_time, 0, 0, int(self.currently_receiving[n_id]["collision"] > 0), 0)
					r_id.append(n_id)
					self.rx_fail += 1
			for n_id in r_id:
				del self.currently_receiving[n_id]
			if len(self.currently_receiving) == 0:
				if self.backoff_time > 0:
					self.change_state(NodeState.WAITING_TO_TX)
				else:
					self.change_state(NodeState.IDLE)
		else:
			self.debug("state unknown")
		
		self.tx_util = self.tx_time_sum / self.current_time
		self.air_util = (self.rx_time_sum + self.tx_time_sum) / self.current_time
		
		if self.state_changed:
			self.logger.log_node(self)

	def debug(self, log):
		if self.debugMask:
			print("T: {:9d}\tS: {:10s} N: {:08x}\t{}".format(self.current_time, self.state, self.node_id, log))

	def __str__(self):
		ret = "{}\n0x{:08x} - {}".format(self.long_name, self.node_id, self.state)
		if (self.state == NodeState.TX_BUSY or self.state == NodeState.WAITING_TO_TX) and self.msg_tx_buffer is not None:
			ret += f" msg: {self.msg_tx_buffer.message_id:08x}"
		ret += "\nin queue: {} ".format(self.message_queue.qsize())
		ret += f"known_nodes: {len(self.known_nodes)}\n"
		ret += f"rx_success: {self.rx_success}, rx_fail: {self.rx_fail}, rx_dups: {self.rx_dups}\ntx_done: {self.tx_done}, forwarded: {self.forwarded}, collisions_caused: {self.collisions_caused}"
		return ret

	def summarize(self):
		return str(self) + f"\nrx_time_sum = {self.rx_time_sum}\ntx_time_sum = {self.tx_time_sum}\nbackoff_time_sum = {self.backoff_time_sum}\ntx_origin = {self.tx_origin}\ntx_util = {self.tx_util:.4f}\nair_util = {self.air_util:.4f}\n"

	def color_from_state(self):
		if self.state == NodeState.IDLE:
			return 'green'
		elif self.state == NodeState.WAITING_TO_TX:
			return 'orange'
		elif self.state == NodeState.RX_BUSY:
			return '#aaaaff'
		elif self.state == NodeState.TX_BUSY:
			return 'red'
