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
from pixelated.provider.base_provider import ProviderInitializingException
from pixelated.test.util import EnforceTLSv1Adapter

__author__ = 'fbernitt'
import unittest
import time
import json
import requests
from mock import MagicMock, patch
from pixelated.provider import Provider
from pixelated.server import RESTfulServer, SSLConfig, PixelatedDispatcherServer
from pixelated.test.util import certfile, keyfile, cafile


class RESTfulServerTest(unittest.TestCase):
    mock_provider = None
    ssl_config = None
    server = None

    @classmethod
    def setUpClass(cls):
        RESTfulServerTest.mock_provider = MagicMock(spec=Provider)

        RESTfulServerTest.ssl_config = SSLConfig(certfile(),
                                                 keyfile())

        RESTfulServerTest.server = RESTfulServer(RESTfulServerTest.ssl_config, RESTfulServerTest.mock_provider)

        RESTfulServerTest.server.server_forever_in_backgroud()
        time.sleep(1)  # let it get up to speed

    @classmethod
    def tearDownClass(cls):
        RESTfulServerTest.server.shutdown()
        print 'Stopped test server'

    def setUp(self):
        self.mock_provider = RESTfulServerTest.mock_provider
        self.mock_provider.reset_mock()
        self.mock_provider.list.side_effect = None

        self.ssl_request = requests.Session()
        self.ssl_request.mount('https://', EnforceTLSv1Adapter())

    def get(self, url):
        return self.ssl_request.get(url, verify=cafile())

    def put(self, url, data=None):
        if data:
            data = json.dumps(data)
        return self.ssl_request.put(url, data=data, headers={'content-type': 'application/json'}, verify=cafile())

    def post(self, url, data=None):
        if data:
            data = json.dumps(data)
        return self.ssl_request.post(url, data=data, headers={'content-type': 'application/json'}, verify=cafile())

    def delete(self, url):
        return self.ssl_request.delete(url, verify=cafile())

    def assertSuccessJson(self, dict, response):
        self.assertEqual(200, response.status_code)
        self.assertEquals('application/json', response.headers['content-type'])
        self.assertEqual(dict, response.json())

    def test_list_empty_agents(self):
        # given
        self.mock_provider.status.return_value = {'state': 'stopped'}
        self.mock_provider.list.return_value = []

        # when
        r = self.get('https://localhost:4443/agents')

        # then
        self.assertSuccessJson({'agents': []}, r)

    def test_list_agents(self):
        # given
        self.mock_provider.status.return_value = {'state': 'stopped'}
        self.mock_provider.list.return_value = ['first', 'second']

        # when
        r = self.get('https://localhost:4443/agents')

        # then
        self.assertSuccessJson(
            {'agents': [
                {'name': 'first', 'state': 'stopped', 'uri': 'http://localhost:4443/agents/first'},
                {'name': 'second', 'state': 'stopped', 'uri': 'http://localhost:4443/agents/second'}
            ]}, r)

    def test_add_agent(self):
        # given
        self.mock_provider.status.return_value = {'state': 'stopped'}

        payload = {'name': 'first', 'password': 'some password'}

        # when
        r = self.post('https://localhost:4443/agents', data=payload)

        # then
        self.assertEqual(201, r.status_code)
        self.assertEqual('http://localhost:4443/agents/first', r.headers['Location'])
        self.mock_provider.add.assert_called_with('first', 'some password')

    def test_get_agent(self):
        # given
        self.mock_provider.status.return_value = {'state': 'stopped'}

        # when
        r = self.get('https://localhost:4443/agents/first')

        # then
        self.assertSuccessJson({'name': 'first', 'state': 'stopped', 'uri': 'http://localhost:4443/agents/first'}, r)

    def test_remove_agent(self):
        # when
        r = self.delete('https://localhost:4443/agents/first')

        # then
        self.assertEqual(200, r.status_code)
        self.mock_provider.remove.assert_called_with('first')

    def test_agent_status(self):
        # given
        self.mock_provider.status.return_value = {'state': 'running'}

        # when
        r = self.get('https://localhost:4443/agents/first/state')

        # then
        self.assertSuccessJson({'state': 'running'}, r)

    def test_start_agent(self):
        # given
        self.mock_provider.status.return_value = {'state': 'running'}
        payload = {'state': 'running'}

        # when
        r = self.put('https://localhost:4443/agents/first/state', data=payload)

        # then
        self.assertSuccessJson({'state': 'running'}, r)
        self.mock_provider.start.assert_called_with('first')

    def test_start_agent_twice_returns_conflict(self):
        # given
        self.mock_provider.start.side_effect = ValueError
        payload = {'state': 'running'}

        # when
        r = self.put('https://localhost:4443/agents/first/state', data=payload)

        # then
        self.assertEqual(409, r.status_code)

    def test_stop_agent(self):
        # given
        self.mock_provider.status.return_value = {'state': 'stopped'}
        payload = {'state': 'stopped'}

        # when
        r = self.put('https://localhost:4443/agents/first/state', data=payload)

        # then
        self.assertSuccessJson({'state': 'stopped'}, r)
        self.mock_provider.stop.assert_called_with('first')

    def test_get_agent_runtime_info(self):
        # given
        self.mock_provider.status.return_value = {'state': 'running', 'port': 1234}

        # when
        r = self.get('https://localhost:4443/agents/first/runtime')

        # then
        self.assertSuccessJson({'state': 'running', 'port': 1234}, r)

    def test_user_can_be_authenticated(self):
        # given
        self.mock_provider.authenticate.return_value = True
        payload = {'password': 'some password'}

        # when
        r = self.post('https://localhost:4443/agents/first/authenticate', data=payload)

        # then
        self.assertEqual(200, r.status_code)

    def test_user_authenticate_with_invalid_password_returns_forbidden(self):
        # given
        self.mock_provider.authenticate.return_value = False
        payload = {'password': 'invalid password'}

        # when
        r = self.post('https://localhost:4443/agents/first/authenticate', data=payload)

        # then
        self.assertEqual(403, r.status_code)

    def test_stats_get_memory_usage(self):
        # given
        expected = {'total_usage': 1234, 'average_usage': 1234, 'agents': [{'name': 'test', 'memory_usage': 1234}]}
        self.mock_provider.memory_usage.return_value = expected

        # when
        r = self.get('https://localhost:4443/stats/memory_usage')

        self.assertSuccessJson(expected, r)

    @patch('pixelated.server.WSGIRefServer')
    @patch('pixelated.server.run')    # mock run call to avoid actually startng the server
    def test_that_serve_forever_runs_without_ssl_context(self, run_mock, wsgiRefServer_mock):
        # given
        server = RESTfulServer(None, RESTfulServerTest.mock_provider)

        # when
        server.serve_forever()

        # then
        wsgiRefServer_mock.assert_called_once_with(host='localhost', port=4443)

    def test_handles_provider_initializing(self):

        self.mock_provider.list.side_effect = ProviderInitializingException

        r = self.get('https://localhost:4443/agents')

        self.assertEqual(503, r.status_code)
        self.assertEqual('Service Unavailable - Busy initializing Provider', r.reason)

    @patch('pixelated.server.DockerProvider')
    @patch('pixelated.server.RESTfulServer')
    @patch('pixelated.server.Thread')
    def test_that_initialize_happens_in_background_thread(self, thread_mock, server_mock, docker_provider_mock):
        # given
        docker_provider_mock.return_value = self.mock_provider
        server = PixelatedDispatcherServer(None, None, None, None, provider='docker')

        # when
        server.serve_forever()

        # then
        thread_mock.assert_called_with(target=self.mock_provider.initialize)
        self.assertFalse(self.mock_provider.initialize.called)
