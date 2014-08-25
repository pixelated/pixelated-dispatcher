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
from pixelated.provider.docker.adapter import DockerAdapter

__author__ = 'fbernitt'


class MailpileDockerAdapter(DockerAdapter):

    MAILPILE_PORT = 33411

    def app_name(self):
        return 'mailpile'

    def run_command(self):
        return '/Mailpile.git/mp --www'

    def setup_command(self):
        return '/Mailpile.git/mp --setup --set sys.http_host=0.0.0.0'

    def port(self):
        return MailpileDockerAdapter.MAILPILE_PORT

    def environment(self, data_path):
        return {'MAILPILE_HOME': data_path}
