#!/usr/bin/python3

# Outputs timestamp, elapsed time, and voltage of active scope channels at trigger point with SDS1104X-U.
# Scope Roll mode must be enabled.
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
	epilog="Outputs timestamp, elapsed time, and voltage of active scope channels at trigger point with SDS1104X-U. Scope Roll mode must be enabled."
)
parser.add_argument('-i', type=float, dest='interval', default=1, metavar='interval', help="Sample interval in seconds (default is 1)")
parser.add_argument('-n', type=int, dest='limit', default=0, metavar='limit', help="Maximum number of samples (default is unlimited)")
parser.add_argument('-p', action='store_true', dest='plot', help="Plot samples (only available with sample limit)")
args = parser.parse_args()

rm = pyvisa.ResourceManager()
for instr in rm.list_resources():
	match = re.search("::SDS.*::INSTR$", instr)
	if match:
		dso = rm.open_resource(instr)
		
if dso.query("SAST?").strip() != "SAST Roll":
	errprint("Scope Roll mode not enabled")
	sys.exit(1)

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
while n < args.limit or args.limit == 0:
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

if args.plot:
	plot(xpts, ypts, channels)
	