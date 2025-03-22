import enum
"""
LoRaMode is equal to ModemPreset in Meshtastic's protobufs
Values taken from:
https://github.com/meshtastic/protobufs/blob/14ec205865592fcfa798065bb001a549fc77b438/meshtastic/config.proto#L874
"""
class LoRaMode(enum.IntEnum):
	LONG_FAST = 0
	LONG_SLOW = 1
	VERY_LONG_SLOW = 2
	MEDIUM_SLOW = 3
	MEDIUM_FAST = 4
	SHORT_SLOW = 5
	SHORT_FAST = 6
	LONG_MODERATE = 7
	SHORT_TURBO = 8

class ModemPreset:
	params = [
		{'SF': 11, 'CR': 5, 'BW': 250000},	#LF
		{'SF': 12, 'CR': 8, 'BW': 125000},	#LS
		{'SF': 12, 'CR': 8, 'BW':  62500},	#VLS
		{'SF': 10, 'CR': 5, 'BW': 250000},	#MS
		{'SF':  9, 'CR': 5, 'BW': 250000},	#MF
		{'SF':  8, 'CR': 5, 'BW': 250000},	#SS
		{'SF':	7, 'CR': 5, 'BW': 250000},	#SF
		{'SF': 11, 'CR': 8, 'BW': 125000},	#LM
		{'SF':  7, 'CR': 5, 'BW': 500000},	#ST
	]
