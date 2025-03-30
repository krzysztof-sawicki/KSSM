import csv
import os
from MeshMessage import MeshMessage

class MeshLogger:
	def __init__(self, message_file_path="message.csv", nodes_file_path="nodes.csv", backoff_file_path = "backoff.csv"):
		self.message_file_path = message_file_path
		self.nodes_file_path = nodes_file_path
		self.backoff_file_path = backoff_file_path
		
	def log_message(self, mesh_message, tx_node, rx_node, timestamp, rssi, snr, collision, complete_reception):
		message_id = mesh_message.message_id
		sender_addr = mesh_message.sender_addr
		dest_addr = mesh_message.dest_addr
		message_type = mesh_message.message_type
		hop_start = mesh_message.hop_start
		hop_limit = mesh_message.hop_limit

		message_id_hex = f"0x{message_id:08x}"
		sender_addr_hex = f"0x{sender_addr:08x}"
		dest_addr_hex = f"0x{dest_addr:08x}"

		log_data = {
			'timestamp': timestamp,
			'message_id': message_id_hex,
			'sender_addr': sender_addr_hex,
			'dest_addr': dest_addr_hex,
			'message_type': message_type,
			'message_length': mesh_message.length,
			'message_tx_time': mesh_message.tx_time,
			'hop_start': hop_start,
			'hop_limit': hop_limit,
			'tx_node': f"0x{tx_node:08x}",
			'rx_node': f"0x{rx_node:08x}",
			'rssi': rssi,
			'snr': snr,
			'collision': collision,
			'complete_reception': complete_reception
		}

		file_exists = os.path.isfile(self.message_file_path)

		with open(self.message_file_path, mode='a', newline='') as file:
			fieldnames = log_data.keys()
			writer = csv.DictWriter(file, fieldnames=fieldnames)
			if not file_exists:
				writer.writeheader()
			writer.writerow(log_data)
	
	def log_node(self, node):
		log_data = {
			'time': node.current_time,
			'node_id': f"{node.node_id:08x}",
			'long_name': node.long_name,
			'role': node.role,
			'position': node.position,
			'tx_power': node.tx_power,
			'noise_level': node.noise_level,
			'frequency': node.frequency,
			'lora_mode': node.lora_mode,
			'state': node.state,
			'backoff_time': node.backoff_time,
			'message_queue_len': node.message_queue.qsize(),
			'messages_heard': len(node.messages_heard),
			'known_nodes': len(node.known_nodes),
			'rx_success': node.rx_success,
			'rx_fail': node.rx_fail,
			'rx_dups': node.rx_dups,
			'rx_unicast': node.rx_unicast,
			'tx_done': node.tx_done,
			'forwarded': node.forwarded,
			'tx_cancelled': node.tx_cancelled,
			'collisions_caused': node.collisions_caused,
			'tx_origin': node.tx_origin,
			'messages_confirmed': node.messages_confirmed,
			'tx_sime_sum': node.tx_time_sum,
			'rx_time_sum': node.rx_time_sum,
			'backoff_time_sum': node.backoff_time_sum,
			'tx_util': f"{node.tx_util:.4f}",
			'air_util': f"{node.air_util:.4f}",
		}
		file_exists = os.path.isfile(self.nodes_file_path)

		with open(self.nodes_file_path, mode='a', newline='') as file:
			fieldnames = log_data.keys()
			writer = csv.DictWriter(file, fieldnames=fieldnames)
			if not file_exists:
				writer.writeheader()
			writer.writerow(log_data)
	
	def log_backoff(self, node, rebroadcast, SNR, CWsize, calculated_backoff):
		log_data = {
			'time': node.current_time,
			'node_id': f"{node.node_id:08x}",
			'long_name': node.long_name,
			'role': node.role,
			'tx_util': f"{node.tx_util:.4f}",
			'air_util': f"{node.air_util:.4f}",
			'rebroadcast': int(rebroadcast),
			'SNR': SNR,
			'CWsize': CWsize,
			'calculated_backoff': calculated_backoff,
		}
		file_exists = os.path.isfile(self.backoff_file_path)

		with open(self.backoff_file_path, mode='a', newline='') as file:
			fieldnames = log_data.keys()
			writer = csv.DictWriter(file, fieldnames=fieldnames)
			if not file_exists:
				writer.writeheader()
			writer.writerow(log_data)
