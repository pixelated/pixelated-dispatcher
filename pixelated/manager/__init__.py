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
import os
from threading import Thread
import traceback
from pixelated.provider.base_provider import ProviderInitializingException
from pixelated.common import logger
from pixelated.provider.docker import DockerProvider
from pixelated.provider.docker.pixelated_adapter import PixelatedDockerAdapter
from pixelated.exceptions import InstanceAlreadyRunningError, UserNotExistError, InstanceNotRunningError, UserAlreadyExistsError, InstanceNotFoundError
from pixelated.users import Users
from pixelated.authenticator import Authenticator

__author__ = 'fbernitt'

import ssl

from bottle import run, Bottle, request, response, WSGIRefServer

from pixelated.manager.bottle_adapter import SSLWSGIRefServerAdapter
from pixelated.provider.fork import ForkProvider
from pixelated.provider.fork.fork_runner import ForkRunner
from pixelated.provider.fork.mailpile_adapter import MailpileAdapter
from pixelated.common import latest_available_ssl_version, DEFAULT_CIPHERS

DEFAULT_PORT = 4443


class SSLConfig(object):

    __slots__ = ('ssl_certfile', 'ssl_keyfile', 'ssl_version', 'ssl_ca_certs', 'ssl_ciphers')

    def __init__(self, ssl_certfile, ssl_keyfile, ssl_version=latest_available_ssl_version(), ssl_ca_certs=None, ssl_ciphers=DEFAULT_CIPHERS):
        self.ssl_certfile = ssl_certfile
        self.ssl_keyfile = ssl_keyfile
        self.ssl_version = ssl_version
        self.ssl_ca_certs = ssl_ca_certs
        self.ssl_ciphers = ssl_ciphers


def catch_initializing_exception_wrapper(callback):
    def wrapper(*args, **kwargs):
        try:
            return callback(*args, **kwargs)
        except ProviderInitializingException, e:
            response.status = '503 Service Unavailable - Busy initializing Provider'
    return wrapper


def log_all_exceptions(callback):
    def wrapper(*args, **kwargs):
        try:
            return callback(*args, **kwargs)
        except Exception, e:
            logger.error('Error during request: %s' % e.message)
            raise
    return wrapper


class RESTfulServer(object):
    __slots__ = ('_ssl_config', '_bindaddr', '_port', '_users', '_authenticator', '_provider', '_server_adapter')

    def __init__(self, ssl_config, users, authenticator, provider, bindaddr='127.0.0.1', port=DEFAULT_PORT):
        self._ssl_config = ssl_config
        self._bindaddr = bindaddr
        self._port = port
        self._users = users
        self._authenticator = authenticator
        self._provider = provider
        self._server_adapter = None

    def init_bottle_app(self):
        app = Bottle()
        app.install(catch_initializing_exception_wrapper)
        app.install(log_all_exceptions)

        app.route('/agents', method='GET', callback=self._list_agents)
        app.route('/agents', method='POST', callback=self._add_agent)
        app.route('/agents/<name>', method='GET', callback=self._get_agent)
        app.route('/agents/<name>', method='DELETE', callback=self._delete_agent)
        app.route('/agents/<name>/state', method='GET', callback=self._get_agent_state)
        app.route('/agents/<name>/state', method='PUT', callback=self._put_agent_state)
        app.route('/agents/<name>/runtime', method='GET', callback=self._get_agent_runtime)
        app.route('/agents/<name>/authenticate', method='POST', callback=self._authenticate_agent)
        app.route('/agents/<name>/reset_data', method='PUT', callback=self._reset_agent_data)

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

    def _user_with_agent_to_json(self, user):
        uri = self._agent_uri(user)
        state = self._provider.status(user)['state']

        return {'name': user, 'uri': uri, 'state': state}

    def _list_agents(self):
        users = self._users.list()
        json = []
        for user in users:
            json.append(self._user_with_agent_to_json(user))

        return {"agents": json}

    def _add_agent(self):
        name = request.json['name']
        password = request.json['password']
        try:
            self._users.add(name)
            self._authenticator.add_credentials(name, password)
            logger.info('Added agent for user %s' % name)
            response.status = '201 Created'
            response.headers['Location'] = self._agent_uri(name)
            return self._agent_to_json(name)
        except UserAlreadyExistsError as error:
                logger.warn(error.message)
                response.status = '409 Conflict - %s' % error.message

    def _get_agent(self, name):
        try:
            self._provider.status(name)
            return self._agent_to_json(name)
        except InstanceNotFoundError as error:
                logger.warn(error.message)
                response.status = '404 Not Found - %s' % error.message

    def _delete_agent(self, name):
        response.status = '500 Not yet implemented'

    def _get_agent_state(self, name):
        try:
            state = self._provider.status(name)['state']
            return {'state': state}
        except InstanceNotFoundError as error:
                logger.warn(error.message)
                response.status = '404 Not Found - %s' % error.message

    def _put_agent_state(self, name):
        state = request.json['state']

        if state == 'running':
            try:
                user_cfg = self._users.config(name)
                self._provider.start(user_cfg)
                logger.info('Started agent for user %s' % name)
                return self._get_agent_state(name)
            except UserNotExistError as error:
                logger.warn(error.message)
                response.status = '404 Not Found - %s' % error.message
            except InstanceAlreadyRunningError as error:
                logger.warn(error.message)
                response.status = '409 Conflict - %s' % error.message
        else:
            try:
                self._provider.stop(name)
                logger.info('Stopped agent for user %s' % name)
                return self._get_agent_state(name)
            except InstanceNotRunningError as error:
                logger.warn(error.message)
                response.status = '409 Conflict - %s' % error.message

    def _get_agent_runtime(self, name):
        try:
            return self._provider.status(name)
        except InstanceNotFoundError as error:
            logger.warn(error.message)
            response.status = '404 Not Found - %s' % error.message

    def _authenticate_agent(self, name):
        password = request.json['password']
        result = self._authenticator.authenticate(name, password)
        if result:
            self._provider.pass_credentials_to_agent(self._users.config(name), password)
            response.status = '200 Ok'
            logger.info('User %s logged in successfully' % name)
        else:
            response.status = '403 Forbidden'
            logger.warn('Authentication failed for user %s!' % name)
        return {}

    def _reset_agent_data(self, name):
        try:
            user_config = self._users.config(name)
            self._provider.reset_data(user_config)
            return self._get_agent_state(name)
        except UserNotExistError as error:
            logger.warn(error.message)
            response.status = '404 Not Found - %s' % error.message
        except InstanceAlreadyRunningError as error:
            logger.warn(error.message)
            response.status = '409 Conflict - %s' % error.message

    def _memory_usage(self):
        return self._provider.memory_usage()

    def serve_forever(self):
        app = self.init_bottle_app()
        if self._ssl_config:
            server_adapter = SSLWSGIRefServerAdapter(host=self._bindaddr, port=self._port,
                                                     ssl_version=self._ssl_config.ssl_version,
                                                     ssl_cert_file=self._ssl_config.ssl_certfile,
                                                     ssl_key_file=self._ssl_config.ssl_keyfile,
                                                     ssl_ca_certs=self._ssl_config.ssl_ca_certs,
                                                     ssl_ciphers=self._ssl_config.ssl_ciphers)
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


class DispatcherManager(object):
    __slots__ = ('_root_path', '_mailpile_bin', '_mailpile_virtualenv', '_ssl_config', '_server', '_provider', '_bindaddr', '_leap_provider_hostname', '_leap_provider_ca', '_leap_provider_fingerprint')

    def __init__(self, root_path, mailpile_bin, ssl_config, leap_provider_hostname, leap_provider_ca, leap_provider_fingerprint=None, mailpile_virtualenv=None, provider='fork', bindaddr='127.0.0.1'):
        self._root_path = root_path
        self._mailpile_bin = mailpile_bin
        self._mailpile_virtualenv = mailpile_virtualenv
        self._ssl_config = ssl_config
        self._server = None
        self._provider = provider
        self._bindaddr = bindaddr
        self._leap_provider_hostname = leap_provider_hostname
        self._leap_provider_ca = leap_provider_ca
        self._leap_provider_fingerprint = leap_provider_fingerprint

    def serve_forever(self):
        users = Users(self._root_path)
        authenticator = Authenticator(users, self._leap_provider_hostname, self._leap_provider_ca, leap_provider_fingerprint=self._leap_provider_fingerprint)
        provider = self._create_provider()

        Thread(target=provider.initialize).start()

        logger.info('Starting REST api')
        self._server = RESTfulServer(self._ssl_config, users, authenticator, provider, bindaddr=self._bindaddr, port=DEFAULT_PORT)
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
            adapter = PixelatedDockerAdapter()
            return DockerProvider(adapter, self._leap_provider_hostname, self._leap_provider_ca, docker_host)
        else:
            adapter = MailpileAdapter(self._mailpile_bin, mailpile_virtualenv=self._mailpile_virtualenv)
            runner = ForkRunner(self._root_path, adapter)
            return ForkProvider(runner)
