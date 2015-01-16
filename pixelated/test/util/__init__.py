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
__author__ = 'fbernitt'

import ssl
import os

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
from pixelated.common import latest_available_ssl_version


class EnforceTLSv1Adapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize,
                                       block=block, ssl_version=latest_available_ssl_version())


def relative_resource(name):
    return os.path.join(os.path.dirname(__file__), name)


def certfile():
    return _check_exists(relative_resource('server.crt'))


def keyfile():
    return _check_exists(relative_resource('server.key'))


def cafile():
    return _check_exists(relative_resource('server.crt'))


def _check_exists(file):
    if not os.path.exists(file):
        raise Exception('File %s not found' % file)
    return file


class StringIOMatcher(object):
    def __init__(self, expected_str):
        self._expected = expected_str

    def __eq__(self, other):
        return self._expected == other.getvalue()
