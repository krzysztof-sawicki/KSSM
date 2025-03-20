import csv
import os
from MeshMessage import MeshMessage

class MeshMessageLogger:
	def __init__(self, log_file_path="out.csv"):
		self.log_file_path = log_file_path
		self.file_exists = os.path.isfile(self.log_file_path)

	def log(self, mesh_message, tx_node, rx_node, timestamp, rssi, collision, complete_reception):
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
			'collision': collision,
			'complete_reception': complete_reception
		}

		file_exists = os.path.isfile(self.log_file_path)

		with open(self.log_file_path, mode='a', newline='') as file:
			fieldnames = log_data.keys()
			writer = csv.DictWriter(file, fieldnames=fieldnames)
			if not file_exists:
				writer.writeheader()
			writer.writerow(log_data)
