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
from pixelated.provider.docker.adapter import DockerAdapter


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
