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
from provider.fork.mailpile_adapter import MailpileAdapter

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
