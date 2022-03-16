# -*- coding: utf-8 -*-

"""
Combine two hardware switches into one.

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

import time
import numpy as np

from qudi.interface.microwave_interface import MicrowaveConstraints
from qudi.util.enums import SamplingOutputMode
from qudi.interface.finite_sampling_input_interface import FiniteSamplingInputConstraints
from qudi.core.configoption import ConfigOption
from qudi.core.connector import Connector
from qudi.core.module import Base

class MicrowaveInterface(Base):
    pass

class FiniteSamplingInputInterface(Base):
    pass

class OdmrMwExtTriggerInterfuse(MicrowaveInterface, FiniteSamplingInputInterface):
    """ Methods to control slow (mechanical) laser switching devices.
    This interfuse in particular combines two switches into one.
    """

    # connectors for the devices to be combined
    finite_sampling_input = Connector(interface='FiniteSamplingInputInterface')
    microwave = Connector(interface='MicrowaveInterface')

    _default_interface = ConfigOption(name='default_interface',
                                         default='MicrowaveInterface',
                                         missing='nothing')

    def on_activate(self):
        """ Activate the module and fill status variables.
        """
        self._interface = self._default_interface

    def on_deactivate(self):
        """ Deactivate the module and clean up.
        """
        pass

    def __getattr__(self, name):
        print(name)

        #if name == '_interface' or name == 'interface':
        #    return self._default_interface

        if self._interface == 'FiniteSamplingInputInterface':
            return getattr(self.finite_sampling_input(), name)
        elif self._interface == 'MicrowaveInterface':
            return getattr(self.microwave(), name)


    def acquire_frame(self, frame_size=None):
        scanner = self.finite_sampling_input()
        with self._thread_lock:
            with scanner._thread_lock:
                if frame_size is None:
                    buffered_frame_size = None
                else:
                    buffered_frame_size = self._frame_size
                    self.set_frame_size(frame_size)

                self.start_buffered_acquisition()

                self.microwave().trigger()

                data = self.get_buffered_samples(self._frame_size)
                self.stop_buffered_acquisition()

                if buffered_frame_size is not None:
                    self._frame_size = buffered_frame_size
                return data
