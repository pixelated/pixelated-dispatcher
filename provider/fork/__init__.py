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
import os.path as path

import psutil

from provider.base_provider import BaseProvider, _mkdir_if_not_exists


class ForkProvider(BaseProvider):
    CFG_FILE_NAME = 'agent.cfg'

    __slots__ = ('_running', '_runner')

    def __init__(self, root_path, runner):
        super(ForkProvider, self).__init__(root_path)
        self._running = dict()
        self._runner = runner

    def add(self, name, password):
        super(ForkProvider, self).add(name, password)

        gnupg_path = path.join(self._instance_path(name), 'gnupg')
        _mkdir_if_not_exists(gnupg_path)

    def list_running(self):
        return self._running.keys()

    def start(self, name):
        self._start(name)

        self._runner.initialize(name)
        process = self._runner.start(name)

        self._running[name] = process

    def stop(self, name):
        self._stop(name)

        self._running[name].terminate()
        del self._running[name]

    def _agent_port(self, name):
        return self._running[name].port

    def memory_usage(self):
        usage = 0
        agents = []
        for name, process in self._running.iteritems():
            usage += process.memory_usage()
            agents.append({'name': name, 'memory_usage': process.memory_usage()})

        avg = usage / len(agents) if len(agents) > 0 else 0

        return {'total_usage': usage, 'average_usage': avg, 'agents': agents}

    def _check_enough_free_memory(self):
        needed = self.memory_usage()['average_usage']
        free = self._free_memory()

        return needed < free

    def _free_memory(self):
        return psutil.virtual_memory().free