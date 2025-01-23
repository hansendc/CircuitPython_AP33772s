from AP33772s import *
import board
import busio

if board.board_id == "raspberry_pi_pico":
    i2c = busio.I2C(sda=board.GP0, scl=board.GP1)
else:
    i2c = board.I2C()

USB_PD = AP37772s(i2c=i2c)
USB_PD.test()

USB_PD.set_voltage(5)
time.sleep(1)
for i in range(50, 244, 2):
    USB_PD.set_voltage(i / 10.0)
    ov = USB_PD.output_voltage()
    oc = USB_PD.output_current()
    print("output voltage: %s current: %s" % (ov, oc))
    time.sleep(0.01)
