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
import traceback
import sys

from tornado import web
from tornado.httpclient import AsyncHTTPClient
from tornado.httpserver import HTTPServer

from pixelated.client.dispatcher_api_client import PixelatedHTTPError, PixelatedNotAvailableHTTPError
from pixelated.common import logger

__author__ = 'fbernitt'

import os
import tornado.ioloop
import tornado.web
import tornado.escape
import time
import base64
import uuid
import ssl

from tornado import gen
from pixelated.common import latest_available_ssl_version, DEFAULT_CIPHERS
from tornado.httpclient import AsyncHTTPClient
import threading
from os.path import exists

COOKIE_NAME = 'pixelated_user'

REQUEST_TIMEOUT = 60
TIMEOUT_WAIT_FOR_AGENT_TO_BE_UP = 5
TIMEOUT_WAIT_STEP = 0.5


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        cookie = self.get_secure_cookie(COOKIE_NAME)
        if cookie:
            return tornado.escape.json_decode(cookie)
        else:
            return None

    def forward(self, port=None, host=None):

        url = "%s://%s:%s%s" % (
            'http', host or "127.0.0.1", port or 80, self.request.uri)
        try:
            response = AsyncHTTPClient().fetch(
                tornado.httpclient.HTTPRequest(
                    url=url,
                    method=self.request.method,
                    body=None if not self.request.body else self.request.body,
                    headers=self.request.headers,
                    follow_redirects=False,
                    request_timeout=REQUEST_TIMEOUT),
                self.handle_response)
            return response
        except tornado.httpclient.HTTPError, x:
            if hasattr(x, 'response') and x.response:
                self.handle_response(x.response)
        except Exception, e:
            logger.error('Error forwarding request %s: %s' % (url, e.message))
            self.set_status(500)
            self.write("Internal server error:\n" + ''.join(traceback.format_exception(*sys.exc_info())))
            self.finish()

    def handle_response(self, response):
        if response.error:
            logger.error('Got error from user %s agent: %s' % (self.current_user, response.error))
            self.set_status(503)
            self.write("Could not connect to instance %s: %s\n" % (self.current_user, str(response.error)))
            self.finish()
        else:
            self.set_status(response.code)
            for header in ("Date", "Cache-Control", "Server", "Content-Type", "Location"):
                v = response.headers.get(header)
                if v:
                    self.set_header(header, v)
            if response.body:
                self.write(response.body)
            self.finish()


class MainHandler(BaseHandler):
    __slots__ = '_client'

    def initialize(self, client):
        self._client = client

    @tornado.web.authenticated
    @tornado.web.asynchronous
    def get(self):
        runtime = self._client.get_agent_runtime(self.current_user)
        if runtime['state'] == 'running':
            port = runtime['port']
            self.forward(port, '127.0.0.1')
        else:
            logger.error('Agent for %s not running - redirecting user to logout' % self.current_user)
            self.redirect(u'/auth/logout')

    @tornado.web.authenticated
    @tornado.web.asynchronous
    def post(self):
        self.get()

    @tornado.web.authenticated
    @tornado.web.asynchronous
    def put(self):
        self.get()

    @tornado.web.authenticated
    @tornado.web.asynchronous
    def delete(self):
        self.get()

    def check_xsrf_cookie(self):
        # agent should do it after user has logged in
        pass


class AuthLoginHandler(tornado.web.RequestHandler):

    def initialize(self, client, banner):
        self._client = client
        self._banner = banner

    def get(self):
        error_message = self.get_cookie('error_msg')
        if error_message:
            error_message = tornado.escape.url_unescape(error_message)
            self.clear_cookie('error_msg')

        status_message = self.get_cookie('status_msg')
        if status_message:
            status_message = tornado.escape.url_unescape(status_message)
            self.clear_cookie('status_msg')

        self.render('login.html', error=error_message, status=status_message, banner=self._banner)

    @tornado.web.asynchronous
    @gen.coroutine
    def post(self):
        username = self.get_argument("username", "")
        password = self.get_argument("password", "")
        try:
            agent = self._client.get_agent(username)

            # now authenticate with server...
            self._client.authenticate(username, password)
            self.set_current_user(username)

            logger.info('Successful login of user %s' % username)
            logger.info('Starting agent for %s' % username)
            runtime = self._client.get_agent_runtime(username)
            if runtime['state'] != 'running':
                self._client.start(username)

                # wait til agent is running
                runtime = self._client.get_agent_runtime(username)
                max_wait_seconds = TIMEOUT_WAIT_FOR_AGENT_TO_BE_UP
                waited = 0
                while runtime['state'] != 'running' and waited < max_wait_seconds:
                    yield gen.Task(tornado.ioloop.IOLoop.current().add_timeout, time.time() + TIMEOUT_WAIT_STEP)
                    runtime = self._client.get_agent_runtime(username)
                    waited += TIMEOUT_WAIT_STEP

                # wait till agent is up and serving
                if runtime['state'] == 'running':
                    yield gen.Task(self._wait_til_agent_is_up, runtime)
                    port = runtime['port']
                    self.redirect(u'/')
                else:
                    logger.warn('Agent not running, redirecting user to login page')
                    self.redirect(u'/auth/login')
            else:
                self.redirect(u'/')
        except PixelatedNotAvailableHTTPError:
            logger.error('Login attempt while service not available by user: %s' % username)
            self.set_cookie('error_msg', tornado.escape.url_escape('Service currently not available'))
            self.redirect(u'/auth/login')
        except PixelatedHTTPError, e:
            logger.warn('Login attempt with invalid credentials by user %s' % username)
            self.set_cookie('error_msg', tornado.escape.url_escape('Invalid credentials'))
            self.redirect(u'/auth/login')
        except Exception, e:
            logger.error('Unexpected exception: %s' % e)
            raise

    @gen.coroutine
    def _wait_til_agent_is_up(self, agent_runtime):
        max_wait = TIMEOUT_WAIT_FOR_AGENT_TO_BE_UP
        waited = 0
        agent_up = False
        port = agent_runtime['port']
        url = 'http://127.0.0.1:%d/' % port

        logger.error('Checking for user agent on url %s' % url)
        start = time.time()
        while waited < max_wait:
            try:
                # define a callback for older tornado versions
                def _some_callback(response):
                    pass

                response = yield AsyncHTTPClient(force_instance=True).fetch(
                    tornado.httpclient.HTTPRequest(
                        connect_timeout=REQUEST_TIMEOUT, request_timeout=REQUEST_TIMEOUT,
                        url=url, allow_ipv6=False), _some_callback)
                if response.code == 200:
                    logger.info('Got 200, agent seems to be up')
                    waited = max_wait
                    agent_up = True
                else:
                    logger.error('Got response with status code %d' % response.code)
            except tornado.httpclient.HTTPError, e:
                logger.info('Got exception while checking for agent to be up: %s' % e)
            except Exception, e:
                logger.info('Got exception while checking for agent to be up: %s' % e)

            if waited < max_wait:
                yield gen.Task(tornado.ioloop.IOLoop.current().add_timeout, time.time() + TIMEOUT_WAIT_STEP)
            waited += TIMEOUT_WAIT_STEP
        if not agent_up:
            raise PixelatedNotAvailableHTTPError('Failed to start agent')

    def set_current_user(self, username):
        if username:
            self.set_secure_cookie(COOKIE_NAME, tornado.escape.json_encode(username))
        else:
            self.clear_cookie(COOKIE_NAME)


class StopServerThread(threading.Thread):
    def __init__(self, client, agent_name):
        threading.Thread.__init__(self)
        self._client = client
        self._agent_name = agent_name

    def run(self):
        try:
            self._client.stop(self._agent_name)
        except Exception, e:
            logger.error('Error while stopping user:')
            logger.error(e)
            raise


class AuthLogoutHandler(BaseHandler):

    def initialize(self, client):
        self._client = client

    def get(self):
        if self.current_user:
            StopServerThread(self._client, self.current_user).start()
        logger.info('User %s logged out' % self.current_user)
        self.clear_cookie(COOKIE_NAME)
        self.set_cookie('status_msg', tornado.escape.url_escape('Logout successful.'))
        self.redirect(u'/')


class DispatcherProxy(object):
    __slots__ = ('_port', '_client', '_bindaddr', '_ioloop', '_certfile', '_keyfile', '_server', '_banner')

    def __init__(self, dispatcher_client, bindaddr='127.0.0.1', port=8080, certfile=None, keyfile=None, banner=None):
        self._port = port
        self._client = dispatcher_client
        self._bindaddr = bindaddr
        self._certfile = certfile
        self._keyfile = keyfile
        self._banner = banner
        self._ioloop = None
        self._server = None

        AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")

    def create_app(self):
        app = tornado.web.Application(
            [
                (r"/auth/login", AuthLoginHandler, dict(client=self._client, banner=self._banner)),
                (r"/auth/logout", AuthLogoutHandler, dict(client=self._client)),
                (r"/dispatcher_static/", web.StaticFileHandler),
                (r"/.*", MainHandler, dict(client=self._client))
            ],
            cookie_secret=base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes),
            login_url='/auth/login',
            template_path=os.path.join(os.path.dirname(__file__), '..', 'files', "templates"),
            static_path=os.path.join(os.path.dirname(__file__), '..', 'files', "static"),
            static_url_prefix='/dispatcher_static/',  # needs to be bound to a different prefix as agent uses static
            xsrf_cookies=True,
            debug=True)
        return app

    @property
    def ssl_options(self):
        if self._certfile:
            return {
                'certfile': os.path.join(self._certfile),
                'keyfile': os.path.join(self._keyfile),
                'ssl_version': latest_available_ssl_version(),
                'ciphers': DEFAULT_CIPHERS
            }
        else:
            return None

    def serve_forever(self):
        app = self.create_app()
        # app.listen(port=self._port, address=self._bindaddr, ssl_options=self.ssl_options)
        if self.ssl_options:
            logger.info('Using SSL certfile %s and keyfile %s' % (self.ssl_options['certfile'], self.ssl_options['keyfile']))
        else:
            logger.warn('No SSL configured!')
        logger.info('Listening on %s:%d' % (self._bindaddr, self._port))
        self._server = HTTPServer(app, ssl_options=self.ssl_options)
        self._server.listen(port=self._port, address=self._bindaddr)
        self._ioloop = tornado.ioloop.IOLoop.instance()
        self._ioloop.start()  # this is a blocking call, server has stopped on next line
        self._ioloop = None

    def shutdown(self):
        if self._ioloop:
            self._server.stop()
            self._ioloop.stop()
            logger.info('Stopped dispatcher')
