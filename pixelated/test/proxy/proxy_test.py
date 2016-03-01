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
import Cookie
import urllib
import time
import tornado.httpserver
from tornado.ioloop import IOLoop
import threading

from mock import MagicMock, patch, ANY
import tornado
from tornado.testing import AsyncHTTPTestCase, gen_test

from pixelated.client.dispatcher_api_client import PixelatedHTTPError, PixelatedNotAvailableHTTPError
from pixelated.proxy import DispatcherProxy, MainHandler
from pixelated.common import latest_available_ssl_version, DEFAULT_CIPHERS
from bottle import request, route, run, ServerAdapter, Bottle

__author__ = 'fbernitt'


class MyWSGIRefServer(ServerAdapter):
    server = None

    def run(self, handler):
        from wsgiref.simple_server import make_server, WSGIRequestHandler
        if self.quiet:
            class QuietHandler(WSGIRequestHandler):
                def log_request(*args, **kw):
                    pass
            self.options['handler_class'] = QuietHandler
        self.server = make_server(self.host, self.port, handler, **self.options)
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()


class Server(object):
    PORT = 8888
    HOSTNAME = '127.0.0.1'

    def __init__(self, thread_name=None):
        self._thread_name = thread_name
        self._thread = None

    def _start_server(self):
        self._thread = threading.Thread(target=self.run)
        self._thread.setDaemon(True)
        if self._thread_name:
            self._thread.setName(self._thread_name)
        self._thread.start()

    def run(self):
        app = Bottle()

        @app.route("/")
        @app.route("/<url:re:.+>")
        def catch_all_requests(url=None):
            return 'You requested %s\n' % request.path

        self._server = MyWSGIRefServer(host=Server.HOSTNAME, port=Server.PORT)
        app.run(server=self._server)

    def __enter__(self):
        self._start_server()
        time.sleep(0.3)  # let server start
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._server.stop()
        self._thread.join()


class DispatcherProxyTest(AsyncHTTPTestCase):
    def setUp(self):
        self.client = MagicMock()
        self.cookies = Cookie.SimpleCookie()
        super(DispatcherProxyTest, self).setUp()

    def get_app(self):
        self._dispatcher = DispatcherProxy(self.client)
        self._dispatcher._ioloop = self.io_loop
        return self._dispatcher.create_app()

    def _method(self, method, url, payload=None, auto_xsrf=True, follow_redirects=False, extra_headers={}, **kwargs):
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
        headers.update(extra_headers)

        self.http_client.fetch(self.get_url(url), self.stop, follow_redirects=follow_redirects, method=method, headers=headers,
                               body=payload)
        return self.wait(timeout=2000)

    def get_url(self, path):
        return '%s://%s:%s%s' % (self.get_protocol(),
                                 Server.HOSTNAME,
                                 self.get_http_port(), path)

    def _get(self, url, **kwargs):
        return self._method('GET', url, **kwargs)

    def _post(self, url, **kwargs):
        return self._method('POST', url, **kwargs)

    def test_redirect_to_login(self):
        response = self._get('/')

        self.assertEqual(302, response.code)
        self.assertEqual('/auth/login?next=%2F', response.headers['Location'])

    def test_error_code_instead_of_redirect_for_ajax_requests(self):
        response = self._get('/', extra_headers={'X-Requested-With': 'XMLHttpRequest'})
        cookies = self._get_cookies(response)
        clear_session = ''

        self.assertEqual(401, response.code)
        self.assertEqual(clear_session, cookies['pixelated_user'].value)

    def _get_cookies(self, response):
        cookies = Cookie.SimpleCookie()

        for cookie in response.headers.get_list("set-cookie"):
            cookies.load(cookie)

        return cookies

    def test_invalid_login(self):
        self.client.get_agent.return_value = {}
        self.client.authenticate.side_effect = PixelatedHTTPError(status_code=403)
        payload = {
            'username': 'tester',
            'password': 'invalid'
        }

        response = self._post('/auth/login', payload=payload)

        self.assertEqual(302, response.code)
        cookies = self._get_cookies(response)

        self.assertEqual('Invalid+credentials', cookies['error_msg'].value)
        self.assertEqual('/auth/login', response.headers['Location'])

    def test_invalid_agent(self):
        self.client.get_agent.side_effect = PixelatedHTTPError(status_code=403)
        payload = {
            'username': 'invalid_agent',
            'password': 'test',
        }
        response = self._post('/auth/login', payload=payload)

        self.assertEqual(302, response.code)
        cookies = self._get_cookies(response)

        self.assertEqual('Invalid+credentials', cookies['error_msg'].value)
        self.assertEqual('/auth/login', response.headers['Location'])

    def test_successful_login(self):
        self.client.get_agent_runtime.side_effect = [{'state': 'stopped'}, {'state': 'stopped'}, {'state': 'running', 'port': Server.PORT}, {'state': 'running', 'port': Server.PORT}]
        payload = {
            'username': 'tester',
            'password': 'test',
        }
        with Server():
            response = self._post('/auth/login', payload=payload)

        self.assertEqual(302, response.code)
        self.assertEqual('/', response.headers['Location'])
        cookies = self._get_cookies(response)
        self.assertTrue('pixelated_user' in cookies)
        self.client.start.assert_called_once_with('tester')

    def test_successful_login_with_already_running_agent(self):
        self.client.start.side_effect = PixelatedHTTPError(status_code=403)
        self.client.get_agent_runtime.return_value = {'state': 'running', 'port': Server.PORT}
        payload = {
            'username': 'tester',
            'password': 'test',
        }
        with Server():
            response = self._post('/auth/login', payload=payload)

        self.assertEqual(302, response.code)
        self.assertEqual('/', response.headers['Location'])
        cookies = self._get_cookies(response)
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

    def test_security_headers(self):
        response = self._get('/some/url')

        self.assertEqual('no-cache,no-store,must-revalidate,private', response.headers.get('Cache-Control'))
        self.assertEqual('no-cache', response.headers.get('Pragma'))
        self.assertEqual('1; mode=block', response.headers.get('X-XSS-Protection'))
        self.assertEqual('nosniff', response.headers.get('X-Content-Type-Options'))
        self.assertEqual('DENY', response.headers.get('X-Frame-Options'))

    def test_strict_transport_security(self):
        class SSLHttpRequest(tornado.httpserver.HTTPRequest):
            @property
            def protocol(self):
                return 'https'

            @protocol.setter
            def protocol(self, ignored):
                pass

        with patch('tornado.httpserver.HTTPRequest', new=SSLHttpRequest) as mock_protocol:
            response = self._get('/some/url')

            self.assertEqual('max-age=31536000; includeSubDomains', response.headers.get('Strict-Transport-Security'))

    def test_noautocomplete_for_login(self):
        response = self._get('/auth/login')

        self.assertTrue('autocomplete="off"' in response.body)

    def _fetch_auth_cookie(self):
        payload = {
            'username': 'tester',
            'password': 'test',
        }
        response = self._post('/auth/login', payload=payload)

        self.assertEqual(302, response.code)
        self.assertEqual('/', response.headers['Location'])
        login_cookies = self._get_cookies(response)
        self.assertTrue('pixelated_user' in login_cookies)

        self.cookies = Cookie.SimpleCookie()
        self.cookies['pixelated_user'] = login_cookies['pixelated_user'].value.strip()

    def test_autostart_agent_if_not_running(self):
        # given
        self.client.get_agent_runtime.side_effect = [{'state': 'stopped'}, {'state': 'stopped'}, {'state': 'running', 'port': Server.PORT}, {'state': 'running', 'port': Server.PORT}]

        # when
        with Server():
            self._fetch_auth_cookie()
            response = self._get('/some/url')

        # then
        self.client.start.assert_called_once_with('tester')
        self.assertEqual(200, response.code)
        self.assertEqual('You requested /some/url\n', response.body)

    def test_autostart_error_message_if_agent_fails_to_start(self):
        # given
        self.client.get_agent_runtime.side_effect = [{'state': 'stopped'}, {'state': 'stopped'}, {'state': 'running', 'port': Server.PORT}, {'state': 'running', 'port': Server.PORT}]
        self.client.get_agent_runtime.return_value = {'state': 'stopped'}

        with Server():
            self._fetch_auth_cookie()

        # when
        response = self._get('/some/url')

        # then
        self.client.start.assert_called_once_with('tester')
        self.assertEqual(503, response.code)
        self.assertRegexpMatches(response.body, 'Could not connect to instance tester: .*')

    def test_logout_stops_user_agent_and_resets_session_cookie(self):
        self.client.get_agent_runtime.side_effect = [{'state': 'stopped'}, {'state': 'stopped'}, {'state': 'running', 'port': Server.PORT}, {'state': 'running', 'port': Server.PORT}]

        with Server():
            self._fetch_auth_cookie()
            response = self._get('/auth/logout')

        cookies = self._get_cookies(response)

        time.sleep(0.01)   # wait for background call to client.stop
        self.assertEqual(302, response.code)
        self.client.stop.assert_called_once_with('tester')
        self.assertEqual('', cookies['pixelated_user'].value)

    def test_logout_does_not_stop_agent_if_user_is_none(self):
        response = self._get('/auth/logout')
        time.sleep(0.01)   # wait for background call to client.stop

        self.assertEqual(302, response.code)
        self.assertFalse(self.client.stop.called)

    def test_successful_logout_redirects_to_login(self):
        response = self._get('/auth/logout')
        cookies = self._get_cookies(response)

        self.assertEqual(302, response.code)
        self.assertEqual('/', response.headers['Location'])
        self.assertEqual('Logout+successful.', cookies['status_msg'].value)

    def test_logout_is_forbidden_when_csrf_invalid_login(self):
        response = self._post('/auth/logout')

        self.assertEqual(403, response.code)

    def test_logout_on_web_request_if_agent_stopped(self):
        self.client.get_agent_runtime.side_effect = [{'state': 'running', 'port': Server.PORT}, {'state': 'stopped', 'port': Server.PORT}]

        with Server():
            self._fetch_auth_cookie()
            response = self._get('/')

        cookies = self._get_cookies(response)

        time.sleep(0.01)   # wait for background call to client.stop
        self.assertEqual(302, response.code)
        self.assertEqual('', cookies['pixelated_user'].value)

    def test_logout_on_ajax_request_if_agent_stopped(self):
        self.client.get_agent_runtime.side_effect = [{'state': 'running', 'port': Server.PORT}, {'state': 'stopped', 'port': Server.PORT}]

        with Server():
            self._fetch_auth_cookie()
            response = self._get('/', extra_headers={'X-Requested-With': 'XMLHttpRequest'})

        cookies = self._get_cookies(response)

        time.sleep(0.01)   # wait for background call to client.stop
        self.assertEqual(401, response.code)
        self.assertEqual('', cookies['pixelated_user'].value)

    def test_pixelated_not_available_error_raised_on_503(self):
        # given
        self.client.get_agent.side_effect = PixelatedNotAvailableHTTPError

        payload = {
            'username': 'tester',
            'password': 'test',
        }

        # when
        response = self._post('/auth/login', payload=payload)
        cookies = self._get_cookies(response)

        # then
        self.assertEqual(302, response.code)
        self.assertEqual('Service+currently+not+available', cookies['error_msg'].value)

    @patch('pixelated.proxy.HTTPServer')
    @patch('pixelated.proxy.tornado.ioloop.IOLoop.instance')
    def test_serve_forever(self, ioloop_factory_mock, http_server_mock):
        # given
        ioloop_mock = MagicMock()
        ioloop_factory_mock.return_value = ioloop_mock
        dispatcher = DispatcherProxy(self.client, certfile='/path/to/some/certfile', keyfile='/path/to/some/keyfile')
        dispatcher._ioloop = ioloop_mock

        # when
        dispatcher.serve_forever()

        # then
        expected_ssl_options = {
            'certfile': '/path/to/some/certfile',
            'keyfile': '/path/to/some/keyfile',
            'ssl_version': latest_available_ssl_version(),
            'ciphers': DEFAULT_CIPHERS
        }
        http_server_mock.assert_called_once_with(ANY, ssl_options=expected_ssl_options)

    def test_status_msg(self):
        # given
        self.cookies['status_msg'] = 'some status msg'

        # when
        response = self._get('/', follow_redirects=True)

        # then
        self.assertEqual(200, response.code)
        self.assertTrue('<div class="message-panel message-panel-small">\n<span>\nsome status msg\n</span>' in response.body)
