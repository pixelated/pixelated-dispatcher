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
import StringIO

from mock import MagicMock, patch

from client.cli import Cli
from client.dispatcher_api_client import PixelatedDispatcherClient


__author__ = 'fbernitt'

import unittest


class CliTest(unittest.TestCase):
    def setUp(self):
        self.buffer = StringIO.StringIO()
        self.apimock = MagicMock(spec=PixelatedDispatcherClient)
        self._override_create_cli()

    def test_cli_excepts_args(self):
        Cli([])

    def test_cli_provides_run(self):
        Cli(['-h']).run()

    def test_cli_supports_list(self):
        self.apimock.list.return_value = [
            {'name': 'first', 'state': 'stopped', 'uri': 'https://localhost:12345/agents/first'},
            {'name': 'second', 'state': 'stopped', 'uri': 'https://localhost:12345/agents/second'},
        ]

        Cli(['list'], out=self.buffer).run()

        self.assertEqual('first\nsecond\n', self.buffer.getvalue())

    def test_cli_supports_running(self):
        self.apimock.list.return_value = [
            {'name': 'first', 'state': 'stopped', 'uri': 'https://localhost:12345/agents/first'},
            {'name': 'second', 'state': 'running', 'uri': 'https://localhost:12345/agents/second'},
        ]

        Cli(['running'], out=self.buffer).run()

        self.assertEqual('second\n', self.buffer.getvalue())

    @patch('getpass.getpass')
    def test_cli_supports_add(self, getpassmock):
        getpassmock.return_value = 'password'
        self.apimock.add.return_value = None
        Cli(['add', 'first']).run()

        self.apimock.add.assert_called_once_with('first', 'password')

    def test_cli_supports_start(self):
        Cli(['start', 'first']).run()

        self.apimock.start.assert_called_once_with('first')

    def test_cli_supports_stop(self):
        Cli(['stop', 'first']).run()

        self.apimock.stop.assert_called_once_with('first')

    def test_supports_runtime(self):
        self.apimock.get_agent_runtime.return_value = {'port': 1234}

        Cli(['info', 'first'], out=self.buffer).run()

        self.apimock.get_agent_runtime.assert_called_once_with('first')
        self.assertEqual('port:\t1234\n', self.buffer.getvalue())

    def test_memory_usage(self):
        self.apimock.memory_usage.return_value = {'total_usage': 1234, 'average_usage': 1234, 'agents': [{'name': 'testagent', 'memory_usage': 1234}]}

        Cli(['memory_usage'], out=self.buffer).run()

        self.assertEqual('memory usage:\t1234\naverage usage:\t1234\n\n\ttestagent:\t1234\n', self.buffer.getvalue())

    def test_verify_ssl_by_defaut(self):
        self.apimock.list.return_value = [{'name': 'first', 'state': 'stopped', 'uri': 'https://localhost:12345/agents/first'}]

        Cli(['list']).run()

        self.assertEqual(True, self._last_cacert)
        self.assertEqual(True, self._last_ssl)

    def test_disable_cert_check(self):
        self.apimock.list.return_value = [{'name': 'first', 'state': 'stopped', 'uri': 'https://localhost:12345/agents/first'}]

        Cli(['-k', 'list']).run()

        self.assertEqual(False, self._last_cacert)

    def test_no_ssl(self):
        self.apimock.list.return_value = [{'name': 'first', 'state': 'stopped', 'uri': 'http://localhost:12345/agents/first'}]

        Cli(['--no-ssl', 'list'], out=self.buffer).run()

        self.assertEqual('first\n', self.buffer.getvalue())
        self.assertFalse(self._last_ssl)

    def _override_create_cli(self):
        mock = self.apimock
        running_test = self
        running_test._last_cacert = None

        def override_create_cli(self, host, port, cacert, ssl):
            running_test._last_cacert = cacert
            running_test._last_ssl = ssl
            return mock

        Cli._create_cli = override_create_cli
