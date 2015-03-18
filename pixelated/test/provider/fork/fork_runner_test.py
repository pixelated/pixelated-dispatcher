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
import unittest
import subprocess
import os.path
from tempfile import NamedTemporaryFile

from tempdir import TempDir
from mock import patch, MagicMock

from pixelated.provider.fork.fork_runner import ForkedProcess, ForkRunner
from pixelated.provider.fork.mailpile_adapter import MailpileAdapter


class ForkRunnerConstructorTest(unittest.TestCase):

    def test_runner_exception_if_rootpath_does_not_exist(self):
            adapter = MagicMock(spec=MailpileAdapter)
            self.assertRaises(ValueError, ForkRunner, '/invalid/root/path', adapter)


class MailpileEnvCheck(dict):
    def __init__(self, validate_dict, absent_keys=[]):
        super(MailpileEnvCheck, self).__init__(validate_dict)
        self._validate_dict = validate_dict
        self._absent_keys = absent_keys

    def __eq__(self, other):
        if type(other) == dict:
            for key, value in self._validate_dict.items():
                if key not in other:
                    return False
                if other[key] != value:
                    return False

            for key in self._absent_keys:
                if key in other:
                    return False
            return True
        else:
            return False


class ForkRunnerTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = TempDir()
        self._tmpbin = NamedTemporaryFile()
        self.mailpile_bin = self._tmpbin.name
        self.root_path = self._tmpdir.name
        self.gpg_initializer = MagicMock()
        self._adapter = MailpileAdapter(self.mailpile_bin, None, gpg_initializer=self.gpg_initializer)

        self.runner = ForkRunner(self.root_path, self._adapter)

    def tearDown(self):
        self._tmpbin.close()
        self._tmpdir.dissolve()

    def _create_expected_env_check(self, agent_name='test'):
        env_check = MailpileEnvCheck({
            'MAILPILE_HOME': os.path.join(self.root_path, agent_name, 'data'),
            'GNUPGHOME': os.path.join(self.root_path, agent_name, 'data', 'gnupg')
        })
        return env_check

    @patch('subprocess.call')
    @patch('os.environ', new={})
    def test_initialize_calls_mailpile_setup_with_proper_environment(self, call_mock):
        self.runner.initialize('test')

        env_check = self._create_expected_env_check()
        call_mock.assert_called_once_with([self.mailpile_bin, '--setup'], close_fds=True, env=env_check)

    @patch('subprocess.call')
    @patch('subprocess.Popen')
    def test_start_calls_mailpile_www_with_proper_environment(self, popen_mock, call_mock):
        # given
        popen_mock.return_value = popen_mock

        # when
        p = self.runner.start('test')

        # then
        self.assertEqual(ForkedProcess(popen_mock, 5000), p)

        env_check = self._create_expected_env_check()

        popen_mock.assert_called_once_with([self.mailpile_bin, '--www'], stdin=subprocess.PIPE, close_fds=True,
                                           env=env_check)
        call_mock.assert_called_once_with([self.mailpile_bin, '--set', 'sys.http_port=5000'], close_fds=True,
                                          env=env_check)

    @patch('subprocess.call')
    @patch('subprocess.Popen')
    def test_that_different_instances_get_different_ports(self, popen_mock, call_mock):
        # given
        popen_mock.return_value = popen_mock

        # when
        self.runner.start('first')
        self.runner.start('second')

        # then
        env_check_first = self._create_expected_env_check('first')
        env_check_second = self._create_expected_env_check('second')
        call_mock.assert_any_call([self.mailpile_bin, '--set', 'sys.http_port=5000'], close_fds=True,
                                  env=env_check_first)
        call_mock.assert_any_call([self.mailpile_bin, '--set', 'sys.http_port=5001'], close_fds=True,
                                  env=env_check_second)

    def _create_expected_env_check_with_virtualenv(self, virtualenv, absent_keys):
        env_check = MailpileEnvCheck(
            {
                'MAILPILE_HOME': os.path.join(self.root_path, 'test', 'data'),
                'GNUPGHOME': os.path.join(self.root_path, 'test', 'data', 'gnupg'),
                'VIRTUAL_ENV': virtualenv,
                'PATH': '%s/bin:/bin:/usr/bin' % virtualenv
            },
            absent_keys=absent_keys)
        return env_check

    @patch('subprocess.call')
    @patch('os.environ', new={'PATH': '/bin:/usr/bin', 'PYTHONHOME': '/some/python/home'})
    def test_that_virtualenv_is_honored(self, call_mock):
        # given
        virtualenv_path = '/some/virtual/env'

        adapter = MailpileAdapter(self.mailpile_bin, virtualenv_path, self.gpg_initializer)

        self.runner = ForkRunner(self.root_path, adapter)

        # when
        self.runner.initialize('test')

        # then
        keys_to_remove = ['PYTHONHOME']  # must not be set for virtualenvs

        env_check = self._create_expected_env_check_with_virtualenv(virtualenv_path, keys_to_remove)
        call_mock.assert_called_once_with([self.mailpile_bin, '--setup'], close_fds=True, env=env_check)
