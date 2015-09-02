#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = 'Artem_Krutalevich'


# Ports and connectors constants
DEFAULT_PORT = 22
DEFAULT_PORT_SSH = 22

PORT_PATTERN = '\d+'
SINGLE_WORD_PATTERN = '^\w+$'
IP_PATTERN = '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
PORT_RESOLVE_PATTERNS = ('\d+(?=[,\.:$])', '(?<=,|\.|:)\d+')
LOGIN_RESOLVE_PATTERNS = ('(?<=^)\D{1}\w*(?=[,\.:$])', '(?<=,|\.|:)\D{1}\w*(?=$)', '^\D{1}\w*(?=$)')
KNOWN_LOGINS = ['ddn', 'user']

import sys
import os

from smarthome.utils.logger import LogLocal as Logger





# Setting up path to access external ssh and ping modules
THIS_FILE_PATH = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = THIS_FILE_PATH.split('tools')[0]
CLUSTER_DIR = os.path.join(LIB_DIR, 'clusterlibs')
sys.path.append(CLUSTER_DIR)


def check_preconditions(argparser_func):
    """
    Checks preconditions to run the script: 1)rsync path 2)rsync version 3)python version
    Used as a wrapper to commandline arguments validator
    """
    from sys import version

    def verify_rsync_and_python_versions():
        # Check that Python version is 2.7
        if float(version[:3]) != 2.7:
            raise EnvironmentError('Tried to run on Python {}. Script needs Python 2.7 only!'.format(version[:3]))

        # Check that rsync is installed and its version is 3.0 or higher
        response = Runner.run_local_cmd('which rsync', silent=1)
        rsync_path = GenericUtils.search_pattern(response, '^/.+')
        if not rsync_path:
            raise EnvironmentError('No rsync utility is found on the system! Install rsync!')

        response = Runner.run_local_cmd('{} --version'.format(rsync_path), silent=1)
        rsync_ver = GenericUtils.search_pattern(response, '(?<=^)\d+.\d+', flatten_array=False)
        if float(rsync_ver) < 3.0:
            raise EnvironmentError('Script needs rsync 3.0 or greater, but got {}'.format(rsync_ver))

        return argparser_func()
    return verify_rsync_and_python_versions


class Runner(object):
    """ A class with helping static method for running local shell commands """

    @staticmethod
    def run_local_cmd(cmd, silent=0, die_on_errors=True):
        """
        Local shell command runner method
        :param cmd: a command to execute
        :param silent: the flag defines output of command and result to console
        :param die_on_errors: the flag defines if the script can go on after command failed running
        :return: stdout if die_on_errors is True (no need to check stderr, script will raise with stack trace on fail)
                 otherwise returns dictionary with corresponding keys: 'stdout', 'stderr', 'return_code'
        """
        import subprocess
        # Default log level is 2 (info). If silent=1, then silent-1 will stand for debug mode
        if silent not in range(0, 2): silent = 0

        Logger.log_c('Running command: \"{cmd}\"'.format(cmd=cmd), 2-silent)
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        stdout, stderr = process.communicate()
        Logger.log_c('Got response: {resp}'.format(resp=stdout.strip()), 2-silent)
        return_code = process.returncode

        # Ensure that we didn't face any problems running a command!
        if (return_code != 0 or stderr) and die_on_errors:
            Logger.log_c('Return code: \"{}\", STDERR: \"{}\" running \"{}\"'.format(return_code, stderr, cmd), 5)
            raise OSError('Got error running command \"{}\"'.format(cmd))

        stdout_array = map(lambda x: x.strip(), stdout.splitlines())
        if die_on_errors:
            return stdout_array
        else:
            return {'stdout': stdout_array, 'stderr': stderr, 'return_code': return_code}


class SyncerUtils(object):
    """ A class with helping static methods meant only for syncer usage purpose """

    @staticmethod
    def define_target_connection_settings(arg):
        """
        Parses the last commandline argument to collect login, port, hostname/ip, remote path
        :param arg: the last arg in command line, defined by argparse
        :return: login, port, host, path
        """
        try:
            login_port_set, host_path_set = arg.split('@')
        except:
            raise LookupError('Format error for target login-host set: {} Expected \"login@host\"'.format(arg))

        # Store the provided login and port separately
        target_login = SyncerUtils.resolve_login_port_set(login_port_set, 'login')
        target_port = SyncerUtils.resolve_login_port_set(login_port_set, 'port')

        # Define essential attributes for the syncer config
        host_path_set = host_path_set.split(':')
        target_host = GenericUtils.make_array(host_path_set[0])
        if len(host_path_set) > 1 and host_path_set[1]:
            target_path = host_path_set[1]
        else:
            target_path = '~/'
        Logger.log_c('Host set: {} {} {} {}'.format(target_login, target_port, target_host, target_path), 1)

        return target_login, target_port, target_host, target_path

    @staticmethod
    def resolve_login_port_set(string, wanted):
        patterns = {'login': LOGIN_RESOLVE_PATTERNS, 'port': PORT_RESOLVE_PATTERNS}
        match = None
        for pattern in patterns[wanted]:
            match = GenericUtils.search_pattern(string, pattern, obligatory=False)
            if match:
                break
        if not match:
            if wanted == 'login':
                raise LookupError('Cannot define login!')
        if wanted == 'port':
            match = GenericUtils.validate_port(match)
        return match

    @staticmethod
    def probe_host(host, port):
        return True


class GenericUtils(object):
    """ A class with useful static methods, meant for generic usage """
    @staticmethod
    def get_current_date():
        import datetime
        now = datetime.datetime.now()
        return datetime.date(now.year, now.month, now.day)

    @staticmethod
    def get_current_time():
        import datetime
        now = datetime.datetime.now()
        return datetime.time(now.hour, now.minute, now.second)

    @staticmethod
    def collect_ips(ips):
        ips_found = []
        for supposed_host in GenericUtils.make_array(ips, get_unique=True):
            ips_found.append(GenericUtils.search_pattern(supposed_host, IP_PATTERN, obligatory=0))
        return list(set(filter(None, ips_found)))

    @staticmethod
    def search_pattern(input_for_search, pattern, obligatory=1, flatten_array=True):
        """
        Searches for certain pattern as string or regexp in supplied string ao array of strings
        :param input_for_search: string or array of strings to search in
        :param pattern: string or regexp for search
        :param obligatory: flag to expect only successful search, die if nothing found.
        :param flatten_array: flag to get rid of duplicates in the initial array
        :return: first found string that matches the search pattern
        """
        import re
        array = GenericUtils.make_array(input_for_search, get_unique=flatten_array)
        # Ensure the initial array is not empty when we need to find something
        if not array and obligatory:
            raise LookupError('Input data type for search is empty!')
        found = None
        for line in array:
            result = re.search(pattern, line)
            if result:
                found = result.group()
                Logger.log_c('Found pattern {}'.format(found), 1)
                break
        if not found and obligatory:
            raise LookupError('Expected pattern {} not found in {}'.format(pattern, array))
        else:
            Logger.log_c('Nothing found in array {}'.format(array), 1)
        return found

    @staticmethod
    def get_current_user():
        """ Get current unix user """
        response = Runner.run_local_cmd('whoami', silent=1)
        return GenericUtils.search_pattern(response, SINGLE_WORD_PATTERN).strip()

    @staticmethod
    def validate_port(port):
        """ Validate supplied port and return default ssh port (22) if the supplied one is invalid """
        validated_port = GenericUtils.search_pattern(str(port), PORT_PATTERN, obligatory=0)
        if not validated_port or int(validated_port) not in range(1, 65537):
            return DEFAULT_PORT
        return int(validated_port)

    @staticmethod
    def get_system_users(mind_root=1, known_logins=True):
        """
        Get existing users on the system
        :param mind_root: adds root in first place of return array
        :param known_logins: adds preexisting known users to the list
        :return: list of unique user names
        """
        response = Runner.run_local_cmd('users', silent=1)
        users = GenericUtils.make_array(response, get_unique=True)
        if known_logins:
            list(set(map(lambda x: users.append(x), KNOWN_LOGINS)))
        if mind_root and 'root' not in users:
            users.insert(0, 'root')
        return users

    @staticmethod
    def make_array(source, get_unique=False, *args):
        """
        Makes an array (list) of any items from args
        :param source: Any homogeneous type. Array must contain items of same type.
        :param get_unique: Get rid of duplicates in the output array.
        :param args: Extra list that must contain items of same type.
        :return: Array of strings, contains split and stripped items.
        """
        # Ensure we acquired valid data to search in:
        array = []
        if type(source) == str or type(source) == int:
            array = GenericUtils.__array_from_string(str(source))
        elif type(source) == list or type(source) == tuple:
            array = GenericUtils.__array_from_list_or_tuple(source)
        elif type(source) == dict:
            array = GenericUtils.__array_from_dictionary(source)

        array += GenericUtils.__array_from_list_or_tuple(args)
        array = filter(None, array)
        if get_unique:
            return list(set(array))
        return array

    @classmethod
    def __array_from_string(cls, source):
        """ Helping internal sub that splits, strips strings and returns array of them """
        return map(lambda x: str(x).strip(), source.split())

    @classmethod
    def __array_from_list_or_tuple(cls, source):
        """ Helping internal sub that splits, strips strings in array or tuple and returns one combined array """
        array = []
        for string in map(lambda x: str(x).strip(), source):
            array += string.split()
        return array

    @classmethod
    def __array_from_dictionary(cls, source):
        """
        Helping internal sub that splits, strips items in dict and returns one combined array.
        For the output array removes duplicates and None items.
        """
        array = []
        for items_set in source.items():
            array += GenericUtils.__array_from_list_or_tuple(items_set)
        return list(set(filter(None, array)))