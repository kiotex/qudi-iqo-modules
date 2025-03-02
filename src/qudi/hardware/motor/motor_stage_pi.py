# -*- coding: utf-8 -*-

"""
This file contains the hardware control of the motorized stage for PI.

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
import time

from collections import OrderedDict

from qudi.core.module import Base
from qudi.core.configoption import ConfigOption
from qudi.interface.motor_interface import MotorInterface


class MotorStagePI(Base, MotorInterface):
    """
    This is the Interface class to define the controls for the simple
    microwave hardware.

    Example config for copy-paste:

    motorstage_pi:
        module.Class: 'motor.motor_stage_pi.MotorStagePI'
        com_port_pi_xyz: 'ASRL1::INSTR'
        pi_xyz_baud_rate: 9600
        pi_xyz_timeout: 1000
        pi_xyz_term_char: '\n'
        pi_first_axis_label: 'x'
        pi_second_axis_label: 'y'
        pi_third_axis_label: 'z'
        pi_first_axis_ID: '1'
        pi_second_axis_ID: '2'
        pi_third_axis_ID: '3'

        pi_first_min: -0.1 # in m
        pi_first_max: 0.1 # in m
        pi_second_min: -0.1 # in m
        pi_second_max: 0.1 # in m
        pi_third_min: -0.1 # in m
        pi_third_max: 0.1 # in m

        pi_first_axis_step: 1e-7 # in m
        pi_second_axis_step: 1e-7 # in m
        pi_third_axis_step: 1e-7 # in m

        vel_first_min: 1e-5 # in m/s
        vel_first_max: 5e-2 # in m/s
        vel_second_min: 1e-5 # in m/s
        vel_second_max: 5e-2 # in m/s
        vel_third_min: 1e-5 # in m/s
        vel_third_max: 5e-2 # in m/s

        vel_first_axis_step: 1e-5 # in m/s
        vel_second_axis_step: 1e-5 # in m/s
        vel_third_axis_step: 1e-5 # in m/s

    """

    _com_port_pi_xyz = ConfigOption('com_port_pi_xyz', 'ASRL1::INSTR', missing='warn')
    _pi_xyz_baud_rate = ConfigOption('pi_xyz_baud_rate', 9600, missing='warn')
    _pi_xyz_timeout = ConfigOption('pi_xyz_timeout', 1000, missing='warn')
    _pi_xyz_term_char = ConfigOption('pi_xyz_term_char', '\n', missing='warn')
    _first_axis_label = ConfigOption('pi_first_axis_label', 'x', missing='warn')
    _second_axis_label = ConfigOption('pi_second_axis_label', 'y', missing='warn')
    _third_axis_label = ConfigOption('pi_third_axis_label', 'z', missing='warn')
    _first_axis_ID = ConfigOption('pi_first_axis_ID', '1', missing='warn')
    _second_axis_ID = ConfigOption('pi_second_axis_ID', '2', missing='warn')
    _third_axis_ID = ConfigOption('pi_third_axis_ID', '3', missing='warn')

    _min_first = ConfigOption('pi_first_min', -0.1, missing='warn')
    _max_first = ConfigOption('pi_first_max', 0.1, missing='warn')
    _min_second = ConfigOption('pi_second_min', -0.1, missing='warn')
    _max_second = ConfigOption('pi_second_max', 0.1, missing='warn')
    _min_third = ConfigOption('pi_third_min', -0.1, missing='warn')
    _max_third = ConfigOption('pi_third_max', 0.1, missing='warn')

    step_first_axis = ConfigOption('pi_first_axis_step', 1e-7, missing='warn')
    step_second_axis = ConfigOption('pi_second_axis_step', 1e-7, missing='warn')
    step_third_axis = ConfigOption('pi_third_axis_step', 1e-7, missing='warn')

    _vel_min_first = ConfigOption('vel_first_min', 1e-5, missing='warn')
    _vel_max_first = ConfigOption('vel_first_max', 5e-2, missing='warn')
    _vel_min_second = ConfigOption('vel_second_min', 1e-5, missing='warn')
    _vel_max_second = ConfigOption('vel_second_max', 5e-2, missing='warn')
    _vel_min_third = ConfigOption('vel_third_min', 1e-5, missing='warn')
    _vel_max_third = ConfigOption('vel_third_max', 5e-2, missing='warn')

    _vel_step_first = ConfigOption('vel_first_axis_step', 1e-5, missing='warn')
    _vel_step_second = ConfigOption('vel_second_axis_step', 1e-5, missing='warn')
    _vel_step_third = ConfigOption('vel_third_axis_step', 1e-5, missing='warn')
    _vel_default = ConfigOption('vel_default', 3e-3, missing='nothing')


    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    def on_activate(self):
        """ Initialisation performed during activation of the module.
        @return: error code
        """
        self.log.warning("This module has not been tested on the new qudi core."
                         "Use with caution and contribute bug fixed back, please.")

        self.rm = visa.ResourceManager()
        self._serial_connection_xyz = self.rm.open_resource(
            resource_name=self._com_port_pi_xyz,
            baud_rate=self._pi_xyz_baud_rate,
            timeout=self._pi_xyz_timeout)
            #read_termination=b'\x03')

        self.set_velocity({'x': self._vel_default,
                           'y': self._vel_default,
                           'z': self._vel_default})

        return 0


    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        @return: error code
        """
        self._serial_connection_xyz.close()
        self.rm.close()
        return 0


    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.

        @return dict: dict with constraints for the sequence generation and GUI

        Provides all the constraints for the xyz stage  and rot stage (like total
        movement, velocity, ...)
        Each constraint is a tuple of the form
            (min_value, max_value, stepsize)
        """
        constraints = OrderedDict()

        axis0 = {'label': self._first_axis_label,
                 'ID': self._first_axis_ID,
                 'unit': 'm',
                 'ramp': None,
                 'pos_min': self._min_first,
                 'pos_max': self._max_first,
                 'pos_step': self.step_first_axis,
                 'vel_min': self._vel_min_first,
                 'vel_max': self._vel_max_first,
                 'vel_step': self._vel_step_first,
                 'acc_min': None,
                 'acc_max': None,
                 'acc_step': None}

        axis1 = {'label': self._second_axis_label,
                 'ID': self._second_axis_ID,
                 'unit': 'm',
                 'ramp': None,
                 'pos_min': self._min_second,
                 'pos_max': self._max_second,
                 'pos_step': self.step_second_axis,
                 'vel_min': self._vel_min_second,
                 'vel_max': self._vel_max_second,
                 'vel_step': self._vel_step_second,
                 'acc_min': None,
                 'acc_max': None,
                 'acc_step': None}

        axis2 = {'label': self._third_axis_label,
                 'ID': self._third_axis_ID,
                 'unit': 'm',
                 'ramp': None,
                 'pos_min': self._min_third,
                 'pos_max': self._max_third,
                 'pos_step': self.step_third_axis,
                 'vel_min': self._vel_min_third,
                 'vel_max': self._vel_max_third,
                 'vel_step': self._vel_step_third,
                 'acc_min': None,
                 'acc_max': None,
                 'acc_step': None}

        # assign the parameter container for x to a name which will identify it
        constraints[axis0['label']] = axis0
        constraints[axis1['label']] = axis1
        constraints[axis2['label']] = axis2

        return constraints

    def move_rel(self, param_dict):
        """Moves stage in given direction (relative movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.


        @return dict pos: dictionary with the current magnet position
        """

        # There are sometimes connections problems therefore up to 3 attempts are started
        for attempt in range(3):
            try:
                for axis_label in param_dict:
                    step = param_dict[axis_label]
                    self._do_move_rel(axis_label, step)
            except:
                self.log.warning('Motor connection problem! Try again...')
            else:
                break
        else:
            self.log.error('Motor cannot move!')

        #The following two lines have been commented out to speed up
        #pos = self.get_pos()
        #return pos
        return param_dict

    def wait_on_condition(self, condition_str, dt_s=0.2, timeout_s=-1):

        timed_out = False
        t = 0
        t_start = time.perf_counter()
        while not eval(condition_str):

            t = time.perf_counter() - t_start
            if timeout_s >= 0 and t > timeout_s:
                timed_out = True
                break
            time.sleep(dt_s)
            #self.log.debug(f"Waiting for {condition_str}")

        if timed_out:
            self.log.warning(f"Timed out after {t} s waiting for {condition_str}")


    def move_abs(self, param_dict):
        """Moves stage to absolute position

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
                                The values for the axes are in millimeter,
                                the value for the rotation is in degrees.

        @return dict pos: dictionary with the current axis position
        """
        # There are sometimes connections problems therefore up to 3 attempts are started
        for attept in range(3):
            try:
                for axis_label in param_dict:
                    move = param_dict[axis_label]
                    self._do_move_abs(axis_label, move)

                timeout_ms = float(self._pi_xyz_timeout)

                self.wait_on_condition("self._motor_stopped()", dt_s=0.02,
                                       timeout_s=timeout_ms/1000.)
            except:
                self.log.warning('Motor connection problem! Try again...')
            else:
                break
        else:
            self.log.error('Motor cannot move!')

        #The following two lines have been commented out to speed up
        #pos = self.get_pos()
        #return pos
        return param_dict


    def abort(self):
        """Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        constraints = self.get_constraints()
        try:
            for axis_label in constraints:
                self._write_xyz(axis_label,'AB')
            while not self._motor_stopped():
                time.sleep(0.2)
            return 0
        except:
            self.log.error('MOTOR MOVEMENT NOT STOPPED!!!)')
            return -1

    def get_pos(self, param_list=None):
        """ Gets current position of the stage arms

        @param list param_list: optional, if a specific position of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                position is asked.

        @return dict: with keys being the axis labels and item the current
                      position.        """

        constraints = self.get_constraints()
        param_dict = {}
        # unfortunately, probably due to connection problems this specific command sometimes failing
        # although it should run.... therefore some retries are added

        try:
            if param_list is not None:
                for axis_label in param_list:
                    for attempt in range(5):
                        # self.log.debug(attempt)
                        try:
                            pos = int(self._ask_xyz(axis_label,'TT', nchunks=3).split(":",1)[1])  # expect 18 bytes
                            param_dict[axis_label] = pos * 1e-7
                        except:
                            continue
                        else:
                            break
            else:
                for axis_label in constraints:
                    for attempt in range(5):
                        #self.log.debug(attempt)
                        try:
                            #pos = int(self._ask_xyz(axis_label,'TT')[8:])
                            pos = int(self._ask_xyz(axis_label, 'TT', nchunks=3).split(":",1)[1])
                            param_dict[axis_label] = pos * 1e-7
                        except:
                            continue
                        else:
                            break

            #self.log.debug(f"Returning Pos {param_dict}")

            return param_dict
        except:
            self.log.error('Could not find current xyz motor position')
            return -1

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict: with the axis label as key and the status number as item.
        The meaning of the return value is:
        Bit 0: Ready Bit 1: On target Bit 2: Reference drive active Bit 3: Joystick ON
        Bit 4: Macro running Bit 5: Motor OFF Bit 6: Brake ON Bit 7: Drive current active
        """
        constraints = self.get_constraints()
        param_dict = {}
        try:
            if param_list is not None:
                for axis_label in param_list:
                    status = self._ask_xyz(axis_label,'TS', nchunks=3).split(":",1)[1]
                    param_dict[axis_label] = status

                    #self.log.debug(f"return code in movevement: {status}")
                    #self.log.debug(f"Updating status dict: {param_dict}")
            else:
                for axis_label in constraints:
                    status = self._ask_xyz(axis_label, 'TS', nchunks=3).split(":",1)[1]
                    param_dict[axis_label] = status

                    #self.log.debug(f"return code in movevement: {status}")
                    #self.log.debug(f"Updating status dict: {param_dict}")

            return param_dict
        except:
            self.log.error('Status request unsuccessful')
            return -1

    def calibrate(self, param_list=None, direction=1):
        """ Calibrates the stage.

        @param dict param_list: param_list: optional, if a specific calibration
                                of an axis is desired, then the labels of the
                                needed axis should be passed in the param_list.
                                If nothing is passed, then all connected axis
                                will be calibrated.
        @param int direction:   0: positive
                                1: negative
                                2: auto (standard stages)
                                3: negative auto

        After calibration the stage moves to home position which will be the
        zero point for the passed axis.

        @return dict pos: dictionary with the current position of the ac#xis
        """

        if direction not in [0,1,2,3]:
            raise ValueError(f"Unsupported direction id {direction}. Check manual!")

        param_dict = {}
        try:
            for axis_label in param_list:
                self._write_xyz(axis_label,f'FE{int(direction)}')
            self.log.info(f"Motors {param_list} are now slowly homing."
                          " Remember to finish_calibrate() afterwards!")
        except:
            self.log.exception('Calibration did not work: ')

        for axis_label in param_list:
            param_dict[axis_label] = 0.0
        self.move_abs(param_dict)

        pos = self.get_pos()
        return pos

    def finish_calibrate(self, param_list=None):
        """
        Sets the current position as zero. Should be called after the motors
        have stopped after calibrate().
        :param param_list:
        :return:
        """

        if not self._motor_stopped():
            self.log.warning("Motors still moving. Couldn't finish calibration.")
            pos = self.get_pos()
            return pos

        for axis_label in param_list:
            self._write_xyz(axis_label, 'DH')

        pos = self.get_pos()
        return pos


    def get_velocity(self, param_list=None):
        """ Gets the current velocity for all connected axes in m/s.

        @param list param_list: optional, if a specific velocity of an axis
                                    is desired, then the labels of the needed
                                    axis should be passed as the param_list.
                                    If nothing is passed, then from each axis the
                                    velocity is asked.

        @return dict : with the axis label as key and the velocity as item.
            """
        constraints = self.get_constraints()
        param_dict = {}
        try:
            if param_list is not None:
                for axis_label in param_list:
                    vel = int(self._ask_xyz(axis_label, 'TY', nchunks=3).split(":",1)[1]) # expect 17 bytes
                    param_dict[axis_label] = vel * 1e-7
            else:
                for axis_label in constraints:
                    vel = int(self._ask_xyz(axis_label, 'TY', nchunks=3).split(":",1)[1])
                    param_dict[axis_label] = vel * 1e-7
            return param_dict
        except:
            self.log.error('Could not find current axis velocity')
            return -1

    def set_velocity(self, param_dict):
        """ Write new value for velocity in m/s.

        @param dict param_dict: dictionary, which passes all the relevant
                                    parameters, which should be changed. Usage:
                                     {'axis_label': <the-velocity-value>}.
                                     'axis_label' must correspond to a label given
                                     to one of the axis.

        @return dict param_dict2: dictionary with the updated axis velocity
        """
        #constraints = self.get_constraints()
        try:
            for axis_label in param_dict:
                vel = int(param_dict[axis_label] * 1.0e7)
                self._write_xyz(axis_label, 'SV{0:d}'.format(vel))

            #The following two lines have been commented out to speed up
            #param_dict2 = self.get_velocity()
            #retrun param_dict2
            return param_dict

        except:
            self.log.error('Could not set axis velocity')
            return -1



########################## internal methods ##################################

    def _write_xyz(self, axis, command):
        """this method just sends a command to the motor! DOES NOT RETURN AN ANSWER!
        @param axis string: name of the axis that should be asked

        @param command string: command

        @return error code (0:OK, -1:error)
        """
        constraints = self.get_constraints()
        try:
            #self.log.info(constraints[axis]['ID'] + command + '\n')

            self._serial_connection_xyz.write(constraints[axis]['ID'] + command + '\n')
            _ = self._read_answer_xyz()
            return 0

        except BaseException:
            self.log.exception('Command was no accepted: ')
            return -1

    def _read_answer_xyz(self):
        """ Read answer if number of chunks is not known ahead of call.
        Try to avoid, may cause instability.
        For a certain command n_chunks should be constant. -> Use ._aks_xyz()
        @return answer string: answer of motor
        """

        finished_reading = False
        timed_out = False
        answer = ''

        timeout_ms = float(self._pi_xyz_timeout)

        t = 0
        timeout_s = float(timeout_ms) / 1000
        t_start = time.perf_counter()

        while not finished_reading and not timed_out:

            #self.log.debug(f"[{t} s] Fetching serial answer. So far: {answer}")
            t = time.perf_counter() - t_start
            if timeout_s >= 0 and t > timeout_s:
                timed_out = True
                break
            try:
                answer = answer + self._serial_connection_xyz.read()[:-1]
            except:
                finished_reading = True
                #self.log.debug("Done.")

        if timed_out:
            self.log.warning(f"Timed out after {t} s while serial read")

        return answer

    def _ask_xyz(self, axis, question, nchunks=1):

        constraints = self.get_constraints()
        #self.log.debug(f"Asking {constraints[axis]['ID'] + question} for {nchunks} chunks...")
        self._serial_connection_xyz.write(str(constraints[axis]['ID']) + question + '\n')

        str_ret = ""

        for i in range(nchunks):
            raw_ret = self._serial_connection_xyz.read()
            str_ret += str(raw_ret).replace("\r", "").replace("\n", "")
            #self.log.debug(f"Chunk {i}: {str_ret}")

        #self.log.debug(f"Finished response: {str_ret}")

        return str_ret

    def _do_move_rel(self, axis, step):
        """internal method for the relative move

        @param axis string: name of the axis that should be moved

        @param float step: step in meter

        @return str axis: axis which is moved
                move float: absolute position to move to
        """
        constraints = self.get_constraints()
        if not(abs(constraints[axis]['pos_step']) < abs(step)):
            self.log.warning('Cannot make the movement of the axis "{0}"'
                'since the step is too small! Ignore command!')
        else:
            current_pos = self.get_pos(axis)[axis]
            move = current_pos + step
            self._do_move_abs(axis, move)
        return axis, move

    def _do_move_abs(self, axis, move):
        """internal method for the absolute move in meter

        @param axis string: name of the axis that should be moved

        @param float move: desired position in meter

        @return str axis: axis which is moved
                move float: absolute position to move to
        """
        constraints = self.get_constraints()
        #self.log.info(axis + 'MA{0}'.format(int(move*1e8)))
        if not(constraints[axis]['pos_min'] <= move <= constraints[axis]['pos_max']):
            self.log.warning('Cannot make the movement of the axis "{0}"'
                'since the border [{1},{2}] would be crossed! Ignore command!'
                ''.format(axis, constraints[axis]['pos_min'], constraints[axis]['pos_max']))
        else:
            self._write_xyz(axis,'MA{0}'.format(int(move*1e7)))  # 1e7 to convert meter to SI units
            #self._write_xyz(axis, 'MP')
        return axis, move



    def _in_movement_xyz(self):
        """this method checks if the magnet is still moving and returns
        a dictionary which of the axis are moving.

        @return: dict param_dict: Dictionary displaying if axis are moving:
        0 for immobile and 1 for moving
        """
        constraints=self.get_constraints()
        param_dict = {}
        for axis_label in constraints:
            try:
                tmp0 = int(self._ask_xyz(constraints[axis_label]['label'],'TS', nchunks=3)[8:])
            except Exception as e:
                self.log.exception("Failed: ")
            #self.log.debug(f"return code in movevement: {tmp0}")
            param_dict[axis_label] = tmp0%2
            #self.log.debug(f"Updating movement dict: {param_dict}")

        return param_dict

    def _motor_stopped(self):
        """this method checks if the magnet is still moving and returns
            False if it is moving and True of it is immobile

            @return: bool stopped: False for immobile and True for moving
                """
        param_dict=self._in_movement_xyz()
        stopped=True
        for axis_label in param_dict:
            if param_dict[axis_label] != 0:
                self.log.debug(axis_label + ' is moving')
                stopped = False
        return stopped



            #########################################################################################
#########################################################################################
#########################################################################################







