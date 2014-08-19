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
import unittest

from httmock import HTTMock, all_requests, urlmatch
from mock import patch

from client.dispatcher_api_client import PixelatedDispatcherClient, PixelatedHTTPError


__author__ = 'fbernitt'


class MultipileClientConstructorTest(unittest.TestCase):
    def test_initialized_with_host_and_port(self):
        PixelatedDispatcherClient('hostname', 1234)

    def test_initialize_with_ssl_ca(self):
        PixelatedDispatcherClient('hostname', 1234, cacert=True)

    def test_initialize_without_ssl(self):
        PixelatedDispatcherClient('hostname', 1234, ssl=False)


@all_requests
def not_found_handler(url, request):
    return {'status_code': 404}


class MultipileClientTest(unittest.TestCase):
    def setUp(self):
        self.client = PixelatedDispatcherClient('localhost', 12345)

    def test_exception_raised_if_not_available(self):
        with HTTMock(not_found_handler):
            self.assertRaises(PixelatedHTTPError, self.client.get_agent, 'test')
            self.assertRaises(PixelatedHTTPError, self.client.list)
            self.assertRaises(PixelatedHTTPError, self.client.get_agent_runtime, 'test')
            self.assertRaises(PixelatedHTTPError, self.client.start, 'test')
            self.assertFalse(self.client.agent_exists('test'))

    def test_list(self):
        expected = [
            {'name': 'first', 'state': 'stopped', 'uri': 'https://localhost:12345/agents/first'},
            {'name': 'second', 'state': 'stopped', 'uri': 'https://localhost:12345/agents/second'},
        ]

        @urlmatch(path='/agents')
        def list_agents(url, request):
            return {
                'status_code': 200,
                'content': {'agents': expected}
            }

        with HTTMock(list_agents, not_found_handler):
            agents = self.client.list()
            self.assertEqual(expected, agents)

    def test_running(self):
        expected = [
            {'name': 'first', 'state': 'stopped', 'uri': 'https://localhost:12345/agents/first'},
            {'name': 'second', 'state': 'stopped', 'uri': 'https://localhost:12345/agents/second'},
        ]

        @urlmatch(path='/agents')
        def list_agents(url, request):
            return {
                'status_code': 200,
                'content': {'agents': expected}
            }

        with HTTMock(list_agents, not_found_handler):
            agents = self.client.list()
            self.assertEqual(expected, agents)

    def test_get_agent(self):
        expected = {'name': 'first', 'state': 'stopped', 'uri': 'https://localhost:12345/agents/first'}

        @urlmatch(path='^/agents/first$')
        def fetch_agent(url, request):
            return {
                'status_code': 200,
                'content': expected
            }

        with HTTMock(fetch_agent, not_found_handler):
            agent = self.client.get_agent('first')

            self.assertEqual(expected, agent)

    def test_agent_exists(self):
        @urlmatch(path=r'^/agents/first$')
        def first_agent(url, request):
            return {'status_code': 200, 'content': {}}

        with HTTMock(first_agent, not_found_handler):
            self.assertTrue(self.client.agent_exists('first'))

    def test_agent_runtime(self):
        @urlmatch(path=r'^/agents/first/runtime$')
        def first_agent_runtime(url, request):
            return {'status_code': 200, 'content': {'port': 5000}}

        with HTTMock(first_agent_runtime, not_found_handler):
            runtime = self.client.get_agent_runtime('first')
            self.assertEqual({'port': 5000}, runtime)

    def test_start(self):
        expected = {'name': 'first', 'state': 'running', 'uri': 'https://localhost:12345/agents/first'}

        @urlmatch(path=r'^/agents/first/state$')
        def start_agent(url, request):
            if request.body == '{"state": "running"}':
                return {'status_code': 200, 'content': expected}
            else:
                print 'woha %s' % request.body
                return {'status_code': 400}

        with HTTMock(start_agent, not_found_handler):
            actual = self.client.start('first')
            self.assertEqual(expected, actual)

    def test_stop(self):
        expected = {'name': 'first', 'state': 'stopped', 'uri': 'https://localhost:12345/agents/first'}

        @urlmatch(path=r'^/agents/first/state$')
        def stop_agent(url, request):
            return {'status_code': 200, 'content': expected}

        with HTTMock(stop_agent, not_found_handler):
            actual = self.client.stop('first')
            self.assertEqual(expected, actual)

    def test_authenticate(self):
        @urlmatch(path=r'^/agents/first/authenticate', method='POST')
        def auth_agent(url, request):
            if request.headers['Content-Type'] != 'application/json':
                return {'status_code': 403}
            if request.body == '{"password": "password"}':
                return {'status_code': 200, 'content': {}}
            else:
                return {'status_code': 403}

        with HTTMock(auth_agent, not_found_handler):
            self.client.authenticate('first', 'password')

    def test_add(self):
        @urlmatch(path=r'^/agents', method='POST')
        def add_agent(url, request):
            return {'status_code': 201}

        with HTTMock(add_agent, not_found_handler):
            self.client.add('first', 'password')

    def test_memory_usage(self):
        expected = {'total_usage': 1234, 'average_usage': 1234, 'agents': [{'name': 'test', 'memory_usage': 1234}]}

        @urlmatch(path=r'^/stats/memory_usage', method='GET')
        def memory_usage(url, request):
            return {'status_code': 200, 'content': expected}

        with HTTMock(memory_usage, not_found_handler):
            usage = self.client.memory_usage()
            self.assertEqual(expected, usage)

    @patch('requests.Session')
    def test_that_certificates_are_verified_by_default(self, requests_mock):
        session = requests_mock.return_value
        verify_certificate = True

        self._assert_cacert_used(session, verify_certificate)

    @patch('requests.Session')
    def test_that_cacert_gets_used(self, requests_mock):
        some_ca = 'some cert'
        self.client = PixelatedDispatcherClient('localhost', 12345, cacert=some_ca)
        session = requests_mock.return_value

        self._assert_cacert_used(session, some_ca)

    def _assert_cacert_used(self, session, cacert):
        self.client.list()
        session.get.assert_called_once_with('https://localhost:12345/agents', verify=cacert)

        self.client.add('test', 'password')
        session.post.assert_called_once_with('https://localhost:12345/agents', verify=cacert, data='{"password": "password", "name": "test"}', headers={'Content-Type': 'application/json'})

        self.client.start('test')
        session.put.assert_called_once_with('https://localhost:12345/agents/test/state', verify=cacert, data='{"state": "running"}', headers={'Content-Type': 'application/json'})

    def test_that_call_without_ssl_is_possible(self):
        self.client = PixelatedDispatcherClient('localhost', 12345, ssl=False)

        @urlmatch(path='/agents')
        def list_agents(url, request):
            if url.scheme == 'https':
                return {'status_code': 500}
            else:
                return {
                    'status_code': 200,
                    'content': {'agents': []}
                }

        with HTTMock(list_agents, not_found_handler):
            self.client.list()