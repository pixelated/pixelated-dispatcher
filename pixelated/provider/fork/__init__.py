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
import os.path as path

import psutil

from pixelated.provider.base_provider import BaseProvider, _mkdir_if_not_exists


class ForkProvider(BaseProvider):
    CFG_FILE_NAME = 'agent.cfg'

    __slots__ = ('_running', '_runner')

    def __init__(self, runner):
        super(ForkProvider, self).__init__()
        self._running = dict()
        self._runner = runner

    def list_running(self):
        return self._running.keys()

    def start(self, user_config):
        name = user_config.username
        self._start(user_config)

        gnupg_path = path.join(user_config.path, 'gnupg')
        _mkdir_if_not_exists(gnupg_path)

        self._runner.initialize(name)
        process = self._runner.start(name)

        self._running[name] = process

    def stop(self, name):
        self._stop(name)

        self._running[name].terminate()
        del self._running[name]

    def reset_data(self, user_config):
        raise Exception('Not yet implemented')

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
