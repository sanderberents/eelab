#!/usr/bin/python3

# Outputs timestamp, elapsed time, and voltage of active scope channels at trigger point with SDS1104X-U.
# Optionally change SDG1032X DC voltage before taking each sample.
#
# Prerequisites:
# - pip3 install -U pyvisa
# - pip3 install -U matplotlib
#
# (c) 2024 Sander Berents
# Published under GNU General Public License v3.0. See file "LICENSE" for full license text.

import sys
import time
import datetime
import re
import argparse
import pyvisa
import matplotlib.pyplot as plt

def errprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def wait():
	"""Small delay for DSO or AWG command processing."""
	time.sleep(0.5)
	awg.query("*OPC?")
	dso.query("*OPC?")
	
def active_channels():
	"""Returns active DSO channels."""
	channels = []
	for ch in ['C1', 'C2', 'C3', 'C4']:
		s = dso.query(f"{ch}:TRA?").strip()
		match = re.search("^(C\d):TRA ON$", s)
		if match: channels.append(match.group(1))
	return channels

def measure_sample(ch):
	"""Returns V of given DSO channel at the trigger point."""
	# Assumes optimal vertical scale
	s = dso.query(f"{ch}:PAVA? LEVELX").strip()
	match = re.search("^C\d:PAVA LEVELX,(.*)V$", s)
	if match:
		sample = float(match.group(1))
	else:
		errprint(f"Error parsing: {s}")
		sys.exit(2)
	return sample

def plot(xpts, ypts, channels):
	"""Plots V of given channels."""
	colors = [ 'gold', 'magenta', 'cyan', 'limegreen' ]
	fig, ax1 = plt.subplots()
	ax1.set_title("Data Logger")
	ax1.set_xlabel("Time [s]")
	ax1.set_ylabel("Voltage [V]")
	for idx, ch in enumerate(channels):
		ax1.plot(xpts, ypts[idx], color=colors[idx], label=ch)
	ax1.legend()
	plt.show()

parser = argparse.ArgumentParser(
	description="Data Logger",
	epilog="Output timestamp, elapsed time, and voltage of active scope channels at trigger point with SDS1104X-U. Optionally change SDG1032X DC voltage before taking each sample."
)
parser.add_argument('-i', type=float, dest='interval', default=1, metavar='interval', help="Sample interval in seconds (default is 1)")
parser.add_argument('-n', type=int, dest='limit', default=0, metavar='limit', help="Maximum number of samples (default is unlimited)")
parser.add_argument('-p', action='store_true', dest='plot', help="Plot samples (only available with sample limit)")
parser.add_argument('-awg', type=int, choices=range(0, 3), dest='cawg', default=0, metavar='awgchannel', help="AWG output channel ([1,2], AWG off by default)")
parser.add_argument('-vmin', type=int, dest='vmin', default=0, metavar='vmin', help="AWG minimum DC voltage (default is 0)")
parser.add_argument('-vmax', type=int, dest='vmax', default=1, metavar='vmax', help="AWG maximum DC voltage (default is 1)")
args = parser.parse_args()

rm = pyvisa.ResourceManager()
awg = None
for instr in rm.list_resources():
	match = re.search("::SDS.*::INSTR$", instr)
	if match:
		dso = rm.open_resource(instr)
	match = re.search("::SDG.*::INSTR$", instr)
	if match:
		awg = rm.open_resource(instr)

awgch = f"C{args.cawg}"
dvawg = 0

scrollmode = dso.query("SAST?").strip() == "SAST Roll"
	
if args.cawg == 0:
	if not scrollmode:
		errprint("Warning: scope roll mode not enabled")
elif args.limit != 0:
	if scrollmode:
		errprint("Warning: scope roll mode enabled")
	# AWG setup: DC, offset, HiZ output ON
	awg.write(f"{awgch}:OUTP LOAD,HZ,PLRT,NOR")
	awg.write(f"{awgch}:BSWV WVTP,DC")
	awg.write(f"{awgch}:BSWV OFST,{args.vmin}")
	awg.write(f"{awgch}:OUTP ON")
	dvawg = (args.vmax - args.vmin) / (args.limit - 1)

channels = active_channels()
xpts = []
ypts = []

print("                 Timestamp,      [s]", end='')
for ch in channels:
	print(f",{ch:>9}", end='')
	ypts.append([])
print()

n = 0
start = None
vawg = args.vmin
while n < args.limit or args.limit == 0:
	if dvawg != 0:
		awg.write(f"{awgch}:BSWV OFST,{vawg}")
		vawg = vawg + dvawg
		wait()

	v = []
	now = datetime.datetime.now()
	if start == None: start = now
	elapsed = (now - start).total_seconds()
	xpts.append(elapsed)
	print(f"{now},{elapsed:9.3f}", end='')
	for idx, ch in enumerate(channels):
		v = measure_sample(ch)
		ypts[idx].append(v)
		print(f",{v:9.5f}", end='')
	print()
	n = n + 1
	time.sleep(args.interval)

dso.close()
if awg != None: awg.close()

if args.plot:
	plot(xpts, ypts, channels)
	