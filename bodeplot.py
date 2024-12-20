#!/usr/bin/python3

# Creates Bode Plot and CSV output using SDS1104X-U and DSG1032X.
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
	time.sleep(args.delay)
	time.sleep(0.1)
	awg.query("*OPC?")
	dso.query("*OPC?")

def norm_angle(x):
	"""Normalizes angle to value between [-180,180[."""
	x = x % 360
	if x >= 180:
		x -= 360
	elif x < -180:
		x += 360
	return x

def step(f):
	"""Computes frequency sweep step size for given frequency."""
	p = math.floor(math.log10(f))
	return round((10 ** p) / args.quality)

def hscale(f):
	"""Computes optimal horizontal scale for given frequency."""
	t = 1 / (f * 4)
	units = ("ns", "us", "ms", "s")
	factors = (1e-9, 1e-6, 1e-3, 1)
	for i in range(0, len(units)):
		for j in (1, 2, 5, 10, 20, 50, 100, 200, 500):
			if j * factors[i] > t: return f"{j}{units[i]}"
	return "1s"

def vunit(v):
	"""Returns voltage with proper unit."""
	units = ("V", "mV", "uV")
	factors = (1, 1e-3, 1e-6)
	for i in range(0, len(units)):
		if abs(v) >= factors[i]: return f"{v / factors[i]}{units[i]}"
	return "1uV"

def vautoscale(ch):
	"""Automatic vertical scale adjustment."""
	# First measures Vpp, then adjusts vertical scale
	s = dso.query(f"{ch}:PAVA? PKPK").strip()
	match = re.search("^C\d:PAVA PKPK,(.*)V$", s)
	if match and not match.group(1).startswith("*"):
		vpp = float(match.group(1))
		vs = vunit(vpp / 7.5)
		dso.write(f"{ch}:VDIV {vs}")
	else:
		errprint(f"Error parsing Vpp for autoscale: {s}")
		sys.exit(1)

def dBV(v):
	return 20 * math.log10(v)

def measure_vpp(ch):
	"""Returns Vpp of given DSO channel."""
	# Assumes optimal vertical scale
	s = dso.query(f"{ch}:PAVA? PKPK").strip()
	match = re.search("^C\d:PAVA PKPK,(.*)V$", s)
	if match and not match.group(1).startswith("*"):
		vpp = float(match.group(1))
	else:
		errprint(f"Error parsing Vpp: {s}")
		sys.exit(2)
	return vpp

def measure_phase(ch1, ch2):
	"""Returns phase difference between two DSO channels."""
	# Assumes optimal horizontal and vertical scales
	dso.write(f"{ch2}-{ch1}:MEAD? PHA") # Query returns extra \xa1\xe3 data, so using read_raw
	s = dso.read_raw()[:-2].decode()
	match = re.search("^C\d-C\d:MEAD PHA,(.*)$", s)
	if match:
		if match.group(1).startswith("*"):
			phase = 0
		else:
			phase = norm_angle(float(match.group(1)))
	else:
		errprint(f"Error parsing phase: {s}")
		sys.exit(4)
	return phase

def plotvpp(xpts, vpps1, vpps2, phases):
	"""Plots Vpp and phase difference of two channels on logarithmic scales."""
	fig, ax1 = plt.subplots()
	ax1.set_title("Bode Plot - Vpp")
	ax1.set_xscale('log')
	ax1.set_yscale('log')
	ax1.set_xlabel("Frequency (Hz)")
	ax1.set_ylabel("Vpp [V]", color='blue')
	ax1.plot(xpts, vpps1, color='gold', label="C1")
	ax1.tick_params(axis ='y', labelcolor='blue')
	ax1.plot(xpts, vpps2, color='magenta', label="C2")
	ax1.legend()
	
	ax2 = ax1.twinx()
	ax2.set_ylabel("Phase [˚]", color='red')
	ax2.plot(xpts, phases, color='red', label="Phase")
	ax2.tick_params(axis ='y', labelcolor='red')
	fig.tight_layout()
	
def plotvdb(xpts, vdbs, phases):
	"""Plots dBV and phase difference on logarithmic scales."""
	fig, ax1 = plt.subplots()
	ax1.set_title("Bode Plot - dbV")
	ax1.set_xscale('log')
	ax1.set_xlabel("Frequency (Hz)")
	ax1.set_ylabel("dBV [dB]", color='blue')
	ax1.plot(xpts, vdbs, color='blue')
	ax1.tick_params(axis ='y', labelcolor='blue')
	
	ax2 = ax1.twinx()
	ax2.set_ylabel("Phase [˚]", color='red')
	ax2.plot(xpts, phases, color='red', label="Phase")
	ax2.tick_params(axis ='y', labelcolor='red')
	fig.tight_layout()

parser = argparse.ArgumentParser(
	description="Bode Plot",
	epilog="Creates Bode Plot and CSV output using SDS1104X-U and DSG1032X."
)
parser.add_argument('-in', type=int, choices=range(1, 5), dest='cin', default=1, metavar='inchannel', help="DSO channel for AWG output ([1-4], default is 1)")
parser.add_argument('-out', type=int, choices=range(1, 5), dest='cout', default=2, metavar='outchannel', help="DSO channel for DUT ([1-4], default is 2)")
parser.add_argument('-awg', type=int, choices=range(1, 3), dest='cawg', default=1, metavar='awgchannel', help="AWG output channel ([1,2], default is 1)")
parser.add_argument('-amp', type=int, dest='amp', default=1, metavar='amplitude', help="AWG sine wave amplitude in V (default is 1)")
parser.add_argument('-fs', type=int, dest='fs', default=1000, metavar='startfreq', help="Sweep start frequency in Hz (default is 1000)")
parser.add_argument('-fe', type=int, dest='fe', default=100000, metavar='endfreq', help="Sweep end frequency in Hz (default is 100000)")
parser.add_argument('-a1', type=int, dest='attn1', default=10, metavar='attenuation', help="Probe attenuation factor for inchannel (default is 10)")
parser.add_argument('-a2', type=int, dest='attn2', default=10, metavar='attenuation', help="Probe attenuation factor for outchannel (default is 10)")
parser.add_argument('-q', type=int, choices=range(1, 11), dest='quality', default=1, metavar='quality', help="Output quality ([1-10], default is 1)")
parser.add_argument('-d', type=float, dest='delay', default=0, metavar='delay', help="Delay between measurements in seconds (default is 0)")
args = parser.parse_args()

rm = pyvisa.ResourceManager()
for instr in rm.list_resources():
	match = re.search("::SDS.*::INSTR$", instr)
	if match:
		dso = rm.open_resource(instr)
	match = re.search("::SDG.*::INSTR$", instr)
	if match:
		awg = rm.open_resource(instr)
			
awgch = f"C{args.cawg}"
dsoch1 = f"C{args.cin}" # Channel for measuring AWG output
dsoch2 = f"C{args.cout}" # DUT channel

wait()

# AWG setup: sine wave, amplitude, HiZ output ON
awg.write(f"{awgch}:OUTP LOAD,HZ,PLRT,NOR")
awg.write(f"{awgch}:BSWV WVTP,SINE")
awg.write(f"{awgch}:BSWV FRQ,{args.fs}")
awg.write(f"{awgch}:BSWV OFST,0")
awg.write(f"{awgch}:BSWV AMP,{args.amp}")
awg.write(f"{awgch}:OUTP ON")

# DSO general setup
dso.write(f"CHDR SHORT")
dso.write(f"MSIZ 7M")
dso.write(f"MENU ON") # Actually turns the menu off
hs = hscale(args.fs)
dso.write(f"TDIV {hs}")

# DSO channels setup: attenuation, bandwidth limit OFF, DC coupling, zero offset, V unit, 150mV divisions
dso.write(f"{dsoch1}:ATTN {args.attn1}")
dso.write(f"{dsoch2}:ATTN {args.attn2}")
for ch in [dsoch1, dsoch2]:
	dso.write(f"{ch}:BWL OFF")
	dso.write(f"{ch}:CPL D1M")
	dso.write(f"{ch}:OFST 0V")
	dso.write(f"{ch}:UNIT V")
	dso.write(f"{ch}:VDIV {vunit(args.amp / 7.5)}")

# DSO trigger setup: edge trigger at 0V for AWG output channel
dso.write(f"{dsoch1}:TRCP DC")
dso.write(f"{dsoch1}:TRLV 0V")
dso.write(f"TRSE EDGE,SR,{dsoch1},HT,OFF")
dso.write("TRMD AUTO")

wait()

match = re.search("^SARA (.*)Sa/s", dso.query("SARA?").strip())
if match:
	sr = float(match.group(1))
	errprint(f"DSO sample rate: {sr} Sa/s")
	
wait()

xpts = []
vpps1 = []
vpps2 = []
vdbs = []
phases = []

print("    Freq,     Vpp 1,     Vpp 2,       dBV,     Phase")
f = args.fs
while f <= args.fe:
	hs = hscale(f)
	dso.write(f"TDIV {hs}")
	awg.write(f"{awgch}:BSWV FRQ,{f}")
	if f < 100: time.sleep(1)
	wait()

	vautoscale(dsoch1)
	vautoscale(dsoch2)
	wait()

	vpp1 = measure_vpp(dsoch1)
	vpp2 = measure_vpp(dsoch2)
	vdb = dBV(vpp2 / vpp1)
	phase = measure_phase(dsoch1, dsoch2)

	print(f"{f:8.0f},{vpp1:10.5f},{vpp2:10.5f},{vdb:10.5f},{phase:10.5f}")
	xpts.append(f);
	vpps1.append(vpp1);
	vpps2.append(vpp2);
	vdbs.append(vdb);
	phases.append(phase);
	
	df = step(f)
	f += df

awg.write(f"{awgch}:OUTP OFF")
awg.close()
dso.close()

plt.figure()
plotvpp(xpts, vpps1, vpps2, phases)
plt.figure()
plotvdb(xpts, vdbs, phases)
plt.show()
