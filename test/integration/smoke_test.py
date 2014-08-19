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
import json
import unittest
import os
import threading
import time

import requests
from tempdir import TempDir

from client.dispatcher_api_client import PixelatedDispatcherClient
from dispatcher import Dispatcher
from server import PixelatedDispatcherServer, SSLConfig, DEFAULT_PORT
from test.util import EnforceTLSv1Adapter, cafile, certfile, keyfile


__author__ = 'fbernitt'

INHERIT = None


class SmokeTest(unittest.TestCase):
    __slots__ = ('_run_method', '_shutdown_method', '_thread_name', '_thread')

    class Server(object):
        def __init__(self, run_method, shutdown_method, thread_name=None):
            self._run_method = run_method
            self._shutdown_method = shutdown_method
            self._thread_name = thread_name
            self._thread = None

        def _start_server(self):
            self._thread = threading.Thread(target=self._run_method)
            self._thread.setDaemon(True)
            if self._thread_name:
                self._thread.setName(self._thread_name)
            self._thread.start()

        def __enter__(self):
            self._start_server()
            time.sleep(0.3)  # let server start
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self._shutdown_method()
            self._thread.join()

    def setUp(self):
        self._tmpdir = TempDir()
        self.ssl_request = requests.Session()
        self.ssl_request.mount('https://', EnforceTLSv1Adapter())

    def tearDown(self):
        self._tmpdir.dissolve()

    def _pixelated_dispatcher_server(self):
        fake_mailpile = os.path.join(os.path.dirname(__file__), 'fake_mailpile.py')
        ssl_config = SSLConfig(certfile(), keyfile())
        server = PixelatedDispatcherServer(self._tmpdir.name, fake_mailpile, ssl_config, mailpile_virtualenv=INHERIT)

        return SmokeTest.Server(server.serve_forever, server.shutdown, thread_name='PixelatedServer')

    def _dispatcher(self):
        dispatcher = Dispatcher(PixelatedDispatcherClient('localhost', DEFAULT_PORT, cacert=cafile()), port=12345, certfile=certfile(),
                                keyfile=keyfile())
        return SmokeTest.Server(dispatcher.serve_forever, dispatcher.shutdown, thread_name='PixelatedDispatcher')

    def _method(self, method, url, form_data=None, json_data=None, timeout=2.0):
        if json_data:
            headers = {'content-type': 'application/json'}
            data = json.dumps(json_data)
            cookies = None
        else:
            cookies = {'_xsrf': '2|7586b241|47c876d965112a2f547c63c95cbc44b1|1402910163'}
            headers = None
            data = form_data.copy()
            data['_xsrf'] = '2|7586b241|47c876d965112a2f547c63c95cbc44b1|1402910163'

        return method(url, data=data, headers=headers, cookies=cookies, timeout=timeout, verify=cafile())

    def get(self, url):
        return self.ssl_request.get(url, verify=cafile())

    def put(self, url, form_data=None, json_data=None):
        return self._method(self.ssl_request.put, url, form_data=form_data, json_data=json_data)

    def post(self, url, form_data=None, json_data=None):
        return self._method(self.ssl_request.post, url, form_data=form_data, json_data=json_data)

    def test_dispatcher_run(self):
        with self._pixelated_dispatcher_server():
            self.assertSuccess(
                self.post('https://localhost:4443/agents', json_data={'name': 'test', 'password': 'some password'}))
            self.assertSuccess(self.get('https://localhost:4443/agents'), json_body={
                'agents': [{'name': 'test', 'state': 'stopped', 'uri': 'http://localhost:4443/agents/test'}]})
            self.assertSuccess(
                self.put('https://localhost:4443/agents/test/state', json_data={'state': 'running'}))
            self.assertSuccess(self.get('https://localhost:4443/agents/test/runtime'),
                               json_body={'state': 'running', 'port': 5000})
            time.sleep(2)  # let mailpile start
            self.assertSuccess(self.get('http://localhost:5000/'))
            self.assertSuccess(
                self.put('https://localhost:4443/agents/test/state', json_data={'state': 'stopped'}))

    def test_dispatcher_starts(self):
        with self._dispatcher():
            self.assertSuccess(self.get('https://localhost:12345/auth/login'))

    def test_server_dispatcher_combination(self):
        with self._pixelated_dispatcher_server():
            with self._dispatcher():
                # add user
                self.assertSuccess(
                    self.post('https://localhost:4443/agents', json_data={'name': 'test', 'password': 'some password'}))
                # try to login with agent down
                # self.assertError(302, self.post('https://localhost:12345/auth/login',
                #                                form_data={'username': 'test', 'password': 'test'}))
                # start agent
                self.assertSuccess(
                    self.put('https://localhost:4443/agents/test/state', json_data={'state': 'running'}))
                # let mailpile start
                time.sleep(1)
                self.assertMemoryUsage(
                    self.get('https://localhost:4443/stats/memory_usage'))
                try:
                    # try to login with agent up
                    self.assertSuccess(self.post('https://localhost:12345/auth/login',
                                                 form_data={'username': 'test', 'password': 'some password'}),
                                       body='Hello World!')
                finally:
                    # shutdown mailple
                    self.put('https://localhost:4443/agents/test/state', json_data={'state': 'stopped'})

    def assertSuccess(self, response, body=None, json_body=None):
        status = response.status_code
        self.assertTrue(200 <= status < 300, msg='%d: %s' % (response.status_code, response.reason))
        if body:
            self.assertEqual(body, response.content)
        if json_body:
            self.assertEqual(json_body, response.json())

    def assertError(self, error_code, response):
        self.assertEqual(error_code, response.status_code,
                         'Expected status code %d but got %d' % (error_code, response.status_code))

    def assertMemoryUsage(self, response):
        self.assertSuccess(response)
        usage = response.json()
        self.assertEqual(1, len(usage['agents']))