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
import os
from threading import Thread
import traceback
from provider.base_provider import ProviderInitializingException
from common import logger
from provider.docker import DockerProvider
from provider.docker.twsmail_adapter import TwsmailDockerAdapter


__author__ = 'fbernitt'

import ssl

from bottle import run, Bottle, request, response, WSGIRefServer

from server.bottle_adapter import SSLWSGIRefServerAdapter
from provider.fork import ForkProvider
from provider.fork.fork_runner import ForkRunner
from provider.fork.mailpile_adapter import MailpileAdapter

DEFAULT_PORT = 4443


class SSLConfig(object):
    def __init__(self, ssl_certfile, ssl_keyfile, ssl_version=ssl.PROTOCOL_TLSv1, ssl_ca_certs=None):
        self.ssl_certfile = ssl_certfile
        self.ssl_keyfile = ssl_keyfile
        self.ssl_version = ssl_version
        self.ssl_ca_certs = ssl_ca_certs


def catch_initializing_exception_wrapper(callback):
    def wrapper(*args, **kwargs):
        try:
            return callback(*args, **kwargs)
        except ProviderInitializingException, e:
            response.status = '503 Service Unavailable - Busy initializing Provider'
    return wrapper


class RESTfulServer(object):
    __slots__ = ('_ssl_config', '_port', '_provider', '_server_adapter')

    def __init__(self, ssl_config, provider, port=DEFAULT_PORT):
        self._ssl_config = ssl_config
        self._port = port
        self._provider = provider
        self._server_adapter = None

    def init_bottle_app(self):
        app = Bottle()
        app.install(catch_initializing_exception_wrapper)

        app.route('/agents', method='GET', callback=self._list_agents)
        app.route('/agents', method='POST', callback=self._add_agent)
        app.route('/agents/<name>', method='GET', callback=self._get_agent)
        app.route('/agents/<name>', method='DELETE', callback=self._delete_agent)
        app.route('/agents/<name>/state', method='GET', callback=self._get_agent_state)
        app.route('/agents/<name>/state', method='PUT', callback=self._put_agent_state)
        app.route('/agents/<name>/runtime', method='GET', callback=self._get_agent_runtime)
        app.route('/agents/<name>/authenticate', method='POST', callback=self._authenticate_agent)

        app.route('/stats/memory_usage', method='GET', callback=self._memory_usage)

        return app

    def __enter__(self):
        self.server_forever_in_backgroud()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    def _resource_url_prefix(self):
        parts = request.urlparts

        return '%s://%s%s' % (parts.scheme, parts.netloc, parts.path)

    def _agent_uri(self, agent):
        parts = request.urlparts

        return '%s://%s%s/%s' % (parts.scheme, parts.netloc, '/agents', agent)

    def _agent_to_json(self, agent):
        uri = self._agent_uri(agent)
        state = self._provider.status(agent)['state']

        return {'name': agent, 'uri': uri, 'state': state}

    def _list_agents(self):
        agents = self._provider.list()

        json = []
        for agent in agents:
            json.append(self._agent_to_json(agent))

        return {"agents": json}

    def _add_agent(self):
        name = request.json['name']
        password = request.json['password']
        try:
            self._provider.add(name, password)
            logger.info('Added agent for user %s' % name)
            response.status = '201 Created'
            response.headers['Location'] = self._agent_uri(name)
            return self._agent_to_json(name)
        except ValueError:
            response.status = '409 Conflict'

    def _get_agent(self, name):
        try:
            self._provider.status(name)
            return self._agent_to_json(name)
        except ValueError:
            response.status = '404 Not Found'

    def _delete_agent(self, name):
        try:
            self._provider.remove(name)
            logger.info('Removed agent of user %s' % name)
            response.status = "200 OK"
        except ValueError:
            response.status = "404 Not Found"

    def _get_agent_state(self, name):
        try:
            state = self._provider.status(name)['state']
            return {'state': state}
        except ValueError:
            response.status = "404 Not Found"

    def _put_agent_state(self, name):
        state = request.json['state']

        if state == 'running':
            try:
                self._provider.start(name)
                logger.info('Started agent for user %s' % name)
                return self._get_agent_state(name)
            except ValueError:
                logger.warn('Agent for user %s already running' % name)
                response.status = '409 Conflict - agent %s already running' % name
        else:
            try:
                self._provider.stop(name)
                logger.info('Stopped agent for user %s' % name)
                return self._get_agent_state(name)
            except ValueError:
                logger.warn('Agent for user %s not running' % name)
                response.status = '409 Conflict - agent named %s not running' % name

    def _get_agent_runtime(self, name):
        try:
            return self._provider.status(name)
        except ValueError:
            response.status = '404 Not Found'

    def _authenticate_agent(self, name):
        password = request.json['password']
        result = self._provider.authenticate(name, password)
        if result:
            response.status = '200 Ok'
            logger.info('User %s logged in successfully' % name)
        else:
            response.status = '403 Forbidden'
            logger.warn('Authentication failed for user %s!' % name)
        return {}

    def _memory_usage(self):
        return self._provider.memory_usage()

    def serve_forever(self):
        app = self.init_bottle_app()
        if self._ssl_config:
            server_adapter = SSLWSGIRefServerAdapter(host='localhost', port=self._port,
                                                     ssl_version=self._ssl_config.ssl_version,
                                                     ssl_cert_file=self._ssl_config.ssl_certfile,
                                                     ssl_key_file=self._ssl_config.ssl_keyfile,
                                                     ssl_ca_certs=self._ssl_config.ssl_ca_certs)
        else:
            server_adapter = WSGIRefServer(host='localhost', port=self._port)

        self._server_adapter = server_adapter
        run(app=app, server=server_adapter)

    def server_forever_in_backgroud(self):
        import threading

        t = threading.Thread(target=self.serve_forever)
        t.start()

        return self

    def shutdown(self):
        if self._server_adapter:
            self._server_adapter.shutdown()
            self._server_adapter = None


class PixelatedDispatcherServer(object):
    __slots__ = ('_root_path', '_mailpile_bin', '_mailpile_virtualenv', '_ssl_config', '_server', '_provider')

    def __init__(self, root_path, mailpile_bin, ssl_config, mailpile_virtualenv=None, provider='fork'):
        self._root_path = root_path
        self._mailpile_bin = mailpile_bin
        self._mailpile_virtualenv = mailpile_virtualenv
        self._ssl_config = ssl_config
        self._server = None
        self._provider = provider

    def serve_forever(self):
        provider = self._create_provider()

        Thread(target=provider.initialize).start()

        # 'server.key', ssl_ca_certs='clientCA.crt')
        logger.info('Starting REST api')
        self._server = RESTfulServer(self._ssl_config, provider, port=DEFAULT_PORT)
        if self._ssl_config:
            logger.info('Using SSL certfile %s and keyfile %s' % (self._ssl_config.ssl_certfile, self._ssl_config.ssl_keyfile))
        else:
            logger.warn('No SSL configured')
        logger.info('Listening on %s:%d' % ('localhost', DEFAULT_PORT))
        self._server.serve_forever()

    def shutdown(self):
        if self._server:
            self._server.shutdown()
            self._server = None
            logger.info('Stopped server')

    def _create_provider(self):
        if self._provider == 'docker':
            docker_host = os.environ['DOCKER_HOST'] if os.environ.get('DOCKER_HOST') else None
            # adapter = MailpileDockerAdapter()
            adapter = TwsmailDockerAdapter()
            return DockerProvider(self._root_path, adapter, docker_host)
        else:
            adapter = MailpileAdapter(self._mailpile_bin, mailpile_virtualenv=self._mailpile_virtualenv)
            runner = ForkRunner(self._root_path, adapter)
            return ForkProvider(self._root_path, runner)
