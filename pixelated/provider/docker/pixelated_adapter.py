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


class PixelatedDockerAdapter(DockerAdapter):

    PIXELATED_PORT = 4567

    def __init__(self):
        pass

    def app_name(self):
        return 'pixelated'

    def run_command(self):
        return '/bin/bash -l -c "cd /pixelated-user-agent/fake-service && ./go"'

    def setup_command(self):
        return '/bin/true'

    def port(self):
        return self.PIXELATED_PORT

    def environment(self, data_path):
        return {}
