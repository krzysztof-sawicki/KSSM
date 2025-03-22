SIMULATION_INTERVAL	= 1000 # µs
SIMULATION_TIME		= 10 # s
SLOWMO_FACTOR		= 5 # every second of the simulation will be 5 times longer in the video

CWmin		= 3		# https://github.com/meshtastic/firmware/blob/1e4a0134e6ed6d455e54cd21f64232389280781b/src/mesh/RadioInterface.h#L95
CWmax		= 8

RX_TIMEOUT	= 3 # remove the message from the receiving queue after RX_TIMEOUT * SIMULATION_INTERVAL of no rx

COLD_START_NODEINFO_MAX_DELAY = 6000000
COLD_START_POSITION_MAX_DELAY = 6000000

NODEINFO_MIN_LEN = 25
NODEINFO_MAX_LEN = 50

POSITION_MIN_LEN = 30
POSITION_MAX_LEN = 70

TEXT_MIN_LEN = 20
TEXT_MAX_LEN = 100
TEXT_MESSAGE_MIN_TIME = 2000000
TEXT_MESSAGE_MAX_TIME = 10000000
