# SDS1104X-U

The SDS1104X-U is an 8-bit oscilloscope similar to the SDS1104X-E but with a reduced feature set and similar limitations. With the release of the SDS800X HD series, neither of these should be considered for purchase, but if you own one already, there is no need to immediate replace it. Its main issue is the strict 8-bits math and acquisition modes, and that, unlike the SDS1104X-E and other Siglent products, it has never received even a single firmware update since its launch in 2021. In this document I will list some of the limitations and bugs I ran into.

Firmware: 1.1.5R6 (2021-05-11).

## General Limitations

- As an 8 bit oscilloscope, it is limited to 256 discrete voltage levels at a given scale. Its average and ERES acquisition modes are implemented in hardware. Although they do significantly reduce noise, the output is still always 8 bits on screen and when exported.

- Its math operations are also limited to 8 bits output. Differential measurements are futile even with the average and ERES acquisition modes. Using the `+` operation in an attempt to have 9-bit output for a channel is therefore still to 8 bits. Vertically scaling the math channel only magnifies this limit.

## SCPI Bugs

- That the oscilloscope has support for SCPI is great, but it is a bit buggy. The SCPI subsystem sometimes gets into a bad state when it is interrupted or a buggy command is used, e.g. `SCDP` or `<source>:PAVA? ALL`. In this state new queries always fail, or return data of a previous query, or always result in a timeout error.

	Workaround: unplug and replug the USB cable, or turn the oscilloscope off and on again.

- Any query that returns more than approximately 40 characters seems to result in an internal buffer overflow.

- Using an incorrect command or query often results in an unresponsive SCPI subsystem.

- `SCDP`

	The screen dump command only returns the BMP header and incorrect data for 12½ pixels. The example of the manual does not work on the SDS1104X-U. It always returns the same 116 bytes. By reading the data in small chunks, up to a few KB may be returned before an inevitable timeout error, even with increased timeout setting. That data still does not resemble the current screen though. It is mostly repeated `\x8631` words. Using this command often leaves the oscilloscope's SCPI subsystem in a bad state. Because the SDS1104X-U does not have a webserver, this command might have been a convenient way to obtain screenshots without having to resort to a USB stick, but alas, the command is totally broken.
	
	Workaround: none.

- `<source>:MEAD? PHA`

	Querying for the phase difference between to channels results in a decode error because of two extra bytes: `\xa1\xe3`.
	
	Workaround: Instead of `.query()` use `.write()` and `.read_raw()[:-2].decode()`.

- `<source>:MEAD? PHA`

	The returned phase is not in the range [-180,180[ but in [-90, 270[ instead. The same is the case in the user interface.
	
	Workaround: Convert to [-180,180[.

- `<source>:PAVA? ALL`

	Returns a truncated response and SCPI gets into a bad state. Subsequent queries return different parts of this request.

	Workaround: Use `PAVA` commands for individual measurements.

- `'MENU?` / `MENU ON` / `MENU OFF`

	Returns the and sets the opposite of the actual state of the menu.

	Workaround: to turn off the menu, use `MENU ON`.

- `MEGS?`

	SCPI subsystem hangs.
	
	Workaround: don't use this query.

- Cursor track mode is slow. Gate measurements is faster and should be used instead with SCPI.

- Waveform download is broken.