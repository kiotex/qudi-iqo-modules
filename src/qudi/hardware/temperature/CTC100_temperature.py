# -*- coding: utf-8 -*-

"""
This module controls the Stanford Instruments CTC100 temperature
controller (also rebranded as CryoVac TIC500, etc).

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

from qudi.core.module import Base
from qudi.core.configoption import ConfigOption
import visa


class CTC100(Base):
    """ This module implements communication with CTC100 temperature controllers
    or clones/licensed devices.

    ATTENTION: This module is untested and very likely broken.

    Example config for copy-paste:

    tempcontroller_ctc100:
        module.Class: 'temperature.CTC100_temperature.CTC100'
        interface: 'ASRL1::INSTR'
        fitlogic: 'fitlogic' # name of the fitlogic module, see default config

    """

    # config options
    _interface = ConfigOption('interface', missing='error')

    def on_activate(self):
        """ Activate modeule
        """
        self.log.warning("This module has not been tested on the new qudi core and might not work properly/at all."
                         "Use it with caution and if possible contribute to its rework, please.")
        self.connect(self._interface)

    def on_deactivate(self):
        """ Deactivate modeule
        """
        self.disconnect()

    def connect(self, interface):
        """ Connect to Instrument.

            @param str interface: visa interface identifier

            @return bool: connection success
        """
        try:
            self.rm = visa.ResourceManager()
            self.inst = self.rm.open_resource(interface, baud_rate=9600, term_chars='\n', send_end=True)
        except visa.VisaIOError as e:
            self.log.exception("")
            return False
        else:
            return True

    def disconnect(self):
        """ Close the connection to the instrument.
        """
        self.inst.close()
        self.rm.close()

    def get_channel_names(self):
        """ Get a list of channel names.

            @return list(str): list of channel names
        """
        return self.inst.ask('getOutputNames?').split(', ')

    def is_channel_selected(self, channel):
        """ Check if a channel is selectes

            @param str channel: channel name

            @return bool: whether channel is selected
        """
        return self.inst.ask(channel.replace(" ", "") + '.selected?' ).split(' = ')[-1] == 'On'

    def is_output_on(self):
        """ Check if device outputs are enabled.

            @return bool: wheter device outputs are enabled
        """
        result = self.inst.ask('OutputEnable?').split()[2]
        return result == 'On'

    def get_temp_by_name(self, name):
        """ Get temperature by name.

            @return float: temperature value
        """
        return self.inst.ask_for_values('{}.value?'.format(name))[0]

    def get_all_outputs(self):
        """ Get a list of all output names

            @return list(str): output names
        """
        names = self.get_channel_names()
        raw = self.inst.ask('getOutputs?').split(', ')
        values = []
        for substr in raw:
            values.append(float(substr))
        return dict(zip(names, values))

    def get_selected_channels(self):
        """ Get all selected channels.

            @return dict: dict of channel_name: bool indicating selected channels
        """
        names = self.get_channel_names()
        values = []
        for channel in names:
                values.append(self.is_channel_selected(channel))
        return dict(zip(names, values))

    def channel_off(self, channel):
        """ Turn off channel.

            @param channel str: name of channel to turn off
        """
        return self.inst.ask('{}.Off'.format(channel)).split(' = ')[1]

    def enable_output(self):
        """ Turn on all outputs.

            @return bool: whether turning on was successful
        """
        if self.is_output_on():
            return True
        else:
            result = self.inst.ask('OutputEnable = On').split()[2]
            return result == 'On'

    def disable_output(self):
        """ Turn off all outputs.

            @return bool: whether turning off was successful
        """
        if self.is_output_on():
            result = self.inst.ask('OutputEnable = Off').split()[2]
            return result == 'Off'
        else:
            return True


#
# All the functions below need to be refactored with multichannel PID in mind
#
#    def get_setpoint(self, channel):
#        return self.inst.ask_for_values('{}.PID.setpoint?'.format(channel))[0]
#
#    def set_setpoint(self, channel, setpoint):
#        return self.inst.ask_for_values('{}.PID.setpoint = {}'.format(channel, setpoint))[0]
#
#    def get_pid_mode(self, channel):
#        return self.inst.ask('{}.PID.Mode?'.format(channel)).split(' = ')[1]
#
#    def set_pid_mode(self, channel, mode):
#        return self.inst.ask('{}.PID.Mode = {}'.format(channel, mode)).split(' = ')[1]
#
#
#    def get_value(self, channel):
#        try:
#            return self.inst.ask_for_values('{}.Value?'.format(channel))[0]
#        except:
#            return NonNonee
#
#    def set_value(self, channel, value):
#        return self.inst.ask_for_values('{}.Value = {}'.format(channel, value))[0]

