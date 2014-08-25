#
# Copyright 2014 ThoughtWorks Deutschland GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import os

__author__ = 'fbernitt'

import subprocess
from provider.fork.adapter import ForkedProcess, Adapter


class ForkRunner(Adapter):
    __slots__ = ('_root_path', '_ports', '_adapter')

    def __init__(self, root_path, adapter):
        if not os.path.isdir(root_path):
            raise ValueError('Root path seems to be invalid: %s' % root_path)

        self._root_path = root_path
        self._ports = set()
        self._adapter = adapter

    def _gnupg_home(self, name):
        return os.path.join(self._root_path, name, 'gnupg')

    def _prepare_env(self, name):
        env = self._adapter.environment(os.path.join(self._root_path, name, 'data'))
        return env

    def initialize(self, name):
        env = self._prepare_env(name)
        self._adapter.initialize_gnupg(name, os.path.join(self._root_path, name, 'data'))
        subprocess.call(self._adapter.setup_command(), close_fds=True, env=env)

    def start(self, name):
        env = self._prepare_env(name)

        port = self._next_available_port()
        self._set_next_port(name, port)
        self._ports.add(port)

        p = subprocess.Popen(self._adapter.run_command(), stdin=subprocess.PIPE, close_fds=True, env=env)

        return ForkedProcess(p, port)

    def _next_available_port(self):
        inital_port = 5000

        port = inital_port
        while port in self._ports:
            port += 1

        return port

    def _set_next_port(self, name, port):
        env = self._prepare_env(name)
        subprocess.call(self._adapter.set_custom_port_command(port), close_fds=True, env=env)
