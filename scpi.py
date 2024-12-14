#!/usr/bin/python3

# SCPI Utility for SDS1104X-U and DSG1032X.
#
# Prerequisites:
# - pip3 install -U pyvisa
#
# (c) 2024 Sander Berents
# Published under GNU General Public License v3.0. See file "LICENSE" for full license text.

import re
import argparse
import pyvisa

parser = argparse.ArgumentParser(
	description="SCPI Utility",
	epilog="Submit SCPI command or query to SDS1104X-U or DSG1032X."
)
parser.add_argument('target', type=str, choices=('dso', 'awg'), metavar='target', help="Target instrument (one of 'dso' or 'awg')")
parser.add_argument('-q', type=str, dest='query', metavar='query', help="SCPI query")
parser.add_argument('-c', type=str, dest='command', metavar='command', help="SCPI command")
parser.add_argument('-x', action='store_true', dest='hex', help="Output query result as byte array")
args = parser.parse_args()

rm = pyvisa.ResourceManager()
resources = {}
for instr in rm.list_resources():
	match = re.search("::SDS.*::INSTR$", instr)
	if match:
		resources['dso'] = rm.open_resource(instr)
	match = re.search("::SDG.*::INSTR$", instr)
	if match:
		resources['awg'] = rm.open_resource(instr)

instr = resources[args.target]
if args.command != None:
	instr.write(args.command)
if args.query != None:
	if args.hex:
		instr.write(args.query)
		print(instr.read_raw())
	else:
		print(instr.query(args.query).strip())
if args.command == None and args.query == None:
	print(instr.query('*IDN?'))

for instr in resources:
	resources[instr].close()
	