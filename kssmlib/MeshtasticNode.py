import random
import enum
import math
import queue
import copy
import os
import numpy.random
from functools import cache
from kssmlib.MeshMessage import MeshMessage, MessageType
from kssmlib import MeshConfig
from kssmlib.LoRaConstants import *
from kssmlib.MeshLogger import MeshLogger
from kssmlib.BasicMeshNode import BasicMeshNode, NodeState

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

class MeshtasticNode(BasicMeshNode):
	def __init__(self, node_id: int = None,
				long_name: str = None,
				role: Role = Role.CLIENT,
				position: tuple[float, float, float] = (0, 0, 10),
				tx_power: int = 10,
				noise_level: float = -100,
				frequency: float = 869.525e6,
				lora_mode: LoRaMode = LoRaMode.MEDIUM_FAST,
				propagation_model = None,
				hop_start = 3,
				position_interval: int = 600000000,
				nodeinfo_interval: int = 600000000,
				text_message_min_interval: int = 2000000,
				text_message_max_interval: int = 12000000,
				neighbors = None,
				debug = False,
				messages_csv_name = 'messages.csv',
				nodes_csv_name = 'nodes.csv',
				backoff_csv_name = 'backoff.csv'):
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
		super().__init__(node_id = node_id, long_name = long_name, position = position, tx_power = tx_power, noise_level = noise_level, frequency = frequency,
						lora_mode = lora_mode, propagation_model = propagation_model, hop_start = hop_start, text_message_min_interval = text_message_min_interval,
						text_message_max_interval = text_message_max_interval, neighbors = neighbors, debug = debug, messages_csv_name = messages_csv_name,
						nodes_csv_name = nodes_csv_name, backoff_csv_name = backoff_csv_name)

		self.role = role
		
		self.nodeinfo_interval = nodeinfo_interval
		if self.nodeinfo_interval > 0:
			self.last_nodeinfo_time = random.randint(0, self.nodeinfo_interval)
		else:
			self.last_nodeinfo_time = 0
		self.position_interval = position_interval
		if self.position_interval > 0:
			self.last_position_time = random.randint(0, self.position_interval)
		else:
			self.last_position_time = 0

	def valmap(self, value, istart, istop, ostart, ostop):
		if value > istop:
			value = istop
		elif value < istart:
			value = istart
		return int(round(ostart + (ostop - ostart) * ((value - istart) / (istop - istart)), 0))

	def set_role(self, new_role: Role):
		self.role = new_role

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
			bt =  random.randint(0, 2**CWsize) * slot_time
		else:
			# https://github.com/meshtastic/firmware/blob/1e4a0134e6ed6d455e54cd21f64232389280781b/src/mesh/RadioInterface.cpp#L279
			CWsize = self.calculate_cwsize_from_snr(SNR)
			if self.role in [Role.ROUTER, Role.REPEATER]:
				bt = random.randint(0, 2 * CWsize) * slot_time
			else:
				bt = (2 * MeshConfig.CWmax * slot_time) + random.randint(0, 2**CWsize) * slot_time;

		self.logger.log_backoff(self, rebroadcast, SNR, CWsize, bt)

		return bt

	def calculate_worst_backoff_time(self, SNR): #for ROUTER_LATE, when duplicate message was found
		# https://github.com/meshtastic/firmware/blob/a93d779ec0a0eb44262015f6b2e6bbfee82621af/src/mesh/RadioInterface.cpp#L271
		CWsize = self.calculate_cwsize_from_snr(SNR)
		slot_time = self.calculate_slot_time()
		bt = 2 * MeshConfig.CWmax * slot_time + 2**CWsize * slot_time
		self.logger.log_backoff(self, True, SNR, CWsize, bt)
		return bt

	def is_unconditional_forwarder(self):
		return (self.role in [Role.ROUTER, Role.REPEATER, Role.ROUTER_CLIENT, Role.ROUTER_LATE])

	def is_forwarder(self):
		return(self.role in [Role.ROUTER, Role.REPEATER, Role.ROUTER_CLIENT, Role.ROUTER_LATE, Role.CLIENT, Role.CLIENT_HIDDEN])

	def is_hidden(self):
		return(self.role in [Role.CLIENT_HIDDEN, Role.REPEATER])

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

	def inform(self, informing_node, message, step_interval):
		distance = self.propagation_model.calculate_distance(informing_node, self)
		signal_rssi = informing_node.tx_power - self.propagation_model.calculate_path_loss(informing_node, self)
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
				self.tx_cancelled += 1
			elif self.role == Role.ROUTER_LATE and self.msg_tx_buffer is not None and self.msg_tx_buffer.message_id == message.message_id and self.backoff_time > 0: # late router window
				"""
				https://github.com/meshtastic/firmware/blob/a93d779ec0a0eb44262015f6b2e6bbfee82621af/src/mesh/FloodingRouter.cpp#L56
				"""
				self.backoff_time = self.calculate_worst_backoff_time(self.messages_heard[message.message_id]["snr"])

		elif message.sender_addr == self.node_id: #ignore echo of my own message
			pass
		else: # heard for the first time
			self.messages_heard[message.message_id] = {"count": 1, "rssi": rssi, "snr": snr, "sender_addr": message.sender_addr, "hops_away": message.hop_start - message.hop_limit}
			self.find_node_by_id(message.sender_addr).message_received()
			if message.dest_addr == self.node_id: # we are the destination
				self.rx_unicast += 1
			elif self.is_forwarder():
				if message.hop_limit > 0:
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
			if not self.is_hidden() and self.nodeinfo_interval > 0 and (self.last_nodeinfo_time is None or self.current_time > self.last_nodeinfo_time + self.nodeinfo_interval):
				l = random.randint(MeshConfig.NODEINFO_MIN_LEN, MeshConfig.NODEINFO_MAX_LEN)
				message = MeshMessage(l, message_type = MessageType.NODEINFO, sender_addr = self.node_id, ModemPreset = self.ModemPreset, hop_start = self.hop_start)
				self.debug("NODEINFO generated")
			elif not self.is_hidden() and self.position_interval > 0 and (self.last_position_time is None or self.current_time > self.last_position_time + self.position_interval):
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
				rebroadcast = (self.msg_tx_buffer.sender_addr != self.node_id)
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

