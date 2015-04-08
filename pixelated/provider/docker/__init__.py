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
import io
import os
import signal
from os.path import join, exists
from os import path
import stat
import subprocess
import time
import tempfile
import multiprocessing
import socket

import pkg_resources
import docker
import psutil
import requests
from psutil import Process
import shutil
import json

from pixelated.provider.base_provider import BaseProvider, _mkdir_if_not_exists
from pixelated.common import Watchdog
from pixelated.common import logger
from pixelated.exceptions import InstanceAlreadyRunningError

__author__ = 'fbernitt'


DOCKER_API_VERSION = '1.14'


class CredentialsToDockerStdinWriter(object):

    __slots__ = ('_docker_url', '_container_id', '_leap_provider', '_user', '_password', '_process')

    def __init__(self, docker_url, container_id, leap_provider, user, password):
        self._docker_url = docker_url
        self._container_id = container_id
        self._leap_provider = leap_provider
        self._user = user
        self._password = password

    def start(self):
        self._process = multiprocessing.Process(target=self.run)
        self._process.daemon = True
        self._process.start()

    def run(self):
        try:
            params = {
                'stdin': True,
                'stream': True,
                'stdout': False,
                'stderr': False}

            client = docker.Client(base_url=self._docker_url, version=DOCKER_API_VERSION)

            s = client.attach_socket(container=self._container_id, params=params)
            s.send("%s\n" % json.dumps({'leap_provider_hostname': self._leap_provider, 'user': self._user, 'password': self._password}))
            s.shutdown(socket.SHUT_WR)
            s.close()
        except Exception, e:
            logger.error('While passing credentials to container %s running on %s: %s' % (self._container_id, self._docker_url, str(e.message)))

    def terminate(self):
        self._process.terminate()


class TempDir(object):
    """ class for temporary directories
    creates a (named) directory which is deleted after use.
    All files created within the directory are destroyed
    Might not work on windows when the files are still opened
    """
    def __init__(self, suffix="", prefix="tmp", basedir=None):
        self.name = tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=basedir)

    def __del__(self):
        if "name" in self.__dict__:
            self.__exit__(None, None, None)

    def __enter__(self):
        return self.name

    def __exit__(self, *errstuff):
        return self.dissolve()

    def dissolve(self):
        """remove all files and directories created within the tempdir"""
        if self.name:
            shutil.rmtree(self.name)
        self.name = ""

    def __str__(self):
        if self.name:
            return "temporary directory at: %s" % (self.name,)
        else:
            return "dissolved temporary directory"


class DockerProvider(BaseProvider):
    __slots__ = ('_docker_url', '_docker', '_ports', '_adapter', '_leap_provider_hostname', '_leap_provider_x509', '_credentials')

    DEFAULT_DOCKER_URL = 'http+unix://var/run/docker.sock'

    def __init__(self, adapter, leap_provider_hostname, leap_provider_x509, docker_url=DEFAULT_DOCKER_URL):
        super(DockerProvider, self).__init__()
        self._docker_url = docker_url
        self._docker = docker.Client(base_url=docker_url, version=DOCKER_API_VERSION)
        self._ports = set()
        self._adapter = adapter
        self._leap_provider_hostname = leap_provider_hostname
        self._leap_provider_x509 = leap_provider_x509
        self._credentials = {}
        self._check_docker_connection()

    def _check_docker_connection(self):
        try:
            self._docker.info()
        except Exception, e:
            logger.error('Failed to talk to docker: %s' % e.message)
            raise

    def initialize(self):
        self._initialize_logger_container()

        if not self._image_exists(self._adapter.docker_image_name()):
            # build the image
            start = time.time()
            logger.info('No docker image for %s found! Triggering build.' % self._adapter.app_name())
            if '/' in self._adapter.docker_image_name():
                self._download_image(self._adapter.docker_image_name())
                logger.info('Finished downloading docker image')
            else:
                if pkg_resources.resource_exists('pixelated.resources', 'init-%s-docker-context.sh' % self._adapter.app_name()):
                    fileobj = None
                    content = pkg_resources.resource_string('pixelated.resources', 'init-%s-docker-context.sh' % self._adapter.app_name())
                    with TempDir() as dir:
                        filename = join(dir, 'run.sh')
                        with open(filename, 'w') as fd:
                            fd.write(content)
                            fd.close()
                            os.chmod(filename, stat.S_IRWXU)
                            subprocess.call([filename], cwd=dir)
                        path = dir
                        self._build_image(path, fileobj)
                else:
                    fileobj = io.StringIO(self._dockerfile())
                    path = None
                    self._build_image(path, fileobj)
                logger.info('Finished image %s build in %d seconds' % ('%s:latest' % self._adapter.docker_image_name(), time.time() - start))
        self._initializing = False

    def _image_exists(self, docker_image_name):
        imgs = self._docker.images()
        repo_tag = docker_image_name + ':latest'
        for img in imgs:
            if repo_tag in img['RepoTags']:
                return True

        return False

    def _download_image(self, docker_image_name):
        stream = self._docker.pull(repository=docker_image_name, tag='latest', stream=True)
        lines = []
        for event in stream:
            data = json.loads(event)
            if 'status' in data:
                logger.debug(data['status'])
                lines.append(data['status'])
            if 'error' in data:
                logger.error('Failed to pull image %s: %s' % (docker_image_name, data['error']))
                logger.error('Replaying docker pull output')
                for line in lines:
                    logger.error('Docker output: %s' % line)
                logger.error('Terminating process by sending TERM signal')
                os.kill(os.getpid(), signal.SIGTERM)

    def _build_image(self, path, fileobj):
        stream = self._docker.build(path=path, fileobj=fileobj, tag='%s:latest' % self._adapter.docker_image_name())
        lines = []
        for event in stream:
            data = json.loads(event)
            if 'stream' in data:
                logger.debug(data['stream'])
                lines.append(data['stream'])
            if 'error' in data:
                logger.error('Whoops! Failed to build image: %s' % data['error'])
                logger.error('Replaying docker image build output')
                for line in lines:
                    logger.error('Docker output: %s' % line)
                logger.error('Terminating process by sending TERM signal')
                os.kill(os.getpid(), signal.SIGTERM)

    def _initialize_logger_container(self):
        LOGGER_CONTAINER_NAME = 'pixelated/logspout'

        if not self._image_exists(LOGGER_CONTAINER_NAME):
            logger.info('Logger container not found. Downloading...')
            self._download_image(LOGGER_CONTAINER_NAME)
            logger.info('Finished downloading logger container')

        logger_container = self._docker.create_container(
            image=LOGGER_CONTAINER_NAME + ':latest',
            command='syslog://localhost:514',
            volumes='/tmp/docker.sock'
        )

        self._docker.start(
            container=logger_container.get('Id'),
            network_mode='host',
            binds={'/var/run/docker.sock': {
                'bind': '/tmp/docker.sock',
                'ro': False
            }}
        )

        logger.info('Logger container initialized successfully')

    def pass_credentials_to_agent(self, user_config, password):
        self._credentials[user_config.username] = password  # remember crendentials until agent gets started

    def _write_credentials_to_docker_stdin(self, user_config):
        if user_config.username not in self._credentials:
            return

        password = self._credentials[user_config.username]
        p = CredentialsToDockerStdinWriter(self._docker_url, user_config.username, self._leap_provider_hostname, user_config.username, password)
        p.start()

        def kill_process_after_timeout(process):
            process.terminate()

        Watchdog(5, userHandler=kill_process_after_timeout, args=[p])

    def start(self, user_config):
        self._ensure_initialized()
        name = user_config.username
        self._start(user_config)

        cm = self._map_container_by_name(all=True)
        if name not in cm:
            self._setup_instance(user_config, cm)
            uid = os.getuid()
            c = self._docker.create_container(self._adapter.docker_image_name(), self._adapter.run_command(self._leap_provider_x509), user=uid, name=name, volumes=['/mnt/user'], ports=[self._adapter.port()], environment=self._adapter.environment('/mnt/user'), stdin_open=True)
        else:
            c = cm[name]
        data_path = self._data_path(user_config)

        self._add_leap_ca_to_user_data_path(data_path)

        port = self._next_available_port()
        self._ports.add(port)

        self._docker.start(
            c,
            binds={data_path: {'bind': '/mnt/user', 'ro': False}},
            port_bindings={self._adapter.port(): ('127.0.0.1', port)})

        self._write_credentials_to_docker_stdin(user_config)

    def _setup_instance(self, user_config, container_map):
        data_path = join(user_config.path, 'data')

        container_name = '%s_prepare' % self._adapter.app_name()
        if container_name not in container_map:
            c = self._docker.create_container(self._adapter.docker_image_name(), self._adapter.setup_command(), name=container_name, volumes=['/mnt/user'], environment=self._adapter.environment('/mnt/user'))
        else:
            c = container_map[container_name]

        self._docker.start(c, binds={data_path: {'bind': '/mnt/user', 'ro': False}})
        s = self._docker.wait(c)
        if s != 0:
            raise Exception('Failed to initialize mailbox: %d!' % s)

    def _add_leap_ca_to_user_data_path(self, data_path):
        if self._leap_provider_x509.has_ca_bundle():
            cert_file = self._leap_provider_x509.ca_bundle
            if exists(cert_file):
                shutil.copyfile(cert_file, join(data_path, 'dispatcher-leap-provider-ca.crt'))

    def list_running(self):
        self._ensure_initialized()

        running = []

        for name in self._map_container_by_name().keys():
            running.append(name)

        return running

    def _map_container_by_name(self, all=False):
        containers = self._docker.containers(all=all)
        names = {}
        for c in containers:
            name = c['Names'][0][1:]  # skip leading slash in container name
            names[name] = c
        return names

    def stop(self, name):
        self._stop(name)
        if name in self._credentials:
            del self._credentials[name]

        for cname, c in self._map_container_by_name().iteritems():
            if name == cname:
                port = self._docker_container_port(name)
                try:
                    self._docker.stop(c, timeout=10)
                except requests.exceptions.Timeout:
                    self._docker.kill(c)
                self._ports.remove(port)
                return

        raise ValueError

    def reset_data(self, user_config):
        self._ensure_initialized()

        if user_config.username in self.list_running():
            raise InstanceAlreadyRunningError('Container %s is currently running. Please stop before resetting data!' % user_config.username)

        if path.exists(user_config.path):
            data_path = self._data_path(user_config)
            if path.exists(data_path):
                shutil.rmtree(data_path)
        else:
            raise ValueError('No agent with name %s' % user_config.username)

    def _agent_port(self, name):
        return self._docker_container_port(name)

    def _dockerfile(self):
        return unicode(pkg_resources.resource_string('pixelated.resources', 'Dockerfile.%s' % self._adapter.app_name()))

    def _docker_container_by_name(self, name):
        return self._map_container_by_name()[name]

    def _docker_container_port(self, name):
        c = self._docker_container_by_name(name)
        return c['Ports'][0]['PublicPort']

    def _next_available_port(self):
        inital_port = 5000

        port = inital_port
        while port in self._ports:
            port += 1

        return port

    def _used_ports(self):
        return self._ports

    def memory_usage(self):
        self._ensure_initialized()

        usage = 0
        agents = []

        for name, container in self._map_container_by_name().iteritems():
            info = self._docker.inspect_container(container)
            pid = info['State']['Pid']
            process = Process(pid)
            mem = process.memory_info()
            usage = usage + mem.rss
            agents.append({'name': name, 'memory_usage': mem.rss})

        avg = usage / len(agents) if len(agents) > 0 else 0

        return {'total_usage': usage, 'average_usage': avg, 'agents': agents}

    def _free_memory(self):
        return psutil.virtual_memory().free
