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
import os

__author__ = 'fbernitt'

import subprocess
from pixelated.provider.fork.adapter import ForkedProcess, Adapter


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
