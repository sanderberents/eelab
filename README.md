# Home Electronics Lab

Controlling the Siglent SDS1104X-U oscilloscope and SDG1032X Arbitrary Waveform Generator with SCPI.

Prerequisites:

- `pip3 install -U pyvisa`
- `pip3 install -U matplotlib`

## Data Logger

![Data Logger](img/datalogger.png)

Samples active oscilloscope channels in Roll mode at the trigger point. Outputs each sample's timestamp, elapsed time, and voltage of the active channels to `stdout` in CSV format. Optionally plots the output. It is assumed that each channel is set up with the optimal vertical scale and position.

	usage: datalogger.py [-h] [-i interval] [-n limit] [-p]
	
	Data Logger
	
	optional arguments:
	-h, --help   show this help message and exit
	-i interval  Sample interval in seconds (default is 1)
	-n limit     Maximum number of samples (default is unlimited)
	-p           Plot samples (only available with sample limit)
	
	Outputs timestamp, elapsed time, and voltage of active scope channels at trigger point with SDS1104X-U. Scope Roll mode must be enabled.
