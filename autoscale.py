#!/usr/bin/python3

# Optimizes vertical offset and scale of active scope channels.
# Assumes that the minimum and maximum values of the signals each fit within the
# screen limits before the script is executed.
#
# Prerequisites:
# - pip3 install -U pyvisa
# - pip3 install -U matplotlib
#
# (c) 2024 Sander Berents
# Published under GNU General Public License v3.0. See file "LICENSE" for full license text.

import sys
import math
import time
import re
import argparse
import pyvisa
import matplotlib.pyplot as plt

def errprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)
	
def wait():
	"""Small delay for DSO or AWG command processing."""
	time.sleep(0.1)
	dso.query("*OPC?")

def active_channels():
	"""Returns active DSO channels."""
	channels = []
	for ch in ['C1', 'C2', 'C3', 'C4']:
		s = dso.query(f"{ch}:TRA?").strip()
		match = re.search("^(C\d):TRA ON$", s)
		if match: channels.append(match.group(1))
	return channels

def vautoscale(ch):
	"""Automatic vertical offset and scale adjustment."""
	# Measures Vmin and Vmax, then adjusts vertical offset and scale
	for i in range(0, args.iterations):
		if i > 0: wait()
		s = dso.query(f"{ch}:PAVA? MIN").strip()
		match1 = re.search("^C\d:PAVA MIN,(.*)V$", s)
		s = dso.query(f"{ch}:PAVA? MAX").strip()
		match2 = re.search("^C\d:PAVA MAX,(.*)V$", s)
		if match1 and match2 and not match1.group(1).startswith("*") and not match2.group(1).startswith("*"):
			vmin = float(match1.group(1))
			vmax = float(match2.group(1))
			vpp = vmax - vmin
			v0 = vmin + vpp / 2
			dso.write(f"{ch}:OFST {-v0:.5f}V")
			dso.write(f"{ch}:VDIV {vpp / args.vdiv:.5f}V")
		else:
			errprint(f"Error parsing: {s}")
			sys.exit(1)

parser = argparse.ArgumentParser(
	description="Autoscale",
	epilog="Optimizes vertical offset and scale of active scope channels."
)
parser.add_argument('-d', type=float, dest='vdiv', default=7.5, metavar='vdiv', help="Vertical divisions (default is 7.5)")
parser.add_argument('-i', type=int, dest='iterations', default=2, metavar='iterations', help="Number of iterations (default is 2)")
args = parser.parse_args()

rm = pyvisa.ResourceManager()
for instr in rm.list_resources():
	match = re.search("::SDS.*::INSTR$", instr)
	if match:
		dso = rm.open_resource(instr)

channels = active_channels()
for idx, ch in enumerate(channels):
	vautoscale(ch)

dso.close()
