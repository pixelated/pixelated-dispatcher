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
from pixelated.provider.fork.mailpile_adapter import MailpileAdapter

__author__ = 'fbernitt'

from tempfile import NamedTemporaryFile
import unittest


class NewMailpileAdapterTest(unittest.TestCase):
    def test_adapter_exception_if_mailpile_binary_does_not_exist(self):
            self.assertRaises(ValueError, MailpileAdapter, '/invalid/path/to/binary', None)

    def test_no_error_with_existing_file(self):
        with NamedTemporaryFile() as tmp_bin:
            MailpileAdapter(tmp_bin.name, None)

    def test_adapter_supports_mailpile_virtualenv(self):
        with NamedTemporaryFile() as tmp_bin:
            MailpileAdapter(tmp_bin.name, mailpile_virtualenv='/some/path/to/virtual/env')
