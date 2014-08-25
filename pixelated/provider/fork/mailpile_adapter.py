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
import os

from pixelated.provider.fork.gpg import GnuPGInitializer


class MailpileAdapter(object):
    __slots__ = ('_mailpile_bin', '_mailpile_virtualenv', '_gpg_initializer')

    def __init__(self, mailpile_bin, mailpile_virtualenv, gpg_initializer=GnuPGInitializer()):
        if not os.path.exists(mailpile_bin):
            raise ValueError('Mailpile binary path seems invalid: %s' % mailpile_bin)

        self._mailpile_bin = mailpile_bin
        self._mailpile_virtualenv = mailpile_virtualenv
        self._gpg_initializer = gpg_initializer

    def app_name(self):
        return 'mailpile'

    def run_command(self):
        return [self._mailpile_bin, '--www']

    def environment(self, data_path):
        env = {}
        for name, value in os.environ.iteritems():
            env[name] = value

        env['MAILPILE_HOME'] = data_path
        env['GNUPGHOME'] = self._gnupg_home(data_path)

        if self._mailpile_virtualenv is not None:
            env['VIRTUAL_ENV'] = self._mailpile_virtualenv
            env['PATH'] = '%s/bin:%s' % (self._mailpile_virtualenv, env['PATH'])  # prefix with virtualenv bin dir
            if 'PYTHONHOME' in env:  # must not be set for virtualenvs
                del env['PYTHONHOME']

        return env

    def setup_command(self):
        return [self._mailpile_bin, '--setup']

    def set_custom_port_command(self, port):
        return [self._mailpile_bin, '--set', 'sys.http_port=%d' % port]

    def initialize_gnupg(self, name, data_path):
        self._gpg_initializer.create_key_pair(self._gnupg_home(data_path), '%s@example.local' % name, name)

    def _gnupg_home(self, data_path):
        return os.path.join(data_path, 'gnupg')
