![icon](misc/icon.png)
# KSSM - Yet Another Mesh network Simulator 
## 🇵🇱 Kolejny Symulator Sieci Mesh

KSSM is yet another mesh network simulator, but its goal is to demonstrate how mesh networks work. KSSM tries to imitate LoRa mesh networks, especially the [Meshtastic network](https://meshtastic.org/).

Why another simulator? Because I can :-)

This is a very early version. Many features are not well thought out yet. It may (or may not) evolve over time.

## Currently working features and their limitations
- Nodes can be of two different types: *BasicMeshNode* and *MeshtasticNode*. *BasicMeshNode* is a simple kind of mesh node that can send text messages and relay messages from others. *MeshtasticNode* implements *managed flood routing* like in Meshtastic network;
- Basic nodes have only one mode: BASIC NODE;
- For the moment, you should create scenarios with nodes of the same type and with the same radio parameters;
- Meshtastic nodes can work in modes: CLIENT, CLIENT_MUTE, CLIENT_HIDDEN, ROUTER, ROUTER_CLIENT (although it is deprecated), REPEATER, ROUTER_LATE; all other modes will work as a CLIENT;
- Nodes can work in one of these presets: LONG_FAST, LONG_SLOW, VERY_LONG_SLOW (despite it is deprecated), MEDIUM_SLOW, MEDIUM_FAST, SHORT_SLOW, SHORT_FAST, LONG_MODERATE, SHORT_TURBO;
- Nodes generate messages with very random length;
- CSMA/CA algorithm, based on values used by real Meshtastic nodes;
- The best possible time resolution is 1 µs, the default time resolution is 1 ms;
- Simple collision detection;
- Very simple propagation model;
- Station "range" is calculated with processing gain, so different Modem Presets result in different range;
- Output results: charts and nodes' states visualization (png), network state animation (mp4), nodes' states and message list (csv), organized in html.

## Requirements
- ffmpeg,
- python 3.7+,
- numpy, matplotlib, pandas.

## Usage
```
$ python3 KSSM.py --nodes_data=nodes.json 
[--simulation_time=10]
[--time_resolution=1000]
[--results_dir=output_dir]
[--png]
[--mp4]
[--slowmo_factor=5]
[--dpi=200]
```
Options:
- `--nodes_data=nodes.json` - **required**, a JSON file with description of the nodes. An example JSON structure is located in the `examples` directory,
- `--simulation_time=N` - length of the simulation in seconds (default 10 s),
- `--time_resolution=N` - time between the events in microseconds (default 1000 µs),
- `--results_dir=output_dir` - path to the directory where the results will be stored (default ./kssm/),
- `--png` - turns on generation of PNG files showing the current network state after every state change,
- `--mp4` - turns on generation of an MP4 video from the PNG files (automatically turns on `--png`)
- `--slowmo_factor=N` - slowdown factor of the output video file (default 5),
- `--dpi=200` - change the DPI size of PNG and MP4 (default 200).

## Input json structure
```
[
    {
        "type": "meshtastic",
        "node_id": "0xeacb7fe3",
        "long_name": "Node 1",
        "position": [
            2246.37,
            57.61,
            10
        ],
        "tx_power": 22,
        "noise_level": -102,
        "frequency": 869525000,
        "lora_mode": "LongFast",
        "hop_start": 3,
        "role": "CLIENT",
        "position_interval": 0,
        "nodeinfo_interval": 0,
        "text_message_min_interval": 0,
        "text_message_max_interval": 10,
        "debug": false
    },
    {
        "type": "meshtastic",
        "node_id": "0x30e6712a",
        "long_name": "Node 2",
        "position": [
            2068.78,
            2358.12,
            10
        ],
        "tx_power": 22,
        "noise_level": -102,
        "frequency": 869525000,
        "lora_mode": "LongFast",
        "hop_start": 3,
        "role": "CLIENT",
        "position_interval": 0,
        "nodeinfo_interval": 0,
        "text_message_min_interval": 0,
        "text_message_max_interval": 10,
        "debug": false
    }
]
```

The input file is JSON-encoded list of dictionaries. The elements of the dictionary describing a node are:
- *type* - type of the node: *basic* or *meshtastic*, if not provided it defaults to a *meshtastic* node;
- *node_id* - identifier of the node, in a hexadecimal representation of a 32-bit long integer;
- *long_name* - text name of the node;
- *position* - a list of three values representing x, y and z;
- *tx_power* - the power of transmitter as a number in dBm;
- *noise_level* - the power of noise in dBm received by the node;
- *frequency* - frequency used by the node in Hz;
- *lora_mode* - one of the predefined presets of modem (LongFast, MediumFast, ShortFast, ShortTurbo, etc.; check the `LoRaConstants.py` file);
- *role* - (only *meshtastic* nodes) one of the predefined node roles (CLIENT, ROUTER, ROUTER_CLIENT, REPEATER, ROUTER_LATE, CLIENT_HIDDEN, CLIENT_MUTE);
- *position_interval* - (only *meshtastic* nodes) the interval between sending POSITION messages, if set to 0, then feature is turned off;
- *nodeinfo_interval* - (only *meshtastic* nodes) the interval between sending NODEINFO messages, if set to 0, then feature is turned off;
- *text_message_min_interval* - the minimum interval between sending TEXT messages;
- *text_message_max_interval* - the maximum interval between sending TEXT messages, if *text_message_min_interval* and *text_message_max_interval* both are equal to 0 then TEXT messages are turned off;
- *debug* - true or false, more information about this node will be printed in terminal.

## Metrics explained
The KSSM calculates some metrics that describe network parameters. These metrics are presented in plots and stored in CSV files. The metrics are:
1. *air_util* - the percentage of the time the node was in one of these states: RX_BUSY and TX_BUSY; in other words this is the percentage of the time the medium was busy;
2. *tx_util* - the percentage of the time that the node was transmitting (TX_BUSY state);
3. *Number of known nodes* - the number of unique source node_ids registered in received frames;
4. *Number of messages heard* - the number of unique messages the node received;
5. *Normalized success rate* - this metric is calculated as 
$$normalized\\_success\\_rate = \frac{confirmed\\_messages}{tx\\_origin \cdot (number\\_of\\_nodes - 1)}$$
When the node successfully receives the message for the first time, the source's *confirmed_messages* metrics is incremented. Every message can be confirmed by all nodes (except the source node) in the map.
6.  *rx_success* - number of successfully completed receptions, this metric counts every received message (echos of our own, duplicates);
7.  *rx_fail* - number of times the reception failed because of collision;
8.  *rx_dups* - number of received duplicated messages;
9.  *rx_unicast* - number of received messages that the node was the destination;
10.  *tx_origin* - number of messages the node was the source;
11.  *tx_done* - number of times the node was transmitting messages (own or relayed);
12.  *forwarded* - number of messages that were forwarded by the node (the node was not the origin);
13.  *collisions_caused* - number of collisions caused by the node's transmission activity, collisions are counted for every node affected by the collision;
14.  *tx_cancelled* - number of times the node cancelled relaying, despite the fact the node was originally intended to relay, but heard another copy of this message (only *meshtastic* nodes);
15.  *tx_time_sum* - the cumulative time the node spent in TX_BUSY state;
16.  *rx_time_sum* - the cumulative time the node spent in RX_BUSY state;
17.  *backoff_time_sum* - the cumulative time the node spent in WAITING_FOR_TX state;

Plots of the success rate for every node are also available. For each inspected node, the number of received messages originating from it is displayed for every other node. For every received message, the number of hops is also registered, and an average *hops away* metric is calculated.

## Some details explained
### tx_time calculation
The time needed to transmit a message over LoRa is calculated with the method published in [Lora Modem Designer's Guide](https://github.com/meshtastic/meshtastic/blob/master/static/documents/LoRa_Design_Guide.pdf) and [Meshtastic source code](https://github.com/meshtastic/firmware/blob/1e4a0134e6ed6d455e54cd21f64232389280781b/src/mesh/RadioInterface.cpp#L201).
The symbol time is calculated with the formula $$symbol\\_time = \frac{2^{SF}}{BW}$$
Symbol time for some modem presets:
- *LONG_FAST* (SF = 11, BW = 250000 Hz) - symbol_time = 8192 µs
- *MEDIUM_FAST* (SF = 9, BW = 250000 Hz) - symbol_time = 2048 µs
- *SHORT_FAST* (SF = 7, BW = 250000 Hz) - symbol_time = 512 µs
- *VERY_LONG_SLOW* (SF = 12, BW = 62500 Hz) - symbol_time = 65536 µs
- *SHORT_TURBO* (SF = 7, BW = 500000 HZ) - symbol_time = 256 µs

### Signal-to-Noise Ratio (SNR) calculation
This is simplified, as there is no need to simulate the hardware and the entire communication channel. The SNR is calculated with the formula: $$SNR = P_{signal} - P_{noise}$$ where $$P_{signal}$$ is the RSSI of the signal (dBm) and $$P_{noise}$$ is the power of the background noise (dBm). The RSSI is calculated with simple propagation model. The background noise level (power) is just a parameter of the node (default: -100 dBm). The background noise level is constant during the simulation (it may change in future). When $$SNR > -1 \cdot PG$$ (PG - *processing gain*), then it is considered as "*station in range*".

### Processing gain
Different LoRa settings result in different "range". For the same antennas and the same tx_power we can have further range by changing SF (*Spreading Factor*) and CR (*Coding Rate*) parameters in exchange for longer time needed for the transmission.

The *processing gain* (PG) is calculated as:

$$PG = 10 \cdot log_{10}(\frac{2^{SF}}{SF}) - 10 \cdot log_{10}(\frac{CR}{4})$$

where:
- SF is the Spreading Factor (7 to 12),
- CR is the cumulative number of bits used to code 4 information bits (from 5 to 8).

### Backoff time calculation (Meshtastic nodes)
Backoff time (contention window) is the random amount of time a station waits before a transmission starts. This time is calculated in a few different ways. The important values are:
- CWmin = 3
- CWmax = 8
- $$slot\\_time = 2.5 \cdot symbol\\_time + 7.6\cdot 10^{-3}$$
#### For messages originating from the node
To calculate the backoff time in this case we need to know the current *air utilization* - the percentage of time the medium was used (we were transmitting or receiving). Then we need to "map" this percentage value (from 0 to 100) to the range <CWmin, CWmax>:

$$CWsize = \frac{airutil}{100} \cdot (CW_{max} - CW_{min}) + CW_{min}$$

The backoff time is the random value from the range $$<0, 2^{CWsize}>$$ multiplied by symbol_time:
$$backoff\\_time = random(0, 2^{CWsize}) \cdot symbol\\_time$$
#### For relayed messages
The backoff time for this case is calculated in two ways, depending the role of the relaying node. In both cases the backoff_time is related to SNR (signal-to-noise ratio) measured during receiving the message to be relayed. The SNR should be in range <-20, +10> and this value is mapped to the range <CWmin, CWmax>:

$$CWsize = \frac{SNR + 20}{30} \cdot (CW_{max} - CW_{min}) + CW_{min}$$

Then the backoff time is calculated as:
- for ROUTER and REPEATER: $$backoff\\_time = random(0, 2^{CWsize}) \cdot slot\\_time$$
- for CLIENT and ROUTER_LATE (if no duplicate message was received): $$backoff\\_time = 2 CWmax \cdot slot\\_time + random(0, 2^{CWsize}) \cdot slot\\_time$$
- for ROUTER_LATE when the message intended to relay was received more than once: $$backoff\\_time = 2CWmax \cdot slot\\_time + 2^{CWsize} \cdot slot\\_time$$

As you can see, the ROUTER and the REPEATER will retransmit the message earlier than CLIENT. In both cases, the station that received the message with lower SNR (we can assume it means the station was further from the source) will retransmit the message earlier.
### Message relay rules
- ROUTER or REPEATER: relays message always,
- CLIENT: will not relay the message if the message was heard at least two times (relayed by other stations),
- ROUTER_LATE: as client, but when message is heard at least twice it does not cancel the relay but delays the relay with the longest backoff time.
## TODO
* [x] tx_time
* [x] rx_time
* [x] backoff_time
* [x] tx_origin
* [x] node description in easy to edit format (json?)
* [x] number of collisions caused by the node
* [ ] state-time plot
* [ ] directional characteristics of antennas
* [ ] separating the data link and network layer logic into separate methods
* [x] backoff calculation regarding the node role
* [ ] waiting for ACK (the source of the message waits for the message to be repeated by other node and may send the message again)
* [x] AirUtil, TxUtil
* [x] summarized bar plots at the end of simulation
* [ ] easy way to change propagation model
* [ ] coexistence of nodes working on different frequencies and LoRa modem presets
* [ ] a little bit more smart doing things (optimization)
* [x] REPEATER
* [x] CLIENT_MUTE
* [x] CLIENT_HIDDEN
* [x] ROUTER_LATE
* [ ] machine-readable results
* [x] different type of nodes (basic, meshtastic) that allows to test and compare different rules of node behavior

## Example results
More examples you can find on: [KSSM examples page](https://kssm.wszechsiec.pl/)

https://github.com/user-attachments/assets/7bcf5927-d4e9-4b02-8332-fba0da0bcaa3

![Air util](images/air_util.png)
![TX util](images/tx_util.png)
![Air stat](images/air_stat.png)
![Known nodes](images/known_nodes.png)
![Messages heard](images/messages_heard.png)
![RX stat](images/rx_stat.png)
![TX stat](images/tx_stat.png)
![Success rate](images/success_rate_70b13ce3.png)

