# -*- coding: utf-8 -*-

"""
This module provides a dummy wavemeter hardware module that is useful for
troubleshooting logic and gui modules.

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

import random
import scipy.constants as sc
from PySide2 import QtCore
from qudi.core.threadmanager import ThreadManager

from qudi.core.configoption import ConfigOption
from qudi.interface.wavemeter_interface import WavemeterInterface
from qudi.util.mutex import Mutex


class HardwarePull(QtCore.QObject):
    """ Helper class for running the hardware communication in a separate
    thread.
    """

    def __init__(self, parentclass):
        super().__init__()

        # remember the reference to the parent class to access functions ad settings
        self._parentclass = parentclass

    def handle_timer(self, state_change):
        """ Threaded method that can be called by a signal from outside to start
            the timer.

        @param bool state_change: (True) starts timer, (False) stops it.
        """

        if state_change:
            self.timer = QtCore.QTimer()
            self.timer.timeout.connect(self._measure_thread)
            #QTimer needs the measurement_timing in miliseconds
            self.timer.start(self._parentclass._measurement_timing/10**(-3))
        else:
            if hasattr(self, 'timer'):
                self.timer.stop()

    def _measure_thread(self):
        """ The threaded method querying the data from the wavemeter. """

        range_step = 0.1e-9 #currently for nm deviation not for frequency

        # update as long as the status is busy
        if self._parentclass.is_running:
            # get the current wavelength from the wavemeter
            #self._parentclass._current_wavelength += random.uniform(-range_step, range_step)
            self._parentclass.current_wavelength += random.uniform(-range_step, range_step)
        #todo emit signal if new measurment value is available (as it's the case in real hardware) and not directly update wavelength in parentclass
        #todo from time to time also simulate some error?


class WavemeterDummy(WavemeterInterface):
    """ Dummy hardware class to simulate the controls for a wavemeter.

    Example config for copy-paste:

    temp_tsys:
        module.Class: 'wavemeter_dummy.WavemeterDummy'
        measurement_timing: 10.0

    """
    #_threaded = True #todo need for that at all? Or not necessary due to sperate measurement thread?

    # config opts
    _measurement_timing = ConfigOption('measurement_timing', 10.e-3)

    sig_handle_timer = QtCore.Signal(bool)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

        # the current wavelength read by the wavemeter in nm (vac)
        self.__current_wavelength = float()
        self._is_running = False
        # Check if thread manager can be retrieved from the qudi main application #todo set to the right position? or better in activate?
        self.thread_manager = ThreadManager.instance()
        if self.thread_manager is None:
            raise RuntimeError('No thread manager found. Qudi application is probably not running.')

    def on_activate(self):
        """ Activate module.
        """
        self.__current_wavelength = float()
        self.log.warning("This module has not been tested on the new qudi core."
                         "Use with caution and contribute bug fixed back, please.")

        # Get a newly spawned thread (PySide2.QtCore.QThread) from the thread manager and give it a name
        # create an independent thread for the hardware communication
        self.hardware_thread = self.thread_manager.get_new_thread('measure_thread')

        # create an object for the hardware communication and let it live on the new thread
        self._hardware_pull = HardwarePull(self)
        self._hardware_pull.moveToThread(self.hardware_thread)

        # connect the signals in and out of the threaded object
        self.sig_handle_timer.connect(self._hardware_pull.handle_timer)
        # self._hardware_pull.sig_wavelength.connect(self.handle_wavelength)

        # start the event loop for the hardware
        self.hardware_thread.start()

        # start automatically acquisition
        self.start_acquisition()

    def on_deactivate(self):
        """ Deactivate module.
        """
        self.stop_acquisition()
        self.thread_manager.quit_thread('measure_thread')
        self.sig_handle_timer.disconnect()
        self._hardware_pull.sig_wavelength.disconnect()

    @property
    def is_running(self):
        """
        Read-only flag indicating if the data acquisition is running.

        @return bool: Data acquisition is running (True) or not (False)
        """
        return self._is_running

    @is_running.setter
    #todo documentation needed here?
    def is_running(self, run):
        if self._is_running and not run:
            self._is_running = False
        elif not self._is_running and run:
            self._is_running = True
        return

    #todo check if this property is necessary or does it just duplication of get_wavelength()
    @property
    def current_wavelength(self):
        return float(self.__current_wavelength)

    @current_wavelength.setter
    def current_wavelength(self, wavelength):
        error_dict = {0: 'Error no value as acquisition stopped',
                      -1: 'Error no signal, wavlength meter has not detected any signal.',
                      -2: 'Error bad signal, wavelength meter has not detected calculatable signal',
                      -3: 'Error low signal, signal is too small to be calculated properly',
                      -4: 'Error big signal, signal is too large to be calculated properly',
                      -5: 'Error wavelength meter missing',
                      -6: 'Error not available',
                      -7: 'Nothing changed',
                      -8: ' Error no pulse, the detected signal could not be divided in separated '
                          'pulses',
                      -13: 'Error division by 0',
                      -14: 'Error out of range',
                      -15: 'Error unit not available'}
        if wavelength > 0 and wavelength not in error_dict:
            self.__current_wavelength = wavelength
            return
        elif wavelength in error_dict:
            self.log.error(error_dict[self.current_wavelength])
            return
        else:
            self.log.error('No valid wavelength/WLM error')
            return

    #############################################
    # Methods of the main class
    #############################################
    def start_acquisition(self):
        """ Method to start the wavemeter software.

        @return int: error code (0:OK, -1:error)

        Also the actual threaded method for getting the current wavemeter reading is started.
        """
        # first check its status
        if self.is_running:
            self.log.error('Wavemeter busy')
            return -1

        self._is_running = True
        #todo self.module_state.lock() does not work

        # actually start the wavemeter
        self.log.info('starting Wavemeter')

        # set initial wavemeter value randomly between 4200nm and 1100nm in SI units
        self.current_wavelength = round(random.uniform(420, 1100), 2)*10**(-9)

        #todo if placing here the creation of the thread: Why can't I create new thread in starting acquisition for the second time

        # create an independent thread for the hardware communication
        # self.hardware_thread = self.thread_manager.get_new_thread('measure_thread')
        #
        # # create an object for the hardware communication and let it live on the new thread
        # self._hardware_pull = HardwarePull(self)
        # self._hardware_pull.moveToThread(self.hardware_thread)
        #
        # # connect the signals in and out of the threaded object
        # self.sig_handle_timer.connect(self._hardware_pull.handle_timer)
        #
        # # start the event loop for the hardware
        # self.hardware_thread.start()

        # start the measuring thread
        self.sig_handle_timer.emit(True)

        return 0

    def stop_acquisition(self):
        """ Stops the Wavemeter from measuring and kills the thread that queries the data.

        @return int: error code (0:OK, -1:error)
        """

        # check status just for a sanity check
        if not self.is_running:
            self.log.warning('Wavemeter was already stopped, stopping it anyway!')
        else:
            # stop the measurement thread
            self.sig_handle_timer.emit(False)
            # set the wavelength to no value again
            #self.current_wavelength = float()
            # set status to idle again
            self.is_running = False
            #todo self.module_state.unlock() does not work

        # Stop the actual wavemeter measurement
        self.log.warning('stopping Wavemeter')

        #self.thread_manager.quit_thread('measure_thread')
        #self.sig_handle_timer.disconnect()
        self.is_running = False

        return 0

    def get_current_wavelength(self, kind="vac"):
        """ This method returns the current wavelength.

        @param string kind: can either be "vac" or "air" for the wavelength in vacuum or air, respectively.

        @return float: wavelength (or negative value for errors)
        """
        error_dict = {0: 'Error no value as acquisition stopped',
                      -1: 'Error no signal, wavlength meter has not detected any signal.',
                      -2: 'Error bad signal, wavelength meter has not detected calculatable signal',
                      -3: 'Error low signal, signal is too small to be calculated properly',
                      -4: 'Error big signal, signal is too large to be calculated properly',
                      -5: 'Error wavelength meter missing',
                      -6: 'Error not available',
                      -7: 'Nothing changed',
                      -8: ' Error no pulse, the detected signal could not be divided in separated '
                          'pulses',
                      -13: 'Error division by 0',
                      -14: 'Error out of range',
                      -15: 'Error unit not available'}

        if self.current_wavelength > 0 and self.current_wavelength not in error_dict:
            #todo set here the current wavelength?
            if kind in "vac":
                # for vacuum just return the current wavelength
                #return float(self._current_wavelength)
                return self.current_wavelength
            if kind in "air":
                # for air we need the convert the current wavelength.
                #return float(self.convert_unit(self._current_wavelength, 'vac', 'air'))
                return self.convert_unit(self.current_wavelength, 'vac', 'air')
        elif self.current_wavelength in error_dict:
            self.log.error(error_dict[self.current_wavelength])
            return self.current_wavelength
        else:
            self.log.error('No valid wavelength/WLM error')
            return

    def handle_wavelength(self, wavelength):
        """ Function to save the wavelength, when it comes in with a signal.
        """
        self._current_wavelength = wavelength

    def get_timing(self):

        """ Get the timing of the internal measurement thread.

        @return float: clock length in second (SI unit)
        """
        return self._measurement_timing

    def set_timing(self, timing):
        """ Set the timing of the internal measurement thread.

        @param float timing: clock length in second (SI unit)

        @return int: error code (0:OK, -1:error)
        """
        self._measurement_timing = float(timing)
        # update the measurement timing in the thread
        self.sig_handle_timer.emit(True)
        return 0

    def convert_unit(self, value, unit_from, unit_to):
        refractive_index_air = 1.0003
        units = {'vac', 'air', 'freq'}
        if unit_from and unit_to in units:
            if unit_from == unit_to:
                return value
            if unit_from == 'vac' and unit_to == 'freq':
                return sc.lambda2nu(value)
            if unit_from == 'vac' and unit_to == 'air':
                return value/refractive_index_air
            if unit_from == 'freq' and unit_to == 'vac':
                return sc.nu2lambda(value)
            if unit_from == 'freq' and unit_to == 'air':
                return sc.nu2lambda(value)/refractive_index_air
            if unit_from == 'air' and unit_to == 'vac':
                return value*refractive_index_air
            if unit_from == 'air' and unit_to == 'freq':
                return sc.lambda2nu(value*refractive_index_air)
        else:
            return self.log.error('not allowed unit(s)')



