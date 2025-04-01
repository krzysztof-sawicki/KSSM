import random
from math import ceil
from enum import Enum
from kssmlib.LoRaConstants import *

class MessageType(Enum):
	"""Enum representing different types of Meshtastic messages."""
	TEXT = 1
	POSITION = 2
	NODEINFO = 3
	TELEMETRY = 4

class MeshMessage:
	"""
	A class representing a message in Meshtastic protocol.
	"""
	
	# Broadcast address
	BROADCAST_ADDR = 0xffffffff
	
	def __init__(self, length, message_type=MessageType.TEXT, message_id=None, hop_start=3, sender_addr=None, dest_addr=BROADCAST_ADDR, ModemPreset = ModemPreset.params[int(LoRaMode.MEDIUM_FAST)]):
		"""
		Initialize a MeshMessage object.
		
		Args:
			length (int): Length of the message in bytes (max 250)
			message_type (MessageType): Type of message (TEXT, POSITION, NODEINFO, TELEMETRY)
			message_id (int): 32-bit integer ID for the message
			hop_start (int): Starting hop count (0-7)
			sender_addr (int): 32-bit integer address of the sender
			dest_addr (int): 32-bit integer address of the recipient
		"""
		# Validate length
		if not isinstance(length, int) or length <= 0 or length > 250:
			raise ValueError("Message length must be between 1 and 250 bytes")
		self.length = length
		
		# Validate message type
		if not isinstance(message_type, MessageType):
			raise ValueError("Invalid message type, must be a MessageType enum")
		self.message_type = message_type
		
		# Generate random ID if not provided
		if message_id is None:
			self.message_id = random.randint(0, 0xFFFFFFFF)
		else:
			if not isinstance(message_id, int) or message_id < 0 or message_id > 0xFFFFFFFF:
				raise ValueError("Message ID must be a 32-bit integer (0 to 4294967295)")
			self.message_id = message_id
		
		# Validate hop_start
		if not isinstance(hop_start, int) or hop_start < 0 or hop_start > 7:
			raise ValueError("hop_start must be between 0 and 7")
		self.hop_start = hop_start
		
		self.hop_limit = hop_start
		
		# Validate sender address
		if sender_addr is None:
			raise ValueError("Sender address must be provided")
		if not isinstance(sender_addr, int) or sender_addr < 0 or sender_addr > 0xFFFFFFFF:
			raise ValueError("Sender address must be a 32-bit integer (0 to 4294967295)")
		self.sender_addr = sender_addr
		
		# Validate destination address
		if not isinstance(dest_addr, int) or dest_addr < 0 or dest_addr > 0xFFFFFFFF:
			raise ValueError("Destination address must be a 32-bit integer (0 to 4294967295)")
		self.dest_addr = dest_addr
		
		self.ModemPreset = ModemPreset
		
		self.calculate_tx_time()
	
	def __str__(self):
		"""Return a string representation of the message."""
		return (f"MeshMessage(type={self.message_type.name}, "
				f"id=0x{self.message_id:08x}, "
				f"length={self.length}, "
				f"hop_limit={self.hop_limit}, "
				f"from=0x{self.sender_addr:08x}, "
				f"to=0x{self.dest_addr:08x})")
	
	def is_broadcast(self):
		"""Check if the message is a broadcast message."""
		return self.dest_addr == self.BROADCAST_ADDR
	
	def calculate_tx_time(self):
		# https://github.com/meshtastic/meshtastic/blob/master/static/documents/LoRa_Design_Guide.pdf
		# 4 The LoRa Packet Format & Time On Air

		symbol_length = 1000000*(2**self.ModemPreset["SF"] / self.ModemPreset["BW"])
		low_data_rate_optimization = 1 if symbol_length > 16000 else 0 #when symbol_length > 16 ms
		header_disabled = 0 #header is always added
		cr = self.ModemPreset["CR"] - 4
		
		preamble_time = (16 + 4.25) * symbol_length
		
		payload_symbols = 8 + max(ceil(((8.0 * self.length - 4 * self.ModemPreset["SF"] + 28 + 16 - 20 * header_disabled) / (4 * (self.ModemPreset["SF"] - 2 * low_data_rate_optimization))) * cr), 0.0)
		
		self.tx_time = int(preamble_time + (payload_symbols * symbol_length))
