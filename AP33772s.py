import struct
import time
from micropython import const
from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_register.i2c_bit import ROBit, RWBit
from adafruit_register.i2c_bits import ROBits, RWBits
from adafruit_register.i2c_struct import UnaryStruct, Struct
from adafruit_register.i2c_struct_array import StructArray

def getbits(word, lowbit, highbit):
    ret = word >> lowbit
    nr_bits = highbit - lowbit + 1
    mask = (1 << nr_bits) - 1
    return ret & mask

def getbit(word, bit):
    return getbits(word, bit, bit)

# Do the comparison in integer 'units' instead in case
# v1 or v2 is a float.
def same_voltage(v1, v2, vunits):
    v1 = int(v1 / vunits)
    v2 = int(v2 / vunits)

    # Just make sure it's within a unit because of floating
    # point borkage
    return abs(v1 - v2) <= 1

class AP37772s:
    # Status bits are cleared after read. Don't define individual
    # "ROBit"s. Declare a whole byte that is read in its entirety
    # once.
    _status         = UnaryStruct(0x01, "<B")
    _mask           = UnaryStruct(0x02, "<B") # defined only for completeness

    _OPMODE = const(0x03)
    _source_pd      = ROBit(_OPMODE, 0)
    _source_legacy  = ROBit(_OPMODE, 1)
    _op_derated     = ROBit(_OPMODE, 6)
    _ccflip         = ROBit(_OPMODE, 7)

    _CONFIG = const(0x04)
    _dr_en          = RWBit(_CONFIG, 7)
    _otp_en         = RWBit(_CONFIG, 6)
    _ocp_en         = RWBit(_CONFIG, 5)
    _ovp_en         = RWBit(_CONFIG, 4)
    _uvp_en         = RWBit(_CONFIG, 3)

    _PDCONFIG = const(0x05)
    _enable_epr     = ROBit(_PDCONFIG, 0)
    _enable_pps     = ROBit(_PDCONFIG, 1) # pps and avs

    _voutctl        = RWBits(2, 0x06, 1)

    # 0x07 => 0x0C are not definted in the documentation

    _tr25           = UnaryStruct(0x0C, "<H")
    _tr50           = UnaryStruct(0x0D, "<H")
    _tr75           = UnaryStruct(0x0E, "<H")
    _tr100          = UnaryStruct(0x0F, "<H")

    _output_voltage = UnaryStruct(0x11, "<H")
    _output_current = UnaryStruct(0x12, "<B")
    _temperature    = UnaryStruct(0x13, "<B")
    _vreq           = UnaryStruct(0x14, "<H")
    _ireq           = UnaryStruct(0x15, "<H")

    _vselmin        = UnaryStruct(0x16, "<B")
    _uvpthr         = UnaryStruct(0x17, "<B")
    _ovpthr         = UnaryStruct(0x18, "<B")
    _ocpthr         = UnaryStruct(0x19, "<B")
    _otpthr         = UnaryStruct(0x1a, "<B")
    _drthr          = UnaryStruct(0x1b, "<B")

    # 0x1C => 0x20 are not definted in the documentation

    _SRCPDO_NUM_PDO = const(13)
    _source_pdo     = Struct(0x20, "<HHHHHHHHHHHHH")

    # 0x21 => 0x2D are aliases for the 13 individual source PDOs

    _pd_reqmsg      = Struct(0x31, "<BB") # Easiest to deal with as two bytes
    _pd_hard_reset  = RWBit (0x32, 0) # PD_CMDMSG
    _pd_msgrlt      = Struct(0x33, "<B")

    def output_voltage(self):
            return self._output_voltage * 0.080 # units are 80 mV
    def output_current(self):
            return self._output_current * 0.024 # units are 24 mA
    def temperature(self):
        return self._temperature # units are degrees C

    def parse_PPS_VOLTAGE_MIN(self, pdo_nr, pdo_dword):
        twobits = getbits(pdo_dword, 8, 9)
        vmin_pps = [ "Reserved",  3.3,  5.0, "others" ]
        vmin_avs = [ "Reserved", 15.0, 20.0, "others" ]

        if pdo_nr <= 7:
                vmin = vmin_pps
        else:
                vmin = vmin_avs

        return vmin[twobits]

    def _pdo_parse(self, pdo_nr, pdo_dword):
        pdo = {}
        pdo['raw'] = "0x%x" % pdo_dword 
        pdo['detected'] = bool(getbit(pdo_dword, 15))
        pdo['pdo_nr'] = pdo_nr

        if pdo['pdo_nr'] <= 7:
            pdo['vunits'] = 0.1
            pdo['epr'] = False
        else:
            pdo['vunits'] = 0.2
            pdo['epr'] = True

        _voltage = pdo['vunits'] * getbits(pdo_dword, 0, 7)
        pdo['max_voltage'] = _voltage
        pdo['min_voltage'] = _voltage

        if getbit(pdo_dword, 14):
            pdo['type'] = 'variable'
            pdo['min_voltage'] = self.parse_PPS_VOLTAGE_MIN(pdo_nr, pdo_dword)
        else:
            pdo['type'] = 'fixed'

        _current = getbits(pdo_dword, 10, 13)
        if _current == 0x0:
            pdo['max_current'] = 1.25
            pdo['moarcurrent'] = False
        elif _current == 0xf:
            pdo['max_current'] = 5.0
            # If set, the limit is over '_current'
            pdo['moarcurrent'] = True
        else:
            pdo['max_current'] = 1.25 + 0.25 * _current
            pdo['moarcurrent'] = False

        return pdo

    def _dump(self, p, prestr = ""):
        s = prestr
        fields = []
        for k in p:
            fields.append(k)
        fields.sort()
        for k in fields:
            if len(s):
                s = s + " "
            s = s + "%s:%-6s" % (k, p[k])
        print("%s" % (s))

    def _pdo_type(self, pdo_dword):
        return bool(pdo_dword & 0x40)

    # Constructor
    def __init__(self, i2c):
        self._i2c     = i2c
        self.slave_id = 0x52
        self.i2c_device = I2CDevice(i2c, self.slave_id)

        self.pdos = []
        raw_pdos = self._source_pdo
        for pdo_nr in range(len(raw_pdos)):
            pdo = raw_pdos[pdo_nr]
            pdohash = self._pdo_parse(pdo_nr+1, pdo)
            if not pdohash['detected']:
                continue
            self._dump(pdohash)
            self.pdos.append(pdohash)

    def test(self):
        print("source type: pd: %s legacy: %s" % (self._source_pd, self._source_legacy))
        print("_op_derated: '%s'" % (self._op_derated))
        print("    _ccflip: '%s'" % (self._ccflip))
        print("_enable_epr: '%s'" % (self._enable_epr))
        print("_enable_pps: '%s'" % (self._enable_pps))

        print("status: %s" % ( self._status))
        _pd_hard_reset = 1
        print("PD_MSGRLT: '%s'" % (self._pd_msgrlt))
        print("status: %s" % ( self._status))
        print("vout: '%s'" % (self._voutctl))
        print("pdconfig: '%s'" % (self._voutctl))
        print("output curr/voltage: '%s' '%s'" % (self._output_voltage, self._output_current))

        print("status: '%s'" % (self.get_pdo_status()))

    def get_best(self, pdo1, pdo2):
        if pdo1 == None:
            return pdo2
        if pdo2 == None:
            return pdo1
        if pdo1['max_current'] >= pdo2['max_current']:
            return pdo1
        return pdo2

    def set_voltage_pdo(self, v, pdo):
        # "0xff" means "max voltage. Sources should be happy with
        # having the voltage explicitly specified, no matter of the
        # PDO is fixed or variable. But some do care, evidently.
        # Use "max voltage" for fixed sources
        reqvolt = 0xff
        if pdo['type'] == 'variable':
            reqvolt = int(v / pdo['vunits'])
        reqidx = pdo['pdo_nr']
        reqcur = 0xf
        raw1 = reqvolt
        raw2 = reqcur | (reqidx<<4)
        self._dump(pdo, "requesting (%s, %s, %s): %2x %2x // " % (reqvolt, reqcur, reqidx, raw1, raw2))
        self._pd_reqmsg = (raw1, raw2)

    def set_voltage(self, v):
        #print("set_voltage() nr pdos: %d" % (len(self.pdos)))
        best_pdo = None
        # Look for a fixed PDO first:
        for pdo in self.pdos:
            if pdo['type'] != 'fixed':
                #print("pdo %d is not fixed" % (pdo['pdo_nr']))
                continue
            if not same_voltage(v, pdo['max_voltage'], pdo['vunits']):
                #print("pdo %d voltage does not match %s vs %s" % (pdo['pdo_nr'], v, pdo['max_voltage']))
                continue
            best_pdo = self.get_best(best_pdo, pdo)
            self._dump(best_pdo, "bestfixed: ")

        # Look for a variable PDO next:
        for pdo in self.pdos:
            if pdo['type'] == 'fixed':
                continue
            matchmax = same_voltage(v, pdo['max_voltage'], pdo['vunits'])
            matchmin = same_voltage(v, pdo['min_voltage'], pdo['vunits'])

            matchceil  = ( v <= pdo['max_voltage'] )
            matchfloor = ( v >= pdo['min_voltage'] )
            matchrange = matchceil and matchfloor

            matchany = matchmax or matchmin or matchrange
            if not matchany:
                print("pdo PPS %d voltage does not match" % (pdo['pdo_nr']))
                continue
            best_pdo = self.get_best(best_pdo, pdo)
            self._dump(best_pdo, "best: ")
        if best_pdo == None:
           print("unable to find pdo for voltage: %s" % (v))
           return
        self.set_voltage_pdo(v, best_pdo)

    _MASK_ADDR      = 0x02
    _STATUS_MASK_OTP     = 0x40
    _STATUS_MASK_OCP     = 0x20
    _STATUS_MASK_OVP     = 0x10
    _STATUS_MASK_NEWPDO  = 0x04
    _STATUS_MASK_READY   = 0x02
    _STATUS_MASK_STARTED = 0x01

    def get_pdo_status(self):
        pdo_status = self._status
        status_list = []
        if (pdo_status & self._STATUS_MASK_STARTED):
            status_list.append('started')
        if (pdo_status & self._STATUS_MASK_READY):
            status_list.append('ready')
        if (pdo_status & self._STATUS_MASK_NEWPDO):
            status_list.append('new_pdo')
        if (pdo_status & self._STATUS_MASK_OVP):
            status_list.append('oover_voltage')
        if (pdo_status & self._STATUS_MASK_OCP):
            status_list.append('over_current')
        if (pdo_status & self._STATUS_MASK_OTP):
            status_list.append('over_temp')
        return status_list


