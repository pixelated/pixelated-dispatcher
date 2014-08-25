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

__author__ = 'fbernitt'

from psutil import Process


class ForkedProcess(object):
    __slots__ = ('_process', 'port')

    def __init__(self, process, port):
        self._process = process
        self.port = port

    def __eq__(self, other):
        return isinstance(other, ForkedProcess) and other._process == self._process

    def terminate(self):
        self._process.stdin.write('quit\n')
        self._process.stdin.close()
        self._process.terminate()

    def memory_usage(self):
        p = Process(self._process.pid)
        mem = p.memory_info()
        return mem.rss


class Adapter(object):
    def initialize(self, name):
        raise NotImplementedError()

    def start(self, name):
        raise NotImplementedError()
