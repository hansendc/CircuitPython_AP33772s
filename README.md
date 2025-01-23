# CircuitPython_AP33772s

This is a CircuitPython library to control the Diodes Incorporated USB PD AP33772s sink
controller. You can use this with a USB PD EPR source to get up to 28v at 5A out of a
capable power supply.

The library supports the new Adjustable Voltage Supply (AVS) mode. AVS is logically similar
to the old Programmable Power Supply (PPS) mode which let you pick your voltage up to 21v.
AVS starts at 15v. It's interesting to me because I have a 24v device I want to power.

## Getting Started

 1. Obtain a CircuitPython-capable microcontroller and connect a AP33772s to it.  You
can get an [all-in-one board](https://github.com/CentyLab/PicoPD_Pro) or a [AP33772s
breakout](https://www.tindie.com/products/centylab/rotopd-usb-pd-breakout-support-150w-avs/).
I bought mine from [CentyLab](https://www.tindie.com/stores/centylab/).
 3. Install CircuitPython on your board.  [This image](https://circuitpython.org/board/raspberry_pi_pico/) works on the PicoPD Pro.
 4. Install the adafruit_bus_device and adafruit_register libaries in CIRCUITPY/lib/ [download here](https://circuitpython.org/libraries)
 5. Install AP33772s.py from this repo in CIRCUITPY/lib/
 6. Copy test_AP33772s.py over to CIRCUITPY/code.py

## Links
 * [Pico PD Pro](https://github.com/CentyLab/PicoPD_Pro) - Basically a Raspberry Pi Pico board with the AP33772s built in
 * [Roto PD](https://www.tindie.com/products/centylab/rotopd-usb-pd-breakout-support-150w-avs/) - Breakout for the AP33772s. Hook up your microcontroller with I2C and go.
 * [AP33772s Data Sheet](https://www.diodes.com/assets/Evaluation-Boards/AP33772S-Sink-Controller-EVB-User-Guide.pdf)
 * [CircuitPython image download](https://circuitpython.org/board/raspberry_pi_pico/)
 * [CircuitPython library bundles](https://circuitpython.org/libraries)
 * [Hackaday Page](https://hackaday.io/project/198384-picopd-pro-usb-c-pd-31-pps-avs-with-rp2040) - Includes links to "EPR/AVS Supplies" that can do 28v.
