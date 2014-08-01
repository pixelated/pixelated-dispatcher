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
from provider.docker.adapter import DockerAdapter


__author__ = 'fbernitt'


class TwsmailDockerAdapter(DockerAdapter):

    TWSMAIL_PORT = 4567

    def __init__(self):
        pass

    def app_name(self):
        return 'twsmail'

    def run_command(self):
        return '/bin/bash -l -c "cd /fake-smail-back && ./go"'

    def setup_command(self):
        return '/bin/true'

    def port(self):
        return TwsmailDockerAdapter.TWSMAIL_PORT

    def environment(self, data_path):
        return {}