from telnetlib import Telnet as TelnetClient
from .driver import Driver, DriverError
import socket


class TelnetDriver(Driver):
    """Represents a connection with Telnet"""
    def __init__(self, target, username='', password='', port=23,
                 username_finder='username: ', password_finder='password: '):
        """Instantiates the connection, but does not open it

        :param str target: Target host
        :param str username: Username to use if authentication is available
        :param str password: Password to use if authentication is available
        :param int port: Port on which connection should be attempted
        :param str username_finder: String to expect before sending the username
        :param str password_finder: String to expect before sending the password"""
        self.target = target
        self.username = username
        self.password = password
        self.port = port
        self.username_finder = username_finder
        self.password_finder = password_finder
        self._client = TelnetClient()

    def open(self):
        self._client.open(self.target, self.port)
        if self.username != '' or self.password != '':
            self.expect(self.username_finder)
            self.send_text(self.username + '\n')
            self.expect(self.password_finder)
            self.send_text(self.password + '\n')

    def send_text(self, text):
        try:
            self._client.write(text.encode('utf8'))
            return True
        except socket.error as ex:
            raise DriverError("Connection closed while sending text") from ex

    def read_until(self, text, timeout=2):
        try:
            return self._client.read_until(text.encode('ascii'), timeout).decode('utf8')
        except EOFError as ex:
            raise DriverError("Connection closed without receiving EOF") from ex

    def read_eof(self, timeout=2):
        return self._client.read_all().encode('utf8')

    def expect(self, expr_list, timeout=2):
        try:
            if isinstance(expr_list, str):
                expr_list = [expr_list]
            for k, v in enumerate(expr_list):
                if isinstance(v, str):
                    expr_list[k] = bytes(v, 'utf8')
            return self._client.expect(expr_list, timeout)
        except EOFError as ex:
            raise DriverError("EOF was reached without finding the expected text") from ex

    def close(self):
        self._client.close()


