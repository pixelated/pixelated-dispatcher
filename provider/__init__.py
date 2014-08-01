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


class NotEnoughFreeMemory(Exception):
    pass


class Provider(object):  # pragma: no cover
    def initialize(self):
        pass

    def add(self, name, password):
        pass

    def remove(self, name):
        pass

    def list(self):
        pass

    def list_running(self):
        pass

    def start(self, name):
        pass

    def stop(self, name):
        pass

    def status(self, name):
        pass

    def authenticate(self, name, password):
        pass

    def memory_usage(self):
        pass
