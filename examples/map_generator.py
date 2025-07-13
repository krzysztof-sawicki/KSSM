import random
import json
NUM_NODES = 10
X_SIZE = 20000
Y_SIZE = 20000

TX_POWER_MIN = 14
TX_POWER_MAX = 22

NOISE_MIN = -110
NOISE_MAX = -95

FREQUENCY = 869525000

TYPE = "meshtastic"

LORA_MODE = "MediumFast"

HOP_START_MIN = 3
HOP_START_MAX = 5

ROLE = "CLIENT"

POSITION_INTERVAL_MIN = 600
POSITION_INTERVAL_MAX = 800

NODEINFO_INTERVAL_MIN = 600
NODEINFO_INTERVAL_MAX = 800

TEXT_MESSAGE_MIN_INTERVAL = 2
TEXT_MESSAGE_MAX_INTERVAL = 12

nodes = []

for i in range(NUM_NODES):
	n = {
		"type":	TYPE,
		"node_id": f"0x{random.randint(0, 0xffffffff):08x}",
		"long_name": f"Node {i:02d}",
		"position": [random.randint(0, X_SIZE), random.randint(0, Y_SIZE), 10],
		"tx_power": random.randint(TX_POWER_MIN, TX_POWER_MAX+1),
		"noise_level": random.randint(NOISE_MIN, NOISE_MAX+1),
		"frequency": FREQUENCY,
		"lora_mode": LORA_MODE,
		"hop_start": random.randint(HOP_START_MIN, HOP_START_MAX),
		"role": ROLE,
		"position_interval": random.randint(POSITION_INTERVAL_MIN, POSITION_INTERVAL_MAX+1),
		"nodeinfo_interval": random.randint(NODEINFO_INTERVAL_MIN, NODEINFO_INTERVAL_MAX+1),
		"text_message_min_interval": TEXT_MESSAGE_MIN_INTERVAL,
		"text_message_max_interval": TEXT_MESSAGE_MAX_INTERVAL,
		"debug": True
	}
	nodes.append(n)

print(json.dumps(nodes, indent=4))

