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

"""
PG - Processing Gain, calculated for every modem preset and corrected by coding rate value:
PG = 10*log10(2^SF/SF) - 10*log10(CR/4)
"""

class ModemPreset:
	params = [
		{'SF': 11, 'CR': 5, 'BW': 250000, 'PG': 21.73},	#LF
		{'SF': 12, 'CR': 8, 'BW': 125000, 'PG': 22.32},	#LS
		{'SF': 12, 'CR': 8, 'BW':  62500, 'PG': 22.32},	#VLS
		{'SF': 10, 'CR': 5, 'BW': 250000, 'PG': 19.13},	#MS
		{'SF':  9, 'CR': 5, 'BW': 250000, 'PG': 16.58},	#MF
		{'SF':  8, 'CR': 5, 'BW': 250000, 'PG': 14.08},	#SS
		{'SF':	7, 'CR': 5, 'BW': 250000, 'PG': 11.65},	#SF
		{'SF': 11, 'CR': 8, 'BW': 125000, 'PG': 19.68},	#LM
		{'SF':  7, 'CR': 5, 'BW': 500000, 'PG': 11.65},	#ST
	]
