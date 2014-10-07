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

from pixelated.provider import Provider, NotEnoughFreeMemory
from pixelated.exceptions import InstanceNotFoundError
from pixelated.exceptions import InstanceNotRunningError
from pixelated.exceptions import InstanceAlreadyRunningError
from pixelated.exceptions import InstanceAlreadyExistsError


__author__ = 'fbernitt'


class ProviderInitializingException(Exception):
    pass


class AgentConfig(object):
    __slots__ = ('name', 'hashed_password', 'salt')

    SALT_HASH_LENGHT = 128

    @classmethod
    def _hash_password(cls, password):
        salt = binascii.hexlify(str(random.getrandbits(128)))
        bytes = binascii.hexlify(scrypt.hash(password, salt))
        return salt, bytes

    def __init__(self, name, password, hashed_password=None, salt=None):
        self.name = name
        if password is None:
            self.salt = salt
            self.hashed_password = hashed_password
        else:
            str_pwd = str_password(password)
            self.salt, self.hashed_password = AgentConfig._hash_password(str_pwd)

    @classmethod
    def read_from(cls, filename):
        cfg = ConfigParser()
        cfg.read(filename)

        name = cfg.get('agent', 'name')
        hashed_password = cfg.get('agent', 'hashed_password')
        salt = cfg.get('agent', 'salt')
        return AgentConfig(name, password=None, hashed_password=hashed_password, salt=salt)

    def write_to(self, fd):
        parser = ConfigParser()

        parser.add_section('agent')
        parser.set('agent', 'name', self.name)
        parser.set('agent', 'hashed_password', self.hashed_password)
        parser.set('agent', 'salt', self.salt)

        parser.write(fd)


def _mkdir_if_not_exists(dir, mode=0700):
    if not os.path.exists(dir):
        os.mkdir(dir, mode)


def str_password(password):
    return password if type(password) != unicode else password.encode('utf8')


class BaseProvider(Provider):
    CFG_FILE_NAME = 'agent.cfg'

    __slots__ = ('_root_path', '_agents', '_initializing')

    def __init__(self, root_path):
        self._root_path = root_path
        if not os.path.exists(root_path):
            raise Exception('%s does not exist' % root_path)
        if not os.path.isdir(root_path):
            raise Exception('%s seems to be a file' % root_path)

        self._agents = []
        self._autodiscover()
        self._initializing = True

    def initialize(self):
        self._initializing = False

    @property
    def initializing(self):
        return self._initializing

    def _cfg_file_name(self, name):
        return path.join(self._root_path, name, BaseProvider.CFG_FILE_NAME)

    def _load_config(self, name):
        filename = self._cfg_file_name(name)
        return AgentConfig.read_from(filename)

    def _create_config_file(self, name, password):
        cfg_file = self._cfg_file_name(name)
        with open(cfg_file, 'w') as file:
            AgentConfig(name, password).write_to(file)

    def _autodiscover(self):
        dirs = [f for f in os.listdir(self._root_path) if os.path.isdir(os.path.join(self._root_path, f))]
        for dir in dirs:
            self._agents.append(dir)

    def add(self, name, password):
        self._ensure_initialized()

        if name in self._agents:
            raise InstanceAlreadyExistsError('Instance %s already exists!' % name)
        self._agents.append(name)

        _mkdir_if_not_exists(self._instance_path(name))
        _mkdir_if_not_exists(path.join(self._instance_path(name), 'data'))

        self._create_config_file(name, password)

    def _instance_path(self, name):
        return path.join(self._root_path, name)

    def _ensure_initialized(self):
        if self.initializing:
            raise ProviderInitializingException()

    def remove(self, name):
        self._ensure_initialized()

        if name in self.list_running():
            raise ValueError('Container %s is currently running. Please stop before removal!' % name)

        self._agents.remove(name)
        shutil.rmtree(path.join(self._root_path, name))

    def list(self):
        self._ensure_initialized()
        return self._agents

    def authenticate(self, name, password):
        self._ensure_initialized()

        cfg = self._load_config(name)

        hashed_password = binascii.hexlify(scrypt.hash(str_password(password), cfg.salt))

        return cfg.hashed_password == hashed_password

    def _start(self, name):
        if name not in self._agents:
            raise InstanceNotFoundError('No instance named %s' % name)
        if name in self.list_running():
            raise InstanceAlreadyRunningError('instance %s already running' % name)

        if not self._check_enough_free_memory():
                raise NotEnoughFreeMemory('Not enough memory to start instance %s!' % name)

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
