# -*- coding: utf-8 -*-
"""
This module controls LaserQuantum lasers.

Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-iqo-modules/>

This file is part of qudi.

Qudi is free software: you can redistribute it and/or modify it under the terms of
the GNU Lesser General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with qudi.
If not, see <https://www.gnu.org/licenses/>.
"""

import visa
from enum import Enum

from qudi.core.configoption import ConfigOption
from qudi.interface.simple_laser_interface import SimpleLaserInterface
from qudi.interface.simple_laser_interface import ControlMode, ShutterState, LaserState


class PSUTypes(Enum):
    """ LaserQuantum power supply types.
    """
    MPC6000 = 0
    MPC3000 = 1
    SMD12 = 2
    SMD6000 = 3


class LaserQuantumLaser(SimpleLaserInterface):
    """ ToDo: describe

    Example config for copy-paste:

    laserquantum_laser:
        module.Class: 'laser.laserquantum_laser.LaserQuantumLaser'
        interface: 'ASRL1::INSTR'
        maxpower: 0.250 # in Watt
        psu: 'SMD6000'
    """

    serial_interface = ConfigOption(name='interface', default='ASRL1::INSTR', missing='warn')
    maxpower = ConfigOption(name='maxpower', default=0.250, missing='warn')
    psu_type = ConfigOption(name='psu', default='SMD6000', missing='warn')

    def on_activate(self):
        """ Activate module.
        """
        self.psu = PSUTypes[self.psu_type]
        self.connect_laser(self.serial_interface)

    def on_deactivate(self):
        """ Deactivate module.
        """
        self.disconnect_laser()

    def connect_laser(self, interface):
        """ Connect to Instrument.

            @param str interface: visa interface identifier

            @return bool: connection success
        """
        try:
            self.rm = visa.ResourceManager()
            rate = 9600 if self.psu in (PSUTypes.SMD6000, PSUTypes.SMD12) else 19200
            self.inst = self.rm.open_resource(
                interface,
                baud_rate=rate,
                write_termination='\r\n',
                read_termination='\r\n',
                send_end=True)
            # give laser 2 seconds maximum to reply
            self.inst.timeout = 2000
        except visa.VisaIOError:
            self.log.exception('Communication Failure:')
            return False
        else:
            return True

    def disconnect_laser(self):
        """ Close the connection to the instrument.
        """
        self.inst.close()
        self.rm.close()

    def allowed_control_modes(self):
        """ Control modes for this laser
        """
        if self.psu in (PSUTypes.SMD6000, PSUTypes.SMD12):
            return {ControlMode.POWER}
        return {ControlMode.POWER, ControlMode.CURRENT}

    def get_control_mode(self):
        """ Get current laser control mode.

        @return ControlMode: current laser control mode
        """
        if self.psu in (PSUTypes.SMD6000, PSUTypes.SMD12):
            return ControlMode.POWER
        return ControlMode[self.inst.query('CONTROL?')]

    def set_control_mode(self, mode):
        """ Set laser control mode.

        @param ControlMode mode: desired control mode
        """
        if self.psu not in (PSUTypes.SMD6000, PSUTypes.SMD12):
            if mode == ControlMode.POWER:
                reply1 = self.inst.query('PFB=OFF')
                reply2 = self.inst.query('CONTROL=POWER')
                self.log.debug("Set POWER control mode {0}, {1}.".format(reply1, reply2))
            else:
                reply1 = self.inst.query('PFB=ON')
                reply2 = self.inst.query('CONTROL=CURRENT')
                self.log.debug("Set CURRENT control mode {0}, {1}.".format(reply1, reply2))

    def get_power(self):
        """ Get laser power.

        @return float: laser power in watts
        """
        answer = self.inst.query('POWER?')
        try:
            if "mW" in answer:
                return float(answer.split('mW')[0])/1000
            elif 'W' in answer:
                return float(answer.split('W')[0])
            else:
                return float(answer)
        except ValueError:
            self.log.exception("Answer was {0}.".format(answer))
            return -1

    def get_power_setpoint(self):
        """ Get the laser power setpoint.

        @return float: laser power setpoint in watts
        """
        # FIXME: This is just wrong
        return self.get_power()

    def get_power_range(self):
        """ Get laser power range.

        @return float[2]: laser power range
        """
        return 0, self.maxpower

    def set_power(self, power):
        """ Set laser power

        @param float power: desired laser power in watts
        """
        self.inst.query('POWER={0:f}'.format(power*1000))

    def get_current_unit(self):
        """ Get unit for laser current.

        @return str: unit for laser current
        """
        return '%'

    def get_current_range(self):
        """ Get range for laser current.

        @return float[2]: range for laser current
        """
        return 0, 100

    def get_current(self):
        """ Cet current laser current

        @return float: current laser current
        """
        if self.psu in (PSUTypes.MPC3000, PSUTypes.MPC6000):
            return float(self.inst.query('SETCURRENT1?').split('%')[0])
        else:
            return float(self.inst.query('CURRENT?').split('%')[0])

    def get_current_setpoint(self):
        """ Current laser current setpoint.

        @return float: laser current setpoint
        """
        if self.psu in (PSUTypes.MPC3000, PSUTypes.MPC6000):
            return float(self.inst.query('SETCURRENT1?').split('%')[0])
        elif self.psu in (PSUTypes.SMD6000, PSUTypes.SMD12):
            return float(self.inst.query('CURRENT?').split('%')[0])
        else:
            return float(self.inst.query('SETCURRENT?').split('%')[0])

    def set_current(self, current_percent):
        """ Set laser current setpoint.

        @param float current_percent: laser current setpoint
        """
        self.inst.query('CURRENT={0}'.format(current_percent))
        return self.get_current()

    def get_shutter_state(self):
        """ Get laser shutter state.

        @return ShutterState: laser shutter state
        """
        return ShutterState.NOSHUTTER

    def set_shutter_state(self, state):
        """ Set the desired laser shutter state.

        @param ShutterState state: desired laser shutter state
        @return ShutterState: actual laser shutter state
        """
        pass

    def get_psu_temperature(self):
        """ Get power supply temperature

        @return float: power supply temperature
        """
        return float(self.inst.query('PSUTEMP?').split('C')[0])

    def get_laser_temperature(self):
        """ Get laser head temperature

        @return float: laser head temperature
        """
        return float(self.inst.query('LASTEMP?').split('C')[0])

    def get_temperatures(self):
        """ Get all available temperatures.

        @return dict: dict of temperature names and value
        """
        return {'psu': self.get_psu_temperature(), 'laser': self.get_laser_temperature()}

    def get_lcd(self):
        """ Get the text displayed on the PSU display.

        @return str: text on power supply display
        """
        if self.psu in (PSUTypes.SMD12, PSUTypes.SMD6000):
            return ''
        else:
            return self.inst.query('STATUSLCD?')

    def get_laser_state(self):
        """ Get laser operation state

        @return LaserState: laser state
        """
        if self.psu == PSUTypes.SMD6000:
            state = self.inst.query('STAT?')
        else:
            state = self.inst.query('STATUS?')
        if 'ENABLED' in state:
            return LaserState.ON
        elif 'DISABLED' in state:
            return LaserState.OFF
        else:
            return LaserState.UNKNOWN

    def set_laser_state(self, status):
        """ Set desited laser state.

        @param LaserState status: desired laser state
        """
        if self.get_laser_state() != status:
            if status == LaserState.ON:
                self.inst.query('ON')
            elif status == LaserState.OFF:
                self.inst.query('OFF')

    def get_firmware_version(self):
        """ Ask the laser for ID.

        @return str: what the laser tells you about itself
        """
        if self.psu == PSUTypes.SMD6000:
            self.inst.write('VERSION')
        else:
            self.inst.write('SOFTVER?')
        lines = []
        try:
            while True:
                lines.append(self.inst.read())
        except:
            pass
        return lines

    def dump(self):
        """ Return LaserQuantum information dump

        @return str: diagnostic information dump from laser
        """
        self.inst.write('DUMP ')
        lines = []
        try:
            while True:
                lines.append(self.inst.read())
        except:
            pass
        return lines

    def timers(self):
        """ Return information about component runtimes.

            @return str: runtimes of components
        """
        self.inst.write('TIMERS')
        lines = []
        try:
            while True:
                lines.append(self.inst.read())
        except:
            pass
        return lines

    def get_extra_info(self):
        """ Extra information from laser.
        For LaserQuantum devices, this is the firmware version, dump and timers information

        @return str: multiple lines of text with information about laser
        """
        extra = ''
        extra += '\n'.join(self.get_firmware_version())
        extra += '\n'
        if self.psu == PSUTypes.FPU:
            extra += '\n'.join(self.dump())
            extra += '\n'
        extra += '\n'.join(self.timers())
        extra += '\n'
        return extra

