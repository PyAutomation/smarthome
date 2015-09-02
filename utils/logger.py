#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'Artem_Krutalevich'

import os
from abc import ABCMeta, abstractmethod
# TODO: replace with temp worker module


class EnvironmentHandler(object):

    __defined_logpath = None

    @staticmethod
    def _propagate_environment(logs_path='/tmp/logs/', run_name='run', debug=False):
        """
        Sets up the logpath and run name prefix.
        :param logs_path: desired path to store session logs
        :param run_name: desired prefix to add for the logs directory
        :param debug: not yet implemented
        :return: full logs path for the session
        """
        if EnvironmentHandler.__defined_logpath:
            return EnvironmentHandler.__defined_logpath

        from smarthome.utils.generic import GenericUtils

        __cur_date = GenericUtils.get_current_date()
        __cur_time = GenericUtils.get_current_time()
        __path_timestamp = '{}_{}-{}-{}_{}-{}-{}'.format(run_name,
                                                         __cur_date.month,
                                                         __cur_date.day,
                                                         __cur_date.year,
                                                         __cur_time.hour,
                                                         __cur_time.minute,
                                                         __cur_time.second)
        __full_logs_path = os.path.join(logs_path, __path_timestamp)

        if not os.path.exists(__full_logs_path):
            try:
                os.makedirs(__full_logs_path)
            except:
                raise IOError('Failed create logs directory {}'.format(__full_logs_path))

        EnvironmentHandler.__defined_logpath = __full_logs_path

        return __full_logs_path


class Logger(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def log_c(self, msg):
        pass


class LogLocal(Logger):

    def __init__(self):
        super(Logger, self).__init__()

    @staticmethod
    def log_c(msg='', level=2):
        import logging

        logs_path = EnvironmentHandler._propagate_environment()
        log_file = os.path.join(logs_path, 'operations.log')
        error_file = os.path.join(logs_path, 'errors.log')

        formatter = logging.Formatter('[%(asctime)s]# %(levelname)-8s # %(message)s')

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        logfile_handler = logging.FileHandler(log_file, 'a')
        logfile_handler.setFormatter(formatter)

        error_handler = logging.FileHandler(error_file, 'a')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)

        root = logging.getLogger()
        if not root.handlers:
            root.addHandler(console_handler)
            root.addHandler(logfile_handler)
            root.addHandler(error_handler)
        root.setLevel(logging.DEBUG)

        levels = {1: root.debug, 2: root.info, 3: root.warning, 4: root.error, 5: root.critical, 6: root.exception}
        if level in levels:
            levels[level](msg)
