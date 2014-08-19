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
import getpass

from client.dispatcher_api_client import PixelatedDispatcherClient, PixelatedHTTPError
import server


__author__ = 'fbernitt'

import sys
import argparse


class Cli(object):
    __slots__ = ('_args', '_out')

    DEFAULT_SERVER_PORT = server.DEFAULT_PORT

    def __init__(self, args, out=sys.stdout):
        self._args = args
        self._out = out

    def _build_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--server', help='Provide server url (default: localhost:4449')
        parser.add_argument('-k', '--no-check-certificate', help='don\'t validate SSL/TLS certificates', dest='check_cert', action='store_false', default=True)
        parser.add_argument('--no-ssl', help='Force unsecured connection', dest='use_ssl', action='store_false', default=True)
        subparsers = parser.add_subparsers(help='Commands', dest='cmd')
        subparsers.add_parser('list', help='List known agents')
        subparsers.add_parser('running', help='List known agents')
        addparser = subparsers.add_parser('add', help='Add a agent')
        addparser.add_argument('name', help='name of new user')
        startparser = subparsers.add_parser('start', help='Start agent')
        startparser.add_argument('name', help='name of user')
        stopparser = subparsers.add_parser('stop', help='Stop agent')
        stopparser.add_argument('name', help='name of user')
        infoparser = subparsers.add_parser('info', help='Show agent info')
        infoparser.add_argument('name', help='name of user')
        subparsers.add_parser('memory_usage', help='show memory usage')
        return parser

    def run(self):
        parser = self._build_parser()

        try:
            args = parser.parse_args(self._args)
            if args.server:
                host, port = args.server.split(':')
            else:
                host, port = 'localhost', Cli.DEFAULT_SERVER_PORT

            cli = self._create_cli(host, port, args.check_cert, args.use_ssl)
            if 'list' == args.cmd:
                for agent in cli.list():
                    self._out.write('%s\n' % agent['name'])
            elif 'running' == args.cmd:
                for agent in cli.list():
                    if 'running' == agent['state']:
                        self._out.write('%s\n' % agent['name'])
            elif 'add' == args.cmd:
                name = args.name
                password = getpass.getpass('Enter password for new user', self._out)
                cli.add(name, password)
            elif 'start' == args.cmd:
                name = args.name
                cli.start(name)
            elif 'stop' == args.cmd:
                name = args.name
                cli.stop(name)
            elif 'info' == args.cmd:
                name = args.name
                info = cli.get_agent_runtime(name)
                self._out.write('port:\t%s\n' % info['port'])
            elif 'memory_usage' == args.cmd:
                usage = cli.memory_usage()
                self._out.write('memory usage:\t%d\n' % usage['total_usage'])
                self._out.write('average usage:\t%d\n\n' % usage['average_usage'])
                for agent in usage['agents']:
                    self._out.write('\t%s:\t%d\n' % (agent['name'], agent['memory_usage']))
        except PixelatedHTTPError, e:
            sys.stderr.write('%s\n' % str(e))
            sys.exit(1)

        except SystemExit:
            pass

    def _create_cli(self, host, port, cacert, ssl):
        return PixelatedDispatcherClient(host, port, cacert=cacert, ssl=ssl)