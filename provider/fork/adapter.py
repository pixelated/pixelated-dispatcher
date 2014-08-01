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
