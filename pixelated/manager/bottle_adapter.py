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
import SocketServer
import socket
import ssl

from bottle import ServerAdapter


class SSLTCPServer(SocketServer.TCPServer):
    def __init__(self, server_address, request_handler_class, bind_and_activate=True, ssl_key_file=None,
                 ssl_cert_file=None, ssl_version=ssl.PROTOCOL_TLSv1, ca_certs=None, ssl_ciphers=None):
        """Constructor. May be extended, do not override."""
        SocketServer.TCPServer.__init__(self, server_address, request_handler_class, False)

        if ca_certs is not None:  # if we have a certificate authority we want to enforce it for all clients
            cert_reqs = ssl.CERT_REQUIRED
        else:
            cert_reqs = ssl.CERT_NONE

        self.socket = ssl.wrap_socket(self.socket, keyfile=ssl_key_file, certfile=ssl_cert_file, ciphers=ssl_ciphers,
                                      ssl_version=ssl_version, server_side=True, ca_certs=ca_certs, cert_reqs=cert_reqs)

        if bind_and_activate:
            self.server_bind()
            self.server_activate()


class SSLHTTPServer(SSLTCPServer):
    allow_reuse_address = 1  # Seems to make sense in testing environment

    def server_bind(self):
        """Override server_bind to store the server name."""
        SSLTCPServer.server_bind(self)
        host, port = self.socket.getsockname()[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port


class SSLWSGIServer(SSLHTTPServer):
    """BaseHTTPServer that implements the Python WSGI protocol"""

    application = None

    def server_bind(self):
        """Override server_bind to store the server name."""
        SSLHTTPServer.server_bind(self)
        self.setup_environ()

    def setup_environ(self):
        # Set up base environment
        env = self.base_environ = {}
        env['SERVER_NAME'] = self.server_name
        env['GATEWAY_INTERFACE'] = 'CGI/1.1'
        env['SERVER_PORT'] = str(self.server_port)
        env['REMOTE_HOST'] = ''
        env['CONTENT_LENGTH'] = ''
        env['SCRIPT_NAME'] = ''

    def get_app(self):
        return self.application

    def set_app(self, application):
        self.application = application


class SSLWSGIRefServerAdapter(ServerAdapter):
    __slots__ = '_server'

    _server = None

    def run(self, app):  # pragma: no cover
        from wsgiref.simple_server import WSGIRequestHandler
        import socket

        class FixedHandler(WSGIRequestHandler):
            def address_string(self):  # Prevent reverse DNS lookups please.
                return self.client_address[0]

            def log_request(*args, **kw):
                if not self.quiet:
                    return WSGIRequestHandler.log_request(*args, **kw)

        handler_cls = self.options.get('handler_class', FixedHandler)
        server_cls = self.options.get('server_class', SSLWSGIServer)
        ssl_keyfile = self.options.get('ssl_key_file')
        ssl_certfile = self.options.get('ssl_cert_file')
        ssl_version = self.options.get('ssl_version', ssl.PROTOCOL_TLSv1)
        ssl_ca_certs = self.options.get('ssl_ca_certs', None)
        ssl_ciphers = self.options.get('ssl_ciphers', None)

        if ':' in self.host:  # Fix wsgiref for IPv6 addresses.
            if getattr(server_cls, 'address_family') == socket.AF_INET:
                class server_cls(server_cls):
                    address_family = socket.AF_INET6

        srv = SSLWSGIServer((self.host, self.port), handler_cls, ssl_cert_file=ssl_certfile, ssl_key_file=ssl_keyfile,
                            ssl_version=ssl_version, ca_certs=ssl_ca_certs, ssl_ciphers=ssl_ciphers)

        self._server = srv
        srv.set_app(app)
        srv.serve_forever()

    def shutdown(self):
        if self._server:
            self._server.shutdown()
            self._server = None
