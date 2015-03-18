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

from mock import MagicMock, patch
from psutil._common import pmem

from pixelated.provider.fork.adapter import ForkedProcess

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

        with patch('pixelated.provider.fork.adapter.Process') as psutil_process_mock:
            psutil_mock = psutil_process_mock.return_value
            psutil_mock.memory_info.return_value = pmem(1024, 2048)

            # when
            usage = p.memory_usage()

            # then
            psutil_process_mock.assert_called_once_with(pid)
            psutil_mock.memory_info.assert_called_once_with()

            self.assertEqual(1024, usage)
