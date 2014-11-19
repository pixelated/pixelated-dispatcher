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
from os.path import join
from os import path
import stat
import subprocess
import time
import tempfile
import multiprocessing

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

__author__ = 'fbernitt'


class CredentialsFifoWriterProcess(object):

    def __init__(self, filename, leap_provider, user, password):
        self._filename = filename
        self._leap_provider = leap_provider
        self._user = user
        self._password = password

    def start(self):
        os.mkfifo(self._filename)
        self._process = multiprocessing.Process(target=self.run)
        self._process.daemon = True
        self._process.start()

    def run(self):
        if os.path.exists(self._filename):
            with open(self._filename, 'w') as fifo:
                fifo.write(json.dumps({'leap_provider_hostname': self._leap_provider, 'user': self._user, 'password': self._password}))
            os.remove(self._filename)

    def terminate(self):
        self._process.terminate()
        if os.path.exists(self._filename):
            os.remove(self._filename)


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
    __slots__ = ('_docker_host', '_docker', '_ports', '_adapter', '_leap_provider_hostname', '_leap_provider_ca')

    DEFAULT_DOCKER_URL = 'http+unix://var/run/docker.sock'

    def __init__(self, adapter, leap_provider_hostname, leap_provider_ca, docker_url=DEFAULT_DOCKER_URL):
        super(DockerProvider, self).__init__()
        self._docker_url = docker_url
        self._docker = docker.Client(base_url=docker_url)
        self._ports = set()
        self._adapter = adapter
        self._leap_provider_hostname = leap_provider_hostname
        self._leap_provider_ca = leap_provider_ca

    def initialize(self):
        imgs = self._docker.images()
        found = False
        for img in imgs:
            if '%s:latest' % self._adapter.app_name() in img['RepoTags']:
                found = True

        if not found:
            # build the image
            start = time.time()
            logger.info('No docker image for %s found! Triggering build.' % self._adapter.app_name())
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
            logger.info('Finished image %s build in %d seconds' % ('%s:latest' % self._adapter.app_name(), time.time() - start))
        self._initializing = False

    def _build_image(self, path, fileobj):
        stream = self._docker.build(path=path, fileobj=fileobj, tag='%s:latest' % self._adapter.app_name())
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

    def pass_credentials_to_agent(self, user_config, password):
        _mkdir_if_not_exists(self._data_path(user_config))
        self._write_credentials_to_fifo(user_config, password)

    def _write_credentials_to_fifo(self, user_config, password):
        fifo_file = path.join(self._data_path(user_config), 'credentials-fifo')

        p = CredentialsFifoWriterProcess(fifo_file, self._leap_provider_hostname, user_config.username, password)
        p.start()

        self._wait_for_fifo_to_be_created(fifo_file, timeout_in_s=1)

        def kill_process_after_timeout(process):
            process.terminate()

        watchdog = Watchdog(5, userHandler=kill_process_after_timeout, args=[p])

    def _wait_for_fifo_to_be_created(self, fifo_file, timeout_in_s):
        start = time.clock()
        while time.clock() - start < timeout_in_s and not path.exists(fifo_file):
            time.sleep(0.01)

        if not path.exists(fifo_file):
            raise Exception('Unexpected: FIFO file %s has not been created' % fifo_file)

    def start(self, user_config):
        self._ensure_initialized()
        name = user_config.username
        self._start(user_config)

        cm = self._map_container_by_name(all=True)
        if name not in cm:
            self._setup_instance(user_config, cm)
            c = self._docker.create_container(self._adapter.app_name(), self._adapter.run_command(), name=name, volumes=['/mnt/user'], ports=[self._adapter.port()], environment=self._adapter.environment('/mnt/user'))
        else:
            c = cm[name]
        data_path = self._data_path(user_config)
        port = self._next_available_port()
        self._ports.add(port)

        self._docker.start(c, binds={data_path: {'bind': '/mnt/user', 'ro': False}}, port_bindings={self._adapter.port(): port})

    def _setup_instance(self, user_config, container_map):
        data_path = join(user_config.path, 'data')

        container_name = '%s_prepare' % self._adapter.app_name()
        if container_name not in container_map:
            c = self._docker.create_container(self._adapter.app_name(), self._adapter.setup_command(), name=container_name, volumes=['/mnt/user'], environment=self._adapter.environment('/mnt/user'))
        else:
            c = container_map[container_name]

        self._docker.start(c, binds={data_path: {'bind': '/mnt/user', 'ro': False}})
        s = self._docker.wait(c)
        if s != 0:
            raise Exception('Failed to initialize mailbox: %d!' % s)

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
