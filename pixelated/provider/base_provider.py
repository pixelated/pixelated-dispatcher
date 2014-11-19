#
# Copyright (c) 2014 ThoughtWorks Deutschland GmbH
#
# Pixelated is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pixelated is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.
from ConfigParser import ConfigParser
import os
import random
import shutil
from os import path
import binascii

import scrypt

from multiprocessing import Process
from pixelated.common import Watchdog
from pixelated.provider import Provider, NotEnoughFreeMemory
from pixelated.exceptions import InstanceNotFoundError
from pixelated.exceptions import InstanceNotRunningError
from pixelated.exceptions import InstanceAlreadyRunningError
from pixelated.exceptions import InstanceAlreadyExistsError


__author__ = 'fbernitt'


class ProviderInitializingException(Exception):
    pass


def _mkdir_if_not_exists(dir, mode=0700):
    if not os.path.exists(dir):
        os.mkdir(dir, mode)


class BaseProvider(Provider):
    CFG_FILE_NAME = 'agent.cfg'

    __slots__ = ('_initializing')

    def __init__(self):
        self._initializing = True

    def initialize(self):
        self._initializing = False

    @property
    def initializing(self):
        return self._initializing

    def _cfg_file_name(self, name):
        return path.join(self._root_path, name, BaseProvider.CFG_FILE_NAME)

    def _data_path(self, user_config):
        return path.join(user_config.path, 'data')

    def _ensure_initialized(self):
        if self.initializing:
            raise ProviderInitializingException()

    def remove(self, user_config):
        self._ensure_initialized()

        if user_config.username in self.list_running():
            raise ValueError('Container %s is currently running. Please stop before removal!' % user_config.username)

        shutil.rmtree(path.join(user_config.path, 'data'))

    def _start(self, user_config):
        name = user_config.username
        if name in self.list_running():
            raise InstanceAlreadyRunningError('instance %s already running' % name)

        if not self._check_enough_free_memory():
                raise NotEnoughFreeMemory('Not enough memory to start instance %s!' % name)

        _mkdir_if_not_exists(self._data_path(user_config))

    def _check_enough_free_memory(self):
        return True

    def _stop(self, name):
        if name not in self.list_running():
            raise InstanceNotRunningError('No running instance named %s' % name)

    def status(self, name):
        if name in self.list_running():
            return {'state': 'running', 'port': self._agent_port(name)}
        else:
            return {'state': 'stopped'}

    def _agent_port(self, name):
        raise NotImplementedError
