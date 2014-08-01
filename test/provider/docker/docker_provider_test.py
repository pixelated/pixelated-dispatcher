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
from os.path import join, isdir, isfile, exists
from tempfile import NamedTemporaryFile

from mock import patch, MagicMock
import pkg_resources
import requests
from tempdir import TempDir
from psutil._common import pmem

from provider.base_provider import BaseProvider
from provider.docker import DockerProvider, MailpileDockerAdapter
from test.util import StringIOMatcher


__author__ = 'fbernitt'

import unittest


class DockerProviderTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = TempDir()
        self.root_path = self._tmpdir.name
        self._adapter = MailpileDockerAdapter()

    def tearDown(self):
        self._tmpdir.dissolve()

    def test_constructor_expects_docker_url(self):
        DockerProvider(self.root_path, self._adapter, 'some docker url')

    @patch('provider.docker.docker.Client')
    def test_initialize_builds_docker_image(self, docker_mock):
        # given
        client = docker_mock.return_value
        client.images.return_value = []
        dockerfile = pkg_resources.resource_string('resources', 'Dockerfile.mailpile')

        # when
        DockerProvider(self.root_path, self._adapter, 'some docker url').initialize()

        # then
        docker_mock.assert_called_once_with(base_url="some docker url")
        client.build.assert_called_once_with(path=None, fileobj=StringIOMatcher(dockerfile), tag='mailpile:latest')

    @patch('provider.docker.docker.Client')
    def test_initialize_skips_image_build_if_available(self, docker_mock):
        # given
        client = docker_mock.return_value
        client.images.return_value = [{'Created': 1404833111, 'VirtualSize': 297017244, 'ParentId': '57885511c8444c2b89743bef8b89eccb65f302b2a95daa95dfcc9b972807b6db', 'RepoTags': ['mailpile:latest'], 'Id': 'b4f10a2395ab8dfc5e1c0fae26fa56c7f5d2541debe54263105fe5af1d263189', 'Size': 181956643}]

        # when
        DockerProvider(self.root_path, self._adapter, 'some docker url').initialize()

        # then
        self.assertFalse(client.build.called)

    def test_add(self):
        DockerProvider(self.root_path, self._adapter, 'some docker url').add('test', 'password')

        instance_path = join(self.root_path, 'test')
        data_dir = join(instance_path, 'data')
        cfg_file = join(instance_path, BaseProvider.CFG_FILE_NAME)

        self.assertTrue(isdir(instance_path), 'No folder for user has been created')
        self.assertTrue(isdir(data_dir), 'No folder for mailpile has been created')
        self.assertTrue(isfile(cfg_file), 'No config file had been created')

    @patch('provider.docker.docker.Client')
    def test_that_non_existing_instance_cannot_be_started(self, docker_mock):
        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')

        self.assertRaises(ValueError, provider.start, 'test')

    @patch('provider.docker.docker.Client')
    def test_that_instance_can_be_started(self, docker_mock):
        client = docker_mock.return_value
        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')
        prepare_mailpile_container = MagicMock()
        container = MagicMock()
        client.create_container.side_effect = [prepare_mailpile_container, container]
        client.wait.return_value = 0

        provider.add('test', 'password')
        provider.start('test')

        client.create_container.assert_any_call('mailpile', '/Mailpile.git/mp --www', name='test', volumes=['/mnt/user'], ports=[33411], environment={'MAILPILE_HOME': '/mnt/user'})
        client.create_container.assert_any_call('mailpile', '/Mailpile.git/mp --setup --set sys.http_host=0.0.0.0', name='mailpile_prepare', volumes=['/mnt/user'], environment={'MAILPILE_HOME': '/mnt/user'})

        data_path = join(self.root_path, 'test', 'data')

        client.start.assert_any_call(container, binds={data_path: {'bind': '/mnt/user', 'ro': False}}, port_bindings={33411: 5000})
        client.start.assert_any_call(prepare_mailpile_container, binds={data_path: {'bind': '/mnt/user', 'ro': False}})

    @patch('provider.docker.docker.Client')
    def test_that_existing_container_gets_reused(self, docker_mock):
        client = docker_mock.return_value
        client.containers.side_effect = [[], [{u'Status': u'Exited (-1) About an hour ago', u'Created': 1405332375, u'Image': u'mailpile:latest', u'Ports': [], u'Command': u'/Mailpile.git/mp --www', u'Names': [u'/test'], u'Id': u'adfd4633fc42734665d7d98076b19b5f439648678b3b76db891f9d5072af50b6'}]]
        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')
        container = MagicMock()
        client.create_container.return_value = container

        provider.add('test', 'password')
        provider.start('test')

        client.containers.assert_called_with(all=True)
        self.assertFalse(client.build.called)

    @patch('provider.docker.docker.Client')
    def test_running_containers_empty_if_none_started(self, docker_mock):
        client = docker_mock.return_value
        client.containers.return_value = []
        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')

        running = provider.list_running()

        self.assertEqual([], running)

    @patch('provider.docker.docker.Client')
    def test_running_returns_running_container(self, docker_mock):
        client = docker_mock.return_value
        client.containers.side_effect = [[], [], [{u'Status': u'Up 20 seconds', u'Created': 1404904929, u'Image': u'mailpile:latest', u'Ports': [], u'Command': u'sleep 100', u'Names': [u'/test'], u'Id': u'f59ee32d2022b1ab17eef608d2cd617b7c086492164b8c411f1cbcf9bfef0d87'}]]
        client.wait.return_value = 0
        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')
        provider.add('test', 'password')
        provider.start('test')

        running = provider.list_running()

        self.assertEqual(['test'], running)

    @patch('provider.docker.docker.Client')
    def test_a_container_cannot_be_started_twice(self, docker_mock):
        client = docker_mock.return_value
        client.containers.side_effect = [[], [], [{u'Status': u'Up 20 seconds', u'Created': 1404904929, u'Image': u'mailpile:latest', u'Ports': [], u'Command': u'sleep 100', u'Names': [u'/test'], u'Id': u'f59ee32d2022b1ab17eef608d2cd617b7c086492164b8c411f1cbcf9bfef0d87'}]]
        client.wait.return_value = 0
        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')
        provider.add('test', 'password')
        provider.start('test')

        self.assertRaises(ValueError, provider.start, 'test')

    @patch('provider.docker.docker.Client')
    def test_stopping_not_running_container_raises_value_error(self, docker_mock):
        client = docker_mock.return_value
        client.containers.return_value = []
        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')
        provider.add('test', 'password')

        self.assertRaises(ValueError, provider.stop, 'test')

    @patch('provider.docker.docker.Client')
    def test_stop_running_container(self, docker_mock):
        # given
        client = docker_mock.return_value
        container = {u'Status': u'Up 20 seconds', u'Created': 1404904929, u'Image': u'mailpile:latest', u'Ports': [{u'IP': u'0.0.0.0', u'Type': u'tcp', u'PublicPort': 5000, u'PrivatePort': 33411}], u'Command': u'sleep 100', u'Names': [u'/test'], u'Id': u'f59ee32d2022b1ab17eef608d2cd617b7c086492164b8c411f1cbcf9bfef0d87'}
        client.containers.side_effect = [[], [], [container], [container], [container]]
        client.wait.return_value = 0
        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')
        provider.add('test', 'password')
        provider.start('test')
        # when
        provider.stop('test')

        # then
        client.stop.assert_called_once_with(container, timeout=10)
        self.assertFalse(5000 in provider._used_ports())

    @patch('provider.docker.docker.Client')
    def test_stop_running_container_calls_kill_if_stop_times_out(self, docker_mock):
        # given
        client = docker_mock.return_value
        container = {u'Status': u'Up 20 seconds', u'Created': 1404904929, u'Image': u'mailpile:latest', u'Ports': [{u'IP': u'0.0.0.0', u'Type': u'tcp', u'PublicPort': 5000, u'PrivatePort': 33411}], u'Command': u'sleep 100', u'Names': [u'/test'], u'Id': u'f59ee32d2022b1ab17eef608d2cd617b7c086492164b8c411f1cbcf9bfef0d87'}
        client.containers.side_effect = [[], [], [container], [container], [container]]
        client.wait.return_value = 0
        client.stop.side_effect = requests.exceptions.Timeout

        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')
        provider.add('test', 'password')
        provider.start('test')

        # when
        provider.stop('test')

        # then
        client.stop.assert_called_once_with(container, timeout=10)
        client.kill.assert_called_once_with(container)

    @patch('provider.docker.docker.Client')
    def test_status_stopped(self, docker_mock):
        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')
        provider.add('test', 'password')

        self.assertEqual({'state': 'stopped'}, provider.status('test'))

    @patch('provider.docker.docker.Client')
    def test_status_running(self, docker_mock):
        client = docker_mock.return_value
        container = {u'Status': u'Up 20 seconds', u'Created': 1404904929, u'Image': u'mailpile:latest', u'Ports': [{u'IP': u'0.0.0.0', u'Type': u'tcp', u'PublicPort': 5000, u'PrivatePort': 33144}], u'Command': u'sleep 100', u'Names': [u'/test'], u'Id': u'f59ee32d2022b1ab17eef608d2cd617b7c086492164b8c411f1cbcf9bfef0d87'}
        client.containers.side_effect = [[], [], [container], [container]]
        client.wait.return_value = 0
        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')
        provider.add('test', 'password')
        provider.start('test')

        self.assertEqual({'state': 'running', 'port': 5000}, provider.status('test'))

    def test_empty_list(self):
        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')
        self.assertEqual([], provider.list())

    def test_list(self):
        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')
        provider.add('test', 'password')
        self.assertEqual(['test'], provider.list())

    @patch('provider.docker.Process')
    @patch('provider.docker.docker.Client')
    def test_memory_usage(self, docker_mock, process_mock):
        # given
        container = {u'Status': u'Up 20 seconds', u'Created': 1404904929, u'Image': u'mailpile:latest', u'Ports': [{u'IP': u'0.0.0.0', u'Type': u'tcp', u'PublicPort': 5000, u'PrivatePort': 33144}], u'Command': u'sleep 100', u'Names': [u'/test'], u'Id': u'f59ee32d2022b1ab17eef608d2cd617b7c086492164b8c411f1cbcf9bfef0d87'}
        info = {u'HostsPath': u'/var/lib/docker/containers/f2cdb04277e9e056c610240edffe8ff94ae272e462312c270e5300975d60af89/hosts', u'Created': u'2014-07-14T13:17:46.17558664Z', u'Image': u'f63df19194389be6481a174b36d291c483c8982d5c07485baa71a46b7f6582c8', u'Args': [u'--www'], u'Driver': u'aufs', u'HostConfig': {u'PortBindings': {u'33411/tcp': [{u'HostPort': u'5000', u'HostIp': u'0.0.0.0'}]}, u'NetworkMode': u'', u'Links': None, u'LxcConf': None, u'ContainerIDFile': u'', u'Binds': [u'/tmp/multipile/folker:/mnt/user:rw'], u'PublishAllPorts': False, u'Dns': None, u'DnsSearch': None, u'Privileged': False, u'VolumesFrom': None}, u'MountLabel': u'', u'VolumesRW': {u'/mnt/user': True}, u'State': {u'Pid': 3250, u'Paused': False, u'Running': True, u'FinishedAt': u'0001-01-01T00:00:00Z', u'StartedAt': u'2014-07-14T13:17:46.601922899Z', u'ExitCode': 0}, u'ExecDriver': u'native-0.2', u'ResolvConfPath': u'/etc/resolv.conf', u'Volumes': {u'/mnt/user': u'/tmp/multipile/folker'}, u'Path': u'/Mailpile.git/mp', u'HostnamePath': u'/var/lib/docker/containers/f2cdb04277e9e056c610240edffe8ff94ae272e462312c270e5300975d60af89/hostname', u'ProcessLabel': u'', u'Config': {u'MemorySwap': 0, u'Hostname': u'f2cdb04277e9', u'Entrypoint': None, u'PortSpecs': None, u'Memory': 0, u'OnBuild': None, u'OpenStdin': False, u'Cpuset': u'', u'Env': [u'MAILPILE_HOME=/mnt/user', u'HOME=/', u'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'], u'User': u'', u'CpuShares': 0, u'AttachStdout': True, u'NetworkDisabled': False, u'WorkingDir': u'', u'Cmd': [u'/Mailpile.git/mp', u'--www'], u'StdinOnce': False, u'AttachStdin': False, u'Volumes': {u'/mnt/user': {}}, u'Tty': False, u'AttachStderr': True, u'Domainname': u'', u'Image': u'mailpile', u'ExposedPorts': {u'33411/tcp': {}}}, u'Id': u'f2cdb04277e9e056c610240edffe8ff94ae272e462312c270e5300975d60af89', u'NetworkSettings': {u'Bridge': u'docker0', u'PortMapping': None, u'Gateway': u'172.17.42.1', u'IPPrefixLen': 16, u'IPAddress': u'172.17.0.14', u'Ports': {u'33411/tcp': [{u'HostPort': u'5000', u'HostIp': u'0.0.0.0'}]}}, u'Name': u'/folker'}
        client = docker_mock.return_value
        client.containers.return_value = [container]
        client.inspect_container.return_value = info

        psutil_mock = process_mock.return_value
        psutil_mock.memory_info.return_value = pmem(1024, 2048)

        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')
        provider.add('test', 'password')

        # when
        usage = provider.memory_usage()

        # then
        self.assertEqual({'total_usage': 1024,
                          'average_usage': 1024,
                          'agents': [
                              {'name': 'test', 'memory_usage': 1024}
                          ]}, usage)

    def test_that_existing_agents_are_autodiscovered(self):
        agent = os.path.join(self.root_path, 'test')
        os.mkdir(agent)

        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')

        self.assertEqual(['test'], provider.list())

    def test_authenticate(self):
        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')
        provider.add('test', 'password')

        self.assertTrue(provider.authenticate('test', 'password'))
        self.assertFalse(provider.authenticate('test', 'something else'))

    def test_remove_error_if_not_exist(self):
        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')

        self.assertRaises(ValueError, provider.remove, 'does_not_exist')

    @patch('provider.docker.docker.Client')
    def test_remove(self, docker_mock):
        # given
        client = docker_mock.return_value
        client.containers.return_value = []
        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')
        provider.add('test', 'password')

        # when
        provider.remove('test')

        # then
        self.assertFalse(exists(join(self.root_path, 'test')))
        self.assertFalse('test' in provider.list())

    @patch('provider.docker.docker.Client')
    def test_cannot_remove_while_running(self, docker_mock):
        # given
        client = docker_mock.return_value
        container = {u'Status': u'Up 20 seconds', u'Created': 1404904929, u'Image': u'mailpile:latest', u'Ports': [{u'IP': u'0.0.0.0', u'Type': u'tcp', u'PublicPort': 5000, u'PrivatePort': 33411}], u'Command': u'sleep 100', u'Names': [u'/test'], u'Id': u'f59ee32d2022b1ab17eef608d2cd617b7c086492164b8c411f1cbcf9bfef0d87'}
        client.containers.side_effect = [[], [], [container]]
        client.wait.return_value = 0

        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')
        provider.add('test', 'password')
        provider.start('test')

        # when/then
        self.assertRaises(ValueError, provider.remove, 'test')

    @patch('provider.docker.TempDir')
    @patch('provider.docker.pkg_resources')
    @patch('provider.docker.docker.Client')
    def test_use_build_script_instead_of_docker_file_if_available(self, docker_mock, res_mock, tempDir_mock):
        # given
        provider = DockerProvider(self.root_path, self._adapter, 'some docker url')

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
                res_mock.resource_exists.assert_called_with('resources', 'init-mailpile-docker-context.sh')
                res_mock.resource_string.assert_called_with('resources', 'init-mailpile-docker-context.sh')
                with open(file.name, "r") as input:
                    data = input.read().replace('\n', '')
                    self.assertEqual('%s %s' % (file.name, os.path.realpath(tempBuildDir_name)), data)

                docker_mock.return_value.build.assert_called_once_with(path=tempBuildDir_name, tag='mailpile:latest', fileobj=None)
        finally:
            tempBuildDir.dissolve()