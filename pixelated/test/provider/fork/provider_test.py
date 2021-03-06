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
from collections import namedtuple
import unittest
import os
import stat
from os.path import isdir, join, isfile
from tempfile import NamedTemporaryFile

from tempdir import TempDir
from mock import MagicMock, patch

from pixelated.exceptions import *
from pixelated.provider import NotEnoughFreeMemory
from pixelated.provider.fork import ForkProvider
from pixelated.provider.fork.adapter import Adapter
from pixelated.provider.fork.fork_runner import ForkedProcess
from pixelated.users import UserConfig


class ForkProviderTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = TempDir()
        self.root_path = self._tmpdir.name
        self.runner = MagicMock(spec=Adapter)
        self.provider = ForkProvider(self.runner)
        self.provider.initialize()

    def tearDown(self):
        self._tmpdir.dissolve()

    def test_instances_can_be_removed(self):
        user_config = UserConfig('test', join(self.root_path, 'test'))
        os.makedirs(join(user_config.path, 'data'))

        self.provider.remove(user_config)

    def test_that_instance_can_be_started_and_gets_initialized(self):
        self.provider.start(self._user_config('test'))

        self.runner.initialize.assert_called_with('test')
        self.runner.start.assert_called_with('test')

    def test_that_instance_cannot_be_started_twice(self):
        user_config = self._user_config('test')
        self.provider.start(user_config)

        self.assertRaises(InstanceAlreadyRunningError, self.provider.start, user_config)

    def test_that_running_instances_are_in_runnig_list(self):
        self._init_runner_memory_usage()
        for name in ['one', 'two', 'three']:
            self.provider.start(self._user_config(name))

        self.assertEqual({'one', 'two', 'three'}, set(self.provider.list_running()))

    def test_that_non_existing_instance_cannot_be_stopped(self):
        self.assertRaises(InstanceNotRunningError, self.provider.stop, 'test')

    def test_that_non_started_instance_cannot_be_stopped(self):
        self.assertRaises(InstanceNotRunningError, self.provider.stop, UserConfig('not-started', None))

    def test_that_running_instance_can_be_stopped(self):
        process = MagicMock(spec=ForkedProcess)
        self.runner.start.return_value = process
        user_config = self._user_config('test')
        self.provider.start(user_config)
        self.provider.stop(user_config.username)

        process.terminate.assert_called_once_with()

    def test_that_instance_cannot_be_stopped_twice(self):
        self.provider.start(self._user_config('test'))
        self.provider.stop('test')

        self.assertRaises(InstanceNotRunningError, self.provider.stop, 'test')

    def test_that_status_returns_current_port(self):
        process = MagicMock(spec=ForkedProcess(None, 1234))
        process.port = 1234
        self.runner.start.return_value = process
        self.provider.start(self._user_config('test'))

        status = self.provider.status('test')

        self.assertEqual({'port': 1234, 'state': 'running'}, status)

    def assert_config_file(self, filename, name, hashed_password, salt):
        with open(filename, 'r') as file:
            content = file.read()
            self.assertEqual('[agent]\nname = %s\nhashed_password = %s\nsalt = %s\n\n' % (name, hashed_password, salt),
                             content)

    def test_memory_usage_zero_if_no_processes(self):
        self.assertEqual({'total_usage': 0, 'average_usage': 0, 'agents': []}, self.provider.memory_usage())

    def test_memory_usage_with_process(self):
        # given
        process = MagicMock(spec=ForkedProcess(None, 1234))
        process.port = 1234
        process.memory_usage.return_value = 1024
        self.runner.start.return_value = process
        self.provider.start(self._user_config('test'))

        # when
        usage = self.provider.memory_usage()

        # then
        self.assertEqual({'total_usage': 1024,
                          'average_usage': 1024,
                          'agents': [
                              {'name': 'test', 'memory_usage': 1024}
                          ]}, usage)

    @patch('pixelated.provider.fork.psutil.virtual_memory')
    def test_that_instance_cannot_be_started_with_too_little_memory_left(self, vm_mock):
        # given
        svmem = namedtuple('svmem', ['free'])
        free_memory = 1024 * 1024
        vm_mock.return_value = svmem(free_memory)

        process = MagicMock(spec=ForkedProcess)
        process.memory_usage.return_value = free_memory + 1
        self.runner.start.return_value = process
        self.provider.start(self._user_config('memory monster'))

        second_config = self._user_config('second')

        # when/then
        self.assertRaises(NotEnoughFreeMemory, self.provider.start, second_config)

        process.memory_usage.return_value = free_memory - 1
        self.provider.start(second_config)

    def _init_runner_memory_usage(self):
        def new_process(*args):
            process = MagicMock(spec=ForkedProcess)
            process.memory_usage.return_value = 1024
            return process
        self.runner.start.side_effect = new_process

    def _user_config(self, name):
        path = join(self.root_path, name)
        os.makedirs(path)
        return UserConfig(name, path)
