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

from mock import MagicMock, patch
from psutil._common import pmem

from provider.fork.adapter import ForkedProcess


__author__ = 'fbernitt'

import unittest


class ForkedProcessTest(unittest.TestCase):

    def test_that_terminate_closes_stdin_and_terminates_process(self):
        # given
        process = MagicMock()
        port = 1234
        p = ForkedProcess(process, port)

        # when
        p.terminate()

        # then
        process.stdin.write.assert_called_once_with('quit\n')
        process.stdin.close.assert_called_once_with()
        process.terminate.assert_called_once_with()

    def test_memory_usage_is_available(self):
        # given
        port = 1234
        pid = 42
        process = MagicMock()
        p = ForkedProcess(process, port)
        process.pid = pid

        with patch('provider.fork.adapter.Process') as psutil_process_mock:
            psutil_mock = psutil_process_mock.return_value
            psutil_mock.memory_info.return_value = pmem(1024, 2048)

            # when
            usage = p.memory_usage()

            # then
            psutil_process_mock.assert_called_once_with(pid)
            psutil_mock.memory_info.assert_called_once_with()

            self.assertEqual(1024, usage)