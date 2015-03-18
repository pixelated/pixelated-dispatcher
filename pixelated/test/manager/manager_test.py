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

import unittest
import time
import json
import requests
from mock import MagicMock, patch
from pixelated.provider import Provider
from pixelated.manager import RESTfulServer, SSLConfig, DispatcherManager
from pixelated.test.util import certfile, keyfile, cafile
from pixelated.exceptions import InstanceAlreadyExistsError, InstanceAlreadyRunningError, UserAlreadyExistsError
from pixelated.users import Users, UserConfig
from pixelated.authenticator import Authenticator
from pixelated.common import latest_available_ssl_version, DEFAULT_CIPHERS
from tempdir import TempDir
from os.path import join


class RESTfulServerTest(unittest.TestCase):
    mock_provider = None
    ssl_config = None
    server = None

    @classmethod
    def setUpClass(cls):
        RESTfulServerTest.mock_provider = MagicMock(spec=Provider)
        RESTfulServerTest.mock_users = MagicMock(spec=Users)
        RESTfulServerTest.mock_authenticator = MagicMock(spec=Authenticator)

        RESTfulServerTest.ssl_config = SSLConfig(certfile(),
                                                 keyfile())

        RESTfulServerTest.server = RESTfulServer(RESTfulServerTest.ssl_config, RESTfulServerTest.mock_users, RESTfulServerTest.mock_authenticator, RESTfulServerTest.mock_provider)

        RESTfulServerTest.server.server_forever_in_backgroud()
        time.sleep(1)  # let it get up to speed

    @classmethod
    def tearDownClass(cls):
        RESTfulServerTest.server.shutdown()
        print 'Stopped test server'

    def setUp(self):
        self.mock_provider = RESTfulServerTest.mock_provider
        self.mock_provider.reset_mock()
        self.mock_users.reset_mock()
        self.mock_authenticator.reset_mock()

        self.ssl_request = requests.Session()
        self.ssl_request.mount('https://', EnforceTLSv1Adapter())

        self._tmpdir = TempDir()
        self._root_path = self._tmpdir.name

    def tearDown(self):
        self._tmpdir.dissolve()

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

    def assertInternalError(self, response):
        self.assertEqual(500, response.status_code)

    def test_list_empty_agents(self):
        # given
        self.mock_provider.status.return_value = {'state': 'stopped'}
        self.mock_users.list.return_value = []

        # when
        r = self.get('https://localhost:4443/agents')

        # then
        self.assertSuccessJson({'agents': []}, r)

    def test_list_agents(self):
        # given
        self.mock_provider.status.return_value = {'state': 'stopped'}
        self.mock_provider.status.side_effect = None
        self.mock_users.list.return_value = ['first', 'second']

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
        self.mock_users.add.assert_called_with('first')
        self.mock_authenticator.add_credentials.assert_called_once_with('first', 'some password')

    def test_add_agent_twice_returns_conflict(self):
        self.mock_provider.status.return_value = {'state': 'stopped'}
        self.mock_users.add.side_effect = UserAlreadyExistsError

        payload = {'name': 'first', 'password': 'some password'}

        # when
        r = self.post('https://localhost:4443/agents', data=payload)

        # then
        self.assertEqual(409, r.status_code)
        self.assertEqual('Conflict -', r.reason)

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
        self.assertEqual(500, r.status_code)

    def test_agent_status(self):
        # given
        self.mock_provider.status.return_value = {'state': 'running'}

        # when
        r = self.get('https://localhost:4443/agents/first/state')

        # then
        self.assertSuccessJson({'state': 'running'}, r)

    def test_start_agent(self):
        # given
        user_config = UserConfig('first', None)
        self.mock_provider.status.return_value = {'state': 'running'}
        self.mock_users.config.return_value = user_config
        payload = {'state': 'running'}

        # when
        r = self.put('https://localhost:4443/agents/first/state', data=payload)

        # then
        self.assertSuccessJson({'state': 'running'}, r)
        self.mock_provider.start.assert_called_with(user_config)

    def test_start_agent_twice_returns_conflict(self):
        # given
        self.mock_provider.start.side_effect = InstanceAlreadyRunningError
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

    def test_reset_agent_data(self):
        # given
        user_config = UserConfig('first', None)
        self.mock_users.config.return_value = user_config
        self.mock_provider.status.return_value = {'state': 'stopped'}

        # when
        r = self.put('https://localhost:4443/agents/first/reset_data', data={})

        # then
        self.assertSuccessJson({'state': 'stopped'}, r)
        self.mock_provider.reset_data.assert_called_with(user_config)

    def test_reset_agent_data_returns_conflict_if_agent_is_running(self):
        # given
        user_config = UserConfig('first', None)
        self.mock_users.config.return_value = user_config
        self.mock_provider.status.return_value = {'state': 'running'}
        self.mock_provider.reset_data.side_effect = InstanceAlreadyRunningError

        # when
        r = self.put('https://localhost:4443/agents/first/reset_data', data={})

        # then
        self.assertEqual(409, r.status_code)

    def test_get_agent_runtime_info(self):
        # given
        self.mock_provider.status.return_value = {'state': 'running', 'port': 1234}

        # when
        r = self.get('https://localhost:4443/agents/first/runtime')

        # then
        self.assertSuccessJson({'state': 'running', 'port': 1234}, r)

    def test_user_can_be_authenticated_and_passes_credentials_to_provider(self):
        # given
        user_config = UserConfig('first', None)
        self.mock_users.config.return_value = user_config
        self.mock_authenticator.authenticate.return_value = True
        payload = {'password': 'some password'}

        # when
        r = self.post('https://localhost:4443/agents/first/authenticate', data=payload)

        # then
        self.assertEqual(200, r.status_code)
        self.mock_provider.pass_credentials_to_agent.assert_called_once_with(user_config, 'some password')

    def test_user_authenticate_with_invalid_password_returns_forbidden(self):
        # given
        self.mock_authenticator.authenticate.return_value = False
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

    def test_catch_all_exceptions(self):
        try:
            # given
            self.mock_provider.memory_usage.side_effect = Exception('some message')

            # when
            with patch('pixelated.manager.logger') as logger:
                r = self.get('https://localhost:4443/stats/memory_usage')

                # then
                logger.exception.assert_called_once_with('Unhandled Error during request: some message')
                self.assertInternalError(r)
        finally:
            self.mock_provider.memory_usage.side_effect = None  # we need to reset this manually

    @patch('pixelated.manager.SSLWSGIRefServerAdapter')
    @patch('pixelated.manager.run')    # mock run call to avoid actually startng the server
    def test_that_ssl_server_adapter_gets_used_when_ssl_config_is_provided(self, run_mock, ssl_adapter_mock):
        server = RESTfulServer(RESTfulServerTest.ssl_config, RESTfulServerTest.mock_users, RESTfulServerTest.mock_authenticator, RESTfulServerTest.mock_provider)

        # when
        server.serve_forever()

        expected_ca_certs = None  # which means system ciphers
        expected_ciphers = DEFAULT_CIPHERS
        expected_ssl_version = latest_available_ssl_version()
        expected_host = '127.0.0.1'
        expected_port = 4443
        expected_certfile = certfile()
        expected_keyfile = keyfile()

        ssl_adapter_mock.assert_called_once_with(ssl_ca_certs=expected_ca_certs, ssl_ciphers=expected_ciphers, ssl_version=expected_ssl_version, host=expected_host, port=expected_port, ssl_cert_file=expected_certfile, ssl_key_file=expected_keyfile)

    @patch('pixelated.manager.WSGIRefServer')
    @patch('pixelated.manager.run')    # mock run call to avoid actually startng the server
    def test_that_serve_forever_runs_without_ssl_context(self, run_mock, wsgiRefServer_mock):
        # given
        server = RESTfulServer(None, RESTfulServerTest.mock_users, RESTfulServerTest.mock_authenticator, RESTfulServerTest.mock_provider)

        # when
        server.serve_forever()

        # then
        wsgiRefServer_mock.assert_called_once_with(host='localhost', port=4443)

    def test_handles_provider_initializing(self):
        self.mock_users.list.return_value = ['test']
        self.mock_provider.status.side_effect = ProviderInitializingException

        r = self.get('https://localhost:4443/agents')

        self.assertEqual(503, r.status_code)
        self.assertEqual('Service Unavailable - Busy initializing Provider', r.reason)

    @patch('pixelated.manager.DockerProvider')
    @patch('pixelated.manager.RESTfulServer')
    @patch('pixelated.manager.Thread')
    @patch('pixelated.manager.Users')
    @patch('pixelated.manager.LeapProvider')
    def test_that_initialize_happens_in_background_thread(self, leap_provider_mock, users_mock, thread_mock, server_mock, docker_provider_mock):
        # given
        docker_provider_mock.return_value = self.mock_provider
        manager = DispatcherManager(self._root_path, None, None, None, None, provider='docker')

        # when
        manager.serve_forever()

        # then
        thread_mock.assert_called_with(target=self.mock_provider.initialize)
        self.assertFalse(self.mock_provider.initialize.called)

    @patch('pixelated.manager.Authenticator')
    @patch('pixelated.manager.DockerProvider')
    @patch('pixelated.manager.RESTfulServer')
    @patch('pixelated.manager.Thread')
    @patch('pixelated.manager.Users')
    @patch('pixelated.manager.LeapProvider')
    def test_that_tls_config_gets_passed_to_authenticator(self, leap_provider_mock, users_mock, thread_mock, server_mock, docker_provider_mock, authenticator_mock):
        # given
        manager = DispatcherManager(self._root_path, None, None, None, 'some ca bundle', leap_provider_fingerprint='some fingerprint', provider='docker')

        # when
        manager.serve_forever()

        # then
        authenticator_mock.assert_called_once_with(users_mock.return_value, None, 'some ca bundle', leap_provider_fingerprint='some fingerprint')

    @patch('pixelated.manager.Authenticator')
    @patch('pixelated.manager.DockerProvider')
    @patch('pixelated.manager.RESTfulServer')
    @patch('pixelated.manager.Thread')
    @patch('pixelated.manager.Users')
    @patch('pixelated.manager.LeapProvider')
    def test_that_leap_certificate_gets_downloaded_on_serve_forever(self, leap_provider_mock, users_mock, thread_mock, server_mock, docker_provider_mock, authenticator_mock):
        # given
        cert_file = join(self._root_path, 'ca.crt')
        manager = DispatcherManager(self._root_path, None, None, None, 'some ca bundle', leap_provider_fingerprint='some fingerprint', provider='docker')

        # when
        manager.serve_forever()

        # then
        leap_provider_mock.return_value.download_certificate_to.assert_called_once_with(cert_file)
