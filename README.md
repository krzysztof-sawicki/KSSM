# KSSM - Yet Another Mesh network Simulator (🇵🇱 Kolejny Symulator Sieci Mesh)

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

## Requirements
- ffmpeg,
- python 3.7+,
- numpy, matplotlib.

## Usage example
```
$ python3 kssm.py [--simulation_time=10] [--time_resolution=1000] [--out_name=kssm.mp4] [--slowmo_factor=5]
```
Options:
- `--simulation_time=N` - length of the simulation in seconds,
- `--time_resolution=N` - time between the events in microseconds,
- `--out_name=out.mp4` - name of the output video file,
- `--slowmo_factor=N` - slowdown factor of the output video file.

## TODO
- [x] tx_time
- [x] rx_time
- [x] backoff_time
- [x] tx_origin
- [] node description in easy to edit format (json?)
- [] number of collisions caused by the node
- [] state-time plot
- [] directional characteristics of antennas
- [] separating the data link and network layer logic into separate methods
- [] backoff calculation regarding the node role
- [] repeater role
- [] easy way to change propagation model
- [] coexistence of nodes working on different frequencies and LoRa modem presets

![Example](example.gif)
