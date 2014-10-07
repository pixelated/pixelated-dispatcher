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


class ForkProviderConstructorTest(unittest.TestCase):
    def test_init_checks_rootpath_exists(self):
        self.assertRaises(Exception, ForkProvider, '/does/not/exist', None)

        with TempDir() as tmpdir:
            ForkProvider(tmpdir, None)

        with NamedTemporaryFile() as tmpfile:
            self.assertRaises(Exception, ForkProvider, tmpfile.name, None)


class ForkProviderTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = TempDir()
        self.root_path = self._tmpdir.name
        self.runner = MagicMock(spec=Adapter)
        self.provider = ForkProvider(self.root_path, self.runner)
        self.provider.initialize()

    def tearDown(self):
        self._tmpdir.dissolve()

    @patch('random.getrandbits')
    def test_new_instance_can_be_added(self, randmock):
        hashed_password = '1298e6969236f8efe078c2718acc793c6459b6d94720eb2443a9d04820ac68faacc0d79ba28c7b323be13a69d30bf19340cfcadab79c9f11f8b7388436409de9'
        hex_salt = 31
        randmock.return_value = 1

        self.provider.add('test', 'password')

        instance_path = join(self.root_path, 'test')
        cfg_path = join(instance_path, 'agent.cfg')
        data_path = join(instance_path, 'data')
        gnupg_path = join(instance_path, 'gnupg')

        self.assertTrue(isfile(cfg_path), 'No config file created')
        self.assertTrue(isdir(instance_path), 'No folder for user has been created')
        self.assertTrue(isdir(data_path), 'No maipile folder for user has been created')
        self.assertTrue(isdir(gnupg_path), 'No gnupg folder for user has been created')

        self.assert_config_file(cfg_path, 'test', hashed_password, hex_salt)
        self.assertEqual(stat.S_IFDIR | stat.S_IRWXU, os.stat(instance_path).st_mode)
        self.assertEqual(stat.S_IFDIR | stat.S_IRWXU, os.stat(data_path).st_mode)
        self.assertEqual(stat.S_IFDIR | stat.S_IRWXU, os.stat(gnupg_path).st_mode)

    @patch('random.getrandbits')
    def test_random_salt_is_used(self, randmock):
        hashed_password = 'ecb5c3382726fd831a54bc888d46c8813a18750220c2067cd7bc3fe4f7791261099426cabc6ad07220080943de2c331afddd75210d3ecdd7c5742c85146ace3c'
        salt = 2
        hex_salt = 32
        randmock.return_value = salt
        instance_path = join(self.root_path, 'test')
        cfg_path = join(instance_path, 'agent.cfg')

        self.provider.add('test', 'password')

        self.assert_config_file(cfg_path, 'test', hashed_password, hex_salt)

    def test_multiple_instances_can_be_added(self):
        self.provider.add('first', 'password')
        self.provider.add('second', 'password')

        self.assertEqual(['first', 'second'], self.provider.list())

    def test_instances_can_not_be_added_twice(self):
        self.provider.add('test', 'password')

        self.assertRaises(InstanceAlreadyExistsError, self.provider.add, 'test', 'password')

    def test_remove_raises_exception_if_instance_does_not_exist(self):
        self.assertRaises(ValueError, self.provider.remove, 'test')

    def test_instances_can_be_removed(self):
        self.provider.add('test', 'password')
        self.provider.remove('test')

    def test_that_non_existing_instance_cannot_be_started(self):
        self.assertRaises(InstanceNotFoundError, self.provider.start, 'test')

    def test_that_instance_can_be_started_and_gets_initialized(self):
        self.provider.add('test', 'password')
        self.provider.start('test')

        self.runner.initialize.assert_called_with('test')
        self.runner.start.assert_called_with('test')

    def test_that_instance_cannot_be_started_twice(self):
        self.provider.add('test', 'password')
        self.provider.start('test')

        self.assertRaises(InstanceAlreadyRunningError, self.provider.start, 'test')

    def test_that_running_instances_are_in_runnig_list(self):
        self._init_runner_memory_usage()
        for name in ['one', 'two', 'three']:
            self.provider.add(name, 'password')
            self.provider.start(name)

        self.provider.add('not-started', 'password')

        self.assertEqual({'one', 'two', 'three'}, set(self.provider.list_running()))

    def test_that_non_existing_instance_cannot_be_stopped(self):
        self.assertRaises(InstanceNotRunningError, self.provider.stop, 'test')

    def test_that_non_started_instance_cannot_be_stopped(self):
        self.provider.add('test', 'password')

        self.assertRaises(InstanceNotRunningError, self.provider.stop, 'test')

    def test_that_running_instance_can_be_stopped(self):
        process = MagicMock(spec=ForkedProcess)
        self.runner.start.return_value = process
        self.provider.add('test', 'password')
        self.provider.start('test')
        self.provider.stop('test')

        process.terminate.assert_called_once_with()

    def test_that_instance_cannot_be_stopped_twice(self):
        self.provider.add('test', 'password')
        self.provider.start('test')
        self.provider.stop('test')

        self.assertRaises(InstanceNotRunningError, self.provider.stop, 'test')

    def test_that_existing_agents_are_autodiscovered(self):
        agent = os.path.join(self.root_path, 'test')
        os.mkdir(agent)

        self.provider = ForkProvider(self.root_path, self.runner)
        self.provider.initialize()

        self.assertEqual(['test'], self.provider.list())

    def test_that_status_returns_current_port(self):
        process = MagicMock(spec=ForkedProcess(None, 1234))
        process.port = 1234
        self.runner.start.return_value = process
        self.provider.add('test', 'password')
        self.provider.start('test')

        status = self.provider.status('test')

        self.assertEqual({'port': 1234, 'state': 'running'}, status)

    def test_authenticate(self):
        self.provider.add('test', 'password')

        self.assertTrue(self.provider.authenticate('test', 'password'))
        self.assertFalse(self.provider.authenticate('test', 'something else'))

    def test_unicode_passwords_dont_cause_type_error(self):
        self.provider.add('test', u'password')
        self.assertTrue(self.provider.authenticate('test', u'password'))

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
        self.provider.add('test', 'password')
        self.provider.start('test')

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

        self.provider.add('memory monster', 'password')
        self.provider.start('memory monster')

        self.provider.add('second', 'password')

        # when/then
        self.assertRaises(NotEnoughFreeMemory, self.provider.start, 'second')

        process.memory_usage.return_value = free_memory - 1
        self.provider.start('second')

    def _init_runner_memory_usage(self):
        def new_process(*args):
            process = MagicMock(spec=ForkedProcess)
            process.memory_usage.return_value = 1024
            return process
        self.runner.start.side_effect = new_process
