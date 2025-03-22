# KSSM - Yet Another Mesh network Simulator 
## 🇵🇱 Kolejny Symulator Sieci Mesh

KSSM is yet another mesh network simulator, but its goal is to demonstrate how mesh networks work. KSSM tries to imitate [Meshtastic network](https://meshtastic.org/).

Why another simulator? Because I can :-)

This is a very early version. Many features are not well thought out yet. It may (or may not) evolve over time.

## Currently working features and their limitations
- nodes are generating messages with very random lenght,
- nodes can repeat messages,
- simplified CSMA/CA algorithm, still not related to real values used by real Meshtastic nodes,
- simple collision detection,
- very simple propagation model,
- output as mp4 and csv.

## Details explained
### tx_time calculation
The time needed to transmit a message over LoRa is calculated in the simplified way:
	
	def calculate_tx_time(self):
		symbol_length = 1000000*(2**self.ModemPreset["SF"] / self.ModemPreset["BW"])
		data_symbols = 16 + (self.length * 8)/self.ModemPreset["SF"]
		if data_symbols%1 > 0:
			data_symbols = int(data_symbols)+1
		self.tx_time = int(data_symbols*symbol_length)

The symbol_time is calculated with the formula [(source)](https://www.iotforall.com/everything-you-need-to-know-about-lora):
$$ symbol\_time = \frac{2^{SF}}{BW} $$
The *SF* value is the Spreading Factor used, the *BW* is the bandwidth of the signal. For *LONG_FAST* modem preset, the SF = 11, BW = 250000 Hz and symbol_time = 8192 µs. For *MEDIUM_FAST* modem preset, the SF= 9, BW = 250000 Hz and symbol_time = 2048 µs.
The `calculate_tx_time` function adds 16 symbols of LoRa preamble [(source)](https://meshtastic.org/docs/overview/mesh-algo/) to the number of symbols needed to code the payload and multiplies the result by symbol_time. This function does not calculates FEC and ignores the LoRa header. It may change in the future.

## Requirements
- ffmpeg,
- python 3.7+,
- numpy, matplotlib.

## Usage example
```
$ python3 kssm.py [--simulation_time=10] [--time_resolution=1000] [--out_name=kssm.mp4] [--slowmo_factor=5] [--csv_name=file.csv]
```
Options:
- `--simulation_time=N` - length of the simulation in seconds,
- `--time_resolution=N` - time between the events in microseconds,
- `--out_name=out.mp4` - name of the output video file,
- `--slowmo_factor=N` - slowdown factor of the output video file,
- `--csv_name=file.csv` - name of the csv file with the messages history.

## TODO
* [x] tx_time
* [x] rx_time
* [x] backoff_time
* [x] tx_origin
* [ ] node description in easy to edit format (json?)
* [x] number of collisions caused by the node
* [ ] state-time plot
* [ ] directional characteristics of antennas
* [ ] separating the data link and network layer logic into separate methods
* [ ] backoff calculation regarding the node role
* [ ] repeater role
* [ ] easy way to change propagation model
* [ ] coexistence of nodes working on different frequencies and LoRa modem presets

![Example](example.gif)

