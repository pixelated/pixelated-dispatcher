#!/usr/bin/env python2
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

import argparse
import os
from ConfigParser import ConfigParser

from bottle import route, run


@route('/')
def index():
    return 'Hello World!'


def config_file():
    return os.path.join(os.environ['MAILPILE_HOME'], 'mailpile.cfg')


def write_config_value(args):
    parts = args.set.split('=')
    parser = read_config()
    parser.set('mailpile', parts[0], parts[1])
    with open(config_file(), 'w') as f:
        parser.write(f)


def read_config():
    parser = ConfigParser()
    if os.path.isfile(config_file()):
        parser.read(config_file())
    else:
        parser.add_section('mailpile')
        parser.set('mailpile', 'sys.http_port', 44321)
    return parser


def main():
    parser = argparse.ArgumentParser(description='Mailpile')
    parser.add_argument('--set', help='set some value')
    parser.add_argument('--setup', dest='setup', action='store_true')
    parser.add_argument('--www', dest='www', action='store_true')
    args = parser.parse_args()

    cfg = read_config()

    if args.www:
        run(host='localhost', port=cfg.getint('mailpile', 'sys.http_port'))

    if args.set:
        write_config_value(args)


if __name__ == '__main__':
    main()
