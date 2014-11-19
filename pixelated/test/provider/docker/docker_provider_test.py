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
import stat
from os.path import join, isdir, isfile, exists
from tempfile import NamedTemporaryFile
from time import sleep, clock
from mock import patch, MagicMock
import pkg_resources
import requests
import json
from tempdir import TempDir
from psutil._common import pmem
from threading import Thread
from pixelated.provider.base_provider import ProviderInitializingException
from pixelated.provider.docker import DockerProvider
from pixelated.provider.docker.pixelated_adapter import PixelatedDockerAdapter
from pixelated.test.util import StringIOMatcher
from pixelated.exceptions import *
from pixelated.users import UserConfig, Users


__author__ = 'fbernitt'

import unittest


class DockerProviderTest(unittest.TestCase):
    def setUp(self):
        self.users = MagicMock(spec=Users)
        self._tmpdir = TempDir()
        self.root_path = self._tmpdir.name
        self._adapter = PixelatedDockerAdapter()

    def tearDown(self):
        self._tmpdir.dissolve()

    def test_constructor_expects_docker_url(self):
        DockerProvider(self.root_path, self._adapter, 'leap_provider', 'some docker url')

    @patch('pixelated.provider.docker.docker.Client')
    def test_initialize_builds_docker_image(self, docker_mock):
        # given
        client = docker_mock.return_value
        client.images.return_value = []
        dockerfile = pkg_resources.resource_string('pixelated.resources', 'Dockerfile.pixelated')

        # when
        DockerProvider(self._adapter, 'leap_provider', 'some leap ca', 'some docker url').initialize()

        # then
        docker_mock.assert_called_once_with(base_url="some docker url")
        client.build.assert_called_once_with(path=None, fileobj=StringIOMatcher(dockerfile), tag='pixelated:latest')

    @patch('pixelated.provider.docker.docker.Client')
    def test_initialize_skips_image_build_if_available(self, docker_mock):
        # given
        client = docker_mock.return_value
        client.images.return_value = [{'Created': 1404833111, 'VirtualSize': 297017244, 'ParentId': '57885511c8444c2b89743bef8b89eccb65f302b2a95daa95dfcc9b972807b6db', 'RepoTags': ['pixelated:latest'], 'Id': 'b4f10a2395ab8dfc5e1c0fae26fa56c7f5d2541debe54263105fe5af1d263189', 'Size': 181956643}]

        # when
        DockerProvider(self._adapter, 'leap_provider', 'some docker url').initialize()

        # then
        self.assertFalse(client.build.called)

    @patch('pixelated.provider.docker.docker.Client')
    def test_reports_initializing_while_initialize_is_running(self, docker_mock):
        # given
        client = docker_mock.return_value
        client.images.return_value = []

        def build(path, fileobj, tag):
            sleep(0.2)
            return []

        client.build.side_effect = build
        provider = DockerProvider(self._adapter, 'some provider', 'some provider ca', 'some docker url')

        self.assertTrue(provider.initializing)

        # when
        t = Thread(target=provider.initialize)  # move to thread so that initializing behaviour is observable
        t.start()

        # then
        sleep(0.1)
        self.assertTrue(provider.initializing)
        t.join()
        self.assertFalse(provider.initializing)

    def test_throws_initializing_exception_while_initializing(self):
        # given
        provider = DockerProvider(self._adapter, 'provider url', 'provider ca', 'some docker url')

        # when/then
        self.assertRaises(ProviderInitializingException, provider.start, 'test')
        self.assertRaises(ProviderInitializingException, provider.remove, 'test')
        self.assertRaises(ProviderInitializingException, provider.list_running)
        self.assertRaises(ProviderInitializingException, provider.stop, 'test')
        self.assertRaises(ProviderInitializingException, provider.status, 'test')
        self.assertRaises(ProviderInitializingException, provider.memory_usage)

    @patch('pixelated.provider.docker.docker.Client')
    def test_that_instance_can_be_started(self, docker_mock):
        client = docker_mock.return_value
        provider = self._create_initialized_provider(self._adapter, 'some docker url')
        prepare_pixelated_container = MagicMock()
        container = MagicMock()
        client.create_container.side_effect = [prepare_pixelated_container, container]
        client.wait.return_value = 0

        provider.start(self._user_config('test'))

        client.create_container.assert_any_call('pixelated', '/bin/bash -l -c "/usr/bin/pixelated-user-agent --host 0.0.0.0 --port 4567 --dispatcher /mnt/user/credentials-fifo"', name='test', volumes=['/mnt/user'], ports=[4567], environment={'DISPATCHER_LOGOUT_URL': '/auth/logout'})
        client.create_container.assert_any_call('pixelated', '/bin/true', name='pixelated_prepare', volumes=['/mnt/user'], environment={'DISPATCHER_LOGOUT_URL': '/auth/logout'})

        data_path = join(self.root_path, 'test', 'data')

        client.start.assert_any_call(container, binds={data_path: {'bind': '/mnt/user', 'ro': False}}, port_bindings={4567: 5000})
        client.start.assert_any_call(prepare_pixelated_container, binds={data_path: {'bind': '/mnt/user', 'ro': False}})

    @patch('pixelated.provider.docker.docker.Client')
    def test_that_existing_container_gets_reused(self, docker_mock):
        client = docker_mock.return_value
        client.containers.side_effect = [[], [{u'Status': u'Exited (-1) About an hour ago', u'Created': 1405332375, u'Image': u'pixelated:latest', u'Ports': [], u'Command': u'/bin/bash -l -c "/usr/bin/pixelated-user-agent --dispatcher"', u'Names': [u'/test'], u'Id': u'adfd4633fc42734665d7d98076b19b5f439648678b3b76db891f9d5072af50b6'}]]
        provider = self._create_initialized_provider(self._adapter, 'some docker url')
        container = MagicMock()
        client.create_container.return_value = container

        provider.start(self._user_config('test'))

        client.containers.assert_called_with(all=True)
        self.assertFalse(client.build.called)

    @patch('pixelated.provider.docker.docker.Client')
    def test_running_containers_empty_if_none_started(self, docker_mock):
        client = docker_mock.return_value
        client.containers.return_value = []
        provider = self._create_initialized_provider(self._adapter, 'some docker url')

        running = provider.list_running()

        self.assertEqual([], running)

    @patch('pixelated.provider.docker.docker.Client')
    def test_running_returns_running_container(self, docker_mock):
        client = docker_mock.return_value
        client.containers.side_effect = [[], [], [{u'Status': u'Up 20 seconds', u'Created': 1404904929, u'Image': u'pixelated:latest', u'Ports': [], u'Command': u'sleep 100', u'Names': [u'/test'], u'Id': u'f59ee32d2022b1ab17eef608d2cd617b7c086492164b8c411f1cbcf9bfef0d87'}]]
        client.wait.return_value = 0
        provider = self._create_initialized_provider(self._adapter, 'some docker url')
        provider.start(self._user_config('test'))

        running = provider.list_running()

        self.assertEqual(['test'], running)

    @patch('pixelated.provider.docker.docker.Client')
    def test_a_container_cannot_be_started_twice(self, docker_mock):
        client = docker_mock.return_value
        client.containers.side_effect = [[], [], [{u'Status': u'Up 20 seconds', u'Created': 1404904929, u'Image': u'pixelated:latest', u'Ports': [], u'Command': u'sleep 100', u'Names': [u'/test'], u'Id': u'f59ee32d2022b1ab17eef608d2cd617b7c086492164b8c411f1cbcf9bfef0d87'}]]
        client.wait.return_value = 0
        provider = self._create_initialized_provider(self._adapter, 'some docker url')
        user_config = self._user_config('test')
        provider.start(user_config)

        self.assertRaises(InstanceAlreadyRunningError, provider.start, user_config)

    @patch('pixelated.provider.docker.docker.Client')
    def test_stopping_not_running_container_raises_value_error(self, docker_mock):
        client = docker_mock.return_value
        client.containers.return_value = []
        provider = self._create_initialized_provider(self._adapter, 'some docker url')

        self.assertRaises(InstanceNotRunningError, provider.stop, 'test')

    @patch('pixelated.provider.docker.docker.Client')
    def test_stop_running_container(self, docker_mock):
        # given
        client = docker_mock.return_value
        container = {u'Status': u'Up 20 seconds', u'Created': 1404904929, u'Image': u'pixelated:latest', u'Ports': [{u'IP': u'0.0.0.0', u'Type': u'tcp', u'PublicPort': 5000, u'PrivatePort': 4567}], u'Command': u'sleep 100', u'Names': [u'/test'], u'Id': u'f59ee32d2022b1ab17eef608d2cd617b7c086492164b8c411f1cbcf9bfef0d87'}
        client.containers.side_effect = [[], [], [container], [container], [container]]
        client.wait.return_value = 0
        provider = self._create_initialized_provider(self._adapter, 'some docker url')
        provider.start(self._user_config('test'))
        # when
        provider.stop('test')

        # then
        client.stop.assert_called_once_with(container, timeout=10)
        self.assertFalse(5000 in provider._used_ports())

    @patch('pixelated.provider.docker.docker.Client')
    def test_stop_running_container_calls_kill_if_stop_times_out(self, docker_mock):
        # given
        client = docker_mock.return_value
        container = {u'Status': u'Up 20 seconds', u'Created': 1404904929, u'Image': u'pixelated:latest', u'Ports': [{u'IP': u'0.0.0.0', u'Type': u'tcp', u'PublicPort': 5000, u'PrivatePort': 4567}], u'Command': u'sleep 100', u'Names': [u'/test'], u'Id': u'f59ee32d2022b1ab17eef608d2cd617b7c086492164b8c411f1cbcf9bfef0d87'}
        client.containers.side_effect = [[], [], [container], [container], [container]]
        client.wait.return_value = 0
        client.stop.side_effect = requests.exceptions.Timeout

        provider = self._create_initialized_provider(self._adapter, 'some docker url')
        provider.start(self._user_config('test'))

        # when
        provider.stop('test')

        # then
        client.stop.assert_called_once_with(container, timeout=10)
        client.kill.assert_called_once_with(container)

    @patch('pixelated.provider.docker.docker.Client')
    def test_status_stopped(self, docker_mock):
        provider = self._create_initialized_provider(self._adapter, 'some docker url')

        self.assertEqual({'state': 'stopped'}, provider.status('test'))

    @patch('pixelated.provider.docker.docker.Client')
    def test_status_running(self, docker_mock):
        client = docker_mock.return_value
        container = {u'Status': u'Up 20 seconds', u'Created': 1404904929, u'Image': u'pixelated:latest', u'Ports': [{u'IP': u'0.0.0.0', u'Type': u'tcp', u'PublicPort': 5000, u'PrivatePort': 33144}], u'Command': u'sleep 100', u'Names': [u'/test'], u'Id': u'f59ee32d2022b1ab17eef608d2cd617b7c086492164b8c411f1cbcf9bfef0d87'}
        client.containers.side_effect = [[], [], [container], [container]]
        client.wait.return_value = 0
        provider = self._create_initialized_provider(self._adapter, 'some docker url')
        provider.start(self._user_config('test'))

        self.assertEqual({'state': 'running', 'port': 5000}, provider.status('test'))

    @patch('pixelated.provider.docker.Process')
    @patch('pixelated.provider.docker.docker.Client')
    def test_memory_usage(self, docker_mock, process_mock):
        # given
        container = {u'Status': u'Up 20 seconds', u'Created': 1404904929, u'Image': u'pixelated:latest', u'Ports': [{u'IP': u'0.0.0.0', u'Type': u'tcp', u'PublicPort': 5000, u'PrivatePort': 33144}], u'Command': u'sleep 100', u'Names': [u'/test'], u'Id': u'f59ee32d2022b1ab17eef608d2cd617b7c086492164b8c411f1cbcf9bfef0d87'}
        info = {u'HostsPath': u'/var/lib/docker/containers/f2cdb04277e9e056c610240edffe8ff94ae272e462312c270e5300975d60af89/hosts', u'Created': u'2014-07-14T13:17:46.17558664Z', u'Image': u'f63df19194389be6481a174b36d291c483c8982d5c07485baa71a46b7f6582c8', u'Args': [], u'Driver': u'aufs', u'HostConfig': {u'PortBindings': {u'4567/tcp': [{u'HostPort': u'5000', u'HostIp': u'0.0.0.0'}]}, u'NetworkMode': u'', u'Links': None, u'LxcConf': None, u'ContainerIDFile': u'', u'Binds': [u'/tmp/multipile/folker:/mnt/user:rw'], u'PublishAllPorts': False, u'Dns': None, u'DnsSearch': None, u'Privileged': False, u'VolumesFrom': None}, u'MountLabel': u'', u'VolumesRW': {u'/mnt/user': True}, u'State': {u'Pid': 3250, u'Paused': False, u'Running': True, u'FinishedAt': u'0001-01-01T00:00:00Z', u'StartedAt': u'2014-07-14T13:17:46.601922899Z', u'ExitCode': 0}, u'ExecDriver': u'native-0.2', u'ResolvConfPath': u'/etc/resolv.conf', u'Volumes': {u'/mnt/user': u'/tmp/multipile/folker'}, u'Path': u'/bin/bash -l -c "/usr/bin/pixelated-user-agent --dispatcher"', u'HostnamePath': u'/var/lib/docker/containers/f2cdb04277e9e056c610240edffe8ff94ae272e462312c270e5300975d60af89/hostname', u'ProcessLabel': u'', u'Config': {u'MemorySwap': 0, u'Hostname': u'f2cdb04277e9', u'Entrypoint': None, u'PortSpecs': None, u'Memory': 0, u'OnBuild': None, u'OpenStdin': False, u'Cpuset': u'', u'Env': [u'HOME=/', u'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'], u'User': u'', u'CpuShares': 0, u'AttachStdout': True, u'NetworkDisabled': False, u'WorkingDir': u'', u'Cmd': [u'/bin/bash -l -c "/usr/bin/pixelated-user-agent --dispatcher"'], u'StdinOnce': False, u'AttachStdin': False, u'Volumes': {u'/mnt/user': {}}, u'Tty': False, u'AttachStderr': True, u'Domainname': u'', u'Image': u'pixelated', u'ExposedPorts': {u'4567/tcp': {}}}, u'Id': u'f2cdb04277e9e056c610240edffe8ff94ae272e462312c270e5300975d60af89', u'NetworkSettings': {u'Bridge': u'docker0', u'PortMapping': None, u'Gateway': u'172.17.42.1', u'IPPrefixLen': 16, u'IPAddress': u'172.17.0.14', u'Ports': {u'4567/tcp': [{u'HostPort': u'5000', u'HostIp': u'0.0.0.0'}]}}, u'Name': u'/folker'}
        client = docker_mock.return_value
        client.containers.return_value = [container]
        client.inspect_container.return_value = info

        psutil_mock = process_mock.return_value
        psutil_mock.memory_info.return_value = pmem(1024, 2048)

        provider = self._create_initialized_provider(self._adapter, 'some docker url')

        # when
        usage = provider.memory_usage()

        # then
        self.assertEqual({'total_usage': 1024,
                          'average_usage': 1024,
                          'agents': [
                              {'name': 'test', 'memory_usage': 1024}
                          ]}, usage)

    def test_remove_error_if_not_exist(self):
        provider = self._create_initialized_provider(self._adapter, 'some docker url')

        self.assertRaises(ValueError, provider.remove, self._user_config('does_not_exist'))

    @patch('pixelated.provider.docker.docker.Client')
    def test_remove(self, docker_mock):
        # given
        user_config = self._user_config('test')
        os.makedirs(join(user_config.path, 'data'))
        client = docker_mock.return_value
        client.containers.return_value = []
        provider = self._create_initialized_provider(self._adapter, 'some docker url')

        # when
        provider.remove(user_config)

        # then
        self.assertTrue(exists(user_config.path))
        self.assertFalse(exists(join(user_config.path, 'data')))

    @patch('pixelated.provider.docker.docker.Client')
    def test_cannot_remove_while_running(self, docker_mock):
        # given
        client = docker_mock.return_value
        container = {u'Status': u'Up 20 seconds', u'Created': 1404904929, u'Image': u'pixelated:latest', u'Ports': [{u'IP': u'0.0.0.0', u'Type': u'tcp', u'PublicPort': 5000, u'PrivatePort': 4567}], u'Command': u'sleep 100', u'Names': [u'/test'], u'Id': u'f59ee32d2022b1ab17eef608d2cd617b7c086492164b8c411f1cbcf9bfef0d87'}
        client.containers.side_effect = [[], [], [container]]
        client.wait.return_value = 0

        provider = self._create_initialized_provider(self._adapter, 'some docker url')
        user_config = self._user_config('test')
        provider.start(user_config)

        # when/then
        self.assertRaises(ValueError, provider.remove, user_config)

    @patch('pixelated.provider.docker.TempDir')
    @patch('pixelated.provider.docker.pkg_resources')
    @patch('pixelated.provider.docker.docker.Client')
    def test_use_build_script_instead_of_docker_file_if_available(self, docker_mock, res_mock, tempDir_mock):
        # given
        provider = DockerProvider(self._adapter, 'leap_provider', 'some docker url')

        tempBuildDir = TempDir()
        try:
            tempDir_mock.return_value = tempBuildDir
            tempBuildDir_name = tempBuildDir.name
            with NamedTemporaryFile() as file:
                res_mock.resource_exists.return_value = True
                res_mock.resource_string.return_value = '#!/bin/bash\necho %s $PWD > %s' % (file.name, file.name)

                # when
                provider.initialize()

                # then
                res_mock.resource_exists.assert_called_with('pixelated.resources', 'init-pixelated-docker-context.sh')
                res_mock.resource_string.assert_called_with('pixelated.resources', 'init-pixelated-docker-context.sh')
                with open(file.name, "r") as input:
                    data = input.read().replace('\n', '')
                    self.assertEqual('%s %s' % (file.name, os.path.realpath(tempBuildDir_name)), data)

                docker_mock.return_value.build.assert_called_once_with(path=tempBuildDir_name, tag='pixelated:latest', fileobj=None)
        finally:
            tempBuildDir.dissolve()

    @patch('pixelated.provider.docker.docker.Client')
    def test_that_pass_credentials_to_agent_writes_password_to_fifo(self, docker_mock):
        provider = DockerProvider(self._adapter, 'leap_provider_hostname', 'some docker url')
        provider.initialize()
        user_config = self._user_config('test')
        provider.pass_credentials_to_agent(user_config, 'password')

        fifo_file = join(user_config.path, 'data', 'credentials-fifo')
        self.assertTrue(stat.S_ISFIFO(os.stat(fifo_file).st_mode))
        with open(fifo_file, 'r') as fifo:
            config = json.loads(fifo.read())

        self.assertEqual('leap_provider_hostname', config['leap_provider_hostname'])
        self.assertEqual('test', config['user'])
        self.assertEqual('password', config['password'])
        self._assert_file_gets_deleted(fifo_file)

    def _assert_file_gets_deleted(self, filename):
        start = clock()
        timeout = 5
        while (clock() - start) < timeout and exists(filename):
            sleep(0.1)

        self.assertFalse(exists(filename))

    @patch('pixelated.provider.docker.docker.Client')
    def footest_that_authenticate_deletes_fifo_after_timeout(self, docker_mock):
        provider = DockerProvider(self._adapter, 'some docker url')
        provider.initialize()
        provider.add('test', 'password')
        fifo_file = join(self.root_path, 'test', 'data', 'credentials-fifo')
        provider.authenticate('test', 'password')

        sleep(3)

        self.assertFalse(stat.S_ISFIFO(os.stat(fifo_file).st_mode))

    def _create_initialized_provider(self, adapter, docker_url=DockerProvider.DEFAULT_DOCKER_URL):
        provider = DockerProvider(adapter, 'leap_provider_hostname', 'leap provider ca', docker_url)
        provider._initializing = False
        return provider

    def _user_config(self, name):
        path = join(self.root_path, name)
        os.makedirs(path)
        return UserConfig(name, path)
