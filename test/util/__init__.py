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
__author__ = 'fbernitt'

import ssl
import os

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager


class EnforceTLSv1Adapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize,
                                       block=block, ssl_version=ssl.PROTOCOL_TLSv1)


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