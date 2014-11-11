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
import subprocess
import sys
import logging

from pixelated.client.cli import Cli
from pixelated.client.dispatcher_api_client import PixelatedDispatcherClient
from pixelated.dispatcher import DispatcherProxy
from pixelated.manager import SSLConfig, PixelatedDispatcherManager
from pixelated.common import init_logging, latest_available_ssl_version

__author__ = 'fbernitt'

import argparse


def is_proxy():
    for arg in sys.argv:
        if arg == 'proxy':
            return True
    return False


def is_manager():
    for arg in sys.argv:
        if arg == 'manager':
            return True
    return False


def filter_args():
    return [arg for arg in sys.argv[1:] if arg not in ['manager', 'proxy']]


def is_cli():
    return not (is_manager() or is_proxy())


def prepare_venv(root_path):
    venv_path = os.path.join(root_path, 'virtualenv')
    script = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'create_mailpile_venv.sh')
    subprocess.call([script, venv_path])
    mailpile_path = os.path.join(venv_path, 'bin', 'mailpile')
    return venv_path, mailpile_path


def run_manager():
    parser = argparse.ArgumentParser(description='Multipile', )
    parser.add_argument('-r', '--root_path', help='The rootpath for mailpile')
    parser.add_argument('-m', '--mailpile_bin', help='The mailpile executable', default='mailpile')
    parser.add_argument('-b', '--backend', help='the backend to use (fork|docker)', default='fork')
    parser.add_argument('--bind', help="bind to interface. Default 127.0.0.1", default='127.0.0.1')
    parser.add_argument('--sslcert', help='The SSL certficate to use', default=None)
    parser.add_argument('--sslkey', help='The SSL key to use', default=None)
    parser.add_argument('--debug', help='Set log level to debug', default=False, action='store_true')
    parser.add_argument('--log-config', help='Provide a python logging config file', default=None)
    parser.add_argument('--provider', help='Specify the provider this dispatcher will connect to')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--mailpile-virtualenv', help='Use specified virtual env for mailpile', default=None)
    group.add_argument('--auto-mailpile-virtualenv', dest='auto_venv', help='Boostrap virtualenv for mailpile', default=False, action='store_true')

    args = parser.parse_args(args=filter_args())

    if args.sslcert:
        ssl_config = SSLConfig(args.sslcert,
                               args.sslkey,
                               latest_available_ssl_version())
    else:
        ssl_config = None

    venv = args.mailpile_virtualenv
    mailpile_bin = args.mailpile_bin

    if args.auto_venv:
        venv, mailpile_bin = prepare_venv(args.root_path)

    if args.root_path is None or not os.path.isdir(args.root_path):
        raise ValueError('root path %s not found!' % args.root_path)

    log_level = logging.DEBUG if args.debug else logging.INFO
    log_config = args.log_config
    init_logging('manager', level=log_level, config_file=log_config)

    manager = PixelatedDispatcherManager(args.root_path, mailpile_bin, ssl_config, args.provider, mailpile_virtualenv=venv, provider=args.backend, bindaddr=args.bind)

    manager.serve_forever()


def run_proxy():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', help='The port the dispatcher runs on')
    parser.add_argument('-m', '--manager', help="hostname:port of the manager")
    parser.add_argument('--bind', help="bind to interface. Default 127.0.0.1", default='127.0.0.1')
    parser.add_argument('--sslcert', help='The SSL certficate to use', default=None)
    parser.add_argument('--sslkey', help='The SSL key to use', default=None)
    parser.add_argument('--fingerprint', help='Pin certifcate to fingerprint', default=None)
    parser.add_argument('--disable-verifyhostname', help='Disable hostname verification. If fingerprint is specified it gets precedence', dest="verify_hostname", action='store_false', default=None)
    parser.add_argument('--debug', help='Set log level to debug', default=False, action='store_true')
    parser.add_argument('--log-config', help='Provide a python logging config file', default=None)

    args = parser.parse_args(args=filter_args())

    manager_hostname, manager_port = args.manager.split(':')
    certfile = args.sslcert if args.sslcert else None
    keyfile = args.sslkey if args.sslcert else None

    log_level = logging.DEBUG if args.debug else logging.INFO
    log_config = args.log_config
    init_logging('dipatcher', level=log_level, config_file=log_config)
    client = PixelatedDispatcherClient(manager_hostname, manager_port, cacert=certfile, fingerprint=args.fingerprint, assert_hostname=args.verify_hostname)
    client.validate_connection()

    dispatcher = DispatcherProxy(client, bindaddr=args.bind, keyfile=keyfile,
                                 certfile=certfile)
    dispatcher.serve_forever()


def run_cli():
    Cli(args=filter_args()).run()


def main():
    if is_manager():
        run_manager()
    elif is_proxy():
        run_proxy()
    else:
        run_cli()


if __name__ == '__main__':
    main()
