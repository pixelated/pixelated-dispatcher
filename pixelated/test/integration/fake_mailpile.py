#!/usr/bin/env python2
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
