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
import Cookie
import urllib

import tornado.httpserver

from mock import MagicMock, patch
import tornado
from tornado.testing import AsyncHTTPTestCase

from client.dispatcher_api_client import PixelatedHTTPError, PixelatedNotAvailableHTTPError
from dispatcher import Dispatcher, MainHandler


__author__ = 'fbernitt'


class TestServer(object):
    PORT = 8888

    __slots__ = ('_request_handler', '_http_server')

    def __init__(self, request_handler):
        self._request_handler = request_handler
        self._http_server = None

    def __enter__(self):
        self._http_server = tornado.httpserver.HTTPServer(self._request_handler)
        self._http_server.listen(TestServer.PORT, '127.0.0.1')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._http_server.stop()
        pass


class DispatcherTest(AsyncHTTPTestCase):
    def setUp(self):
        self.client = MagicMock()
        self.cookies = Cookie.SimpleCookie()
        super(DispatcherTest, self).setUp()

    def get_app(self):
        self._dispatcher = Dispatcher(self.client)
        self._dispatcher._ioloop = self.io_loop
        return self._dispatcher.create_app()

    def _method(self, method, url, payload=None, auto_xsrf=True, **kwargs):
        if auto_xsrf and method == 'POST':
            self.cookies['_xsrf'] = '2|7586b241|47c876d965112a2f547c63c95cbc44b1|1402910163'
            if payload and '_xsrf' not in payload:
                payload['_xsrf'] = '2|7586b241|47c876d965112a2f547c63c95cbc44b1|1402910163'
            else:
                payload = {'_xsrf': '2|7586b241|47c876d965112a2f547c63c95cbc44b1|1402910163'}

        payload = urllib.urlencode(payload) if payload else None
        headers = {
            'Cookie': self.cookies.output(header='').strip()
        }

        self.http_client.fetch(self.get_url(url), self.stop, follow_redirects=False, method=method, headers=headers,
                               body=payload)
        return self.wait()

    def _get(self, url, **kwargs):
        return self._method('GET', url, **kwargs)

    def _post(self, url, **kwargs):
        return self._method('POST', url, **kwargs)

    def test_redirect_to_login(self):
        response = self._get('/', follow_redirects=False)

        self.assertEqual(302, response.code)
        self.assertEqual('/auth/login?next=%2F', response.headers['Location'])

    def test_invalid_login(self):
        self.client.get_agent.return_value = {}
        self.client.authenticate.side_effect = PixelatedHTTPError
        payload = {
            'username': 'tester',
            'password': 'invalid'
        }

        response = self._post('/auth/login', payload=payload)

        self.assertEqual(302, response.code)
        self.assertEqual('/auth/login?error=Invalid+credentials', response.headers['Location'])

    def test_invalid_agent(self):
        self.client.get_agent.side_effect = PixelatedHTTPError()
        payload = {
            'username': 'invalid_agent',
            'password': 'test',
        }
        response = self._post('/auth/login', payload=payload)

        self.assertEqual(302, response.code)
        self.assertEqual('/auth/login?error=Invalid+credentials', response.headers['Location'])

    def test_successful_login(self):
        self.client.get_agent.return_value = {}
        payload = {
            'username': 'tester',
            'password': 'test',
        }
        response = self._post('/auth/login', payload=payload)

        self.assertEqual(302, response.code)
        self.assertEqual('/', response.headers['Location'])
        cookies = Cookie.SimpleCookie()
        cookies.load(response.headers['Set-Cookie'])
        self.assertTrue('pixelated_user' in cookies)

    def test_missing_xsrf_token_cookie(self):
        self.client.get_agent.return_value = {}
        payload = {
            'username': 'tester',
            'password': 'test',
            '_xsrf': '2|7586b241|47c876d965112a2f547c63c95cbc44b1|1402910163'
        }

        response = self._post('/auth/login', payload=payload, auto_xsrf=False)

        self.assertEqual(403, response.code)

    def _add_auth_cookie(self):
        self.cookies[
            'pixelated_user'] = '2|1:0|10:1407749446|14:pixelated_user|12:InRlc3RlciI=|5ddd4ea06420119d9487c04cb1e83fa6665a9f42644b5969157d93abb2a6ed87'

    def test_autostart_agent_if_not_running(self):
        # given
        self.client.get_agent_runtime.side_effect = [{'state': 'stopped'}, {'state': 'stopped'}, {'state': 'running', 'port': TestServer.PORT}]
        self._add_auth_cookie()

        def fake_handle_request(request):
            message = "You requested %s\n" % request.uri
            request.write("HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n%s" % (
                len(message), message))
            request.finish()

        # when
        with TestServer(fake_handle_request):
            response = self._get('/some/url')

        # then
        self.client.start.assert_called_once_with('tester')
        self.assertEqual(200, response.code)
        self.assertEqual('You requested /some/url\n', response.body)

    def test_autostart_error_message_if_agent_fails_to_start(self):
        # given
        self.client.get_agent_runtime.return_value = {'state': 'stopped'}
        self._add_auth_cookie()

        # when
        response = self._get('/some/url')

        # then
        self.client.start.assert_called_once_with('tester')
        self.assertEqual(503, response.code)
        self.assertEqual('Could not connect to instance tester!\n', response.body)

    def test_pixelated_not_available_error_raised_on_503(self):
        # given
        self.client.get_agent.side_effect = PixelatedNotAvailableHTTPError

        payload = {
            'username': 'tester',
            'password': 'test',
        }

        # when
        response = self._post('/auth/login', payload=payload)

        # then
        self.assertEqual(302, response.code)
        self.assertEqual('/auth/login?error=Service+currently+not+available', response.headers['Location'])
