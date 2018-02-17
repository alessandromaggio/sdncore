from paramiko import client
from paramiko.ssh_exception import AuthenticationException
import threading
import time
import re
from .driver import Driver, DriverError


class SSHDriver(Driver):
    """Represents a connection with SSH"""
    def __init__(self, target, username='', password='', port=22, auto_add_keys=True):
        """Instantiates the connection, but does not open it

        :param str target: Target host
        :param str username: Username to use if authentication is available
        :param str password: Password to use if authentication is available
        :param int port: Port on which connection should be attempted
        :param bool auto_add_keys: If true, automatically populate the known_hosts with discovered keys"""
        self.target = target
        self.username = username
        self.password = password
        self.port = port
        self._client = client.SSHClient()
        if auto_add_keys:
            self._client.set_missing_host_key_policy(client.AutoAddPolicy())
        self._streams = {
            'in': None,
            'out': None,
            'err': None
        }

    def open(self):
        try:
            self._client.connect(self.target,
                                 port=self.port,
                                 username=self.username,
                                 password=self.password,
                                 look_for_keys=False)
        except AuthenticationException:
            raise DriverError("Authentication failed")
        except client.SSHException:
            raise DriverError("Keys error when attempting connection to " + self.target)

    def send_text(self, text):
        try:
            self._streams['in'], self._streams['out'], self._streams['err'] = self._client.exec_command(text)
        except AttributeError:
            raise DriverError('Attempting to use a session that was not opened')

    @staticmethod
    def _set_timeout(event, duration):
        """Triggers an event after the given duration

        :param threading.Event event: The event to be set
        :param int duration: seconds after which to trigger the event"""
        time.sleep(duration)
        event.set()

    def read_eof(self, timeout=2):
        data = b''
        signal_timeout = threading.Event()
        t1 = threading.Thread(
            target=self._set_timeout,
            args=(signal_timeout, timeout,)
        )
        t1.start()
        while not signal_timeout.is_set() and not self._streams['out'].channel.exit_status_ready():
            while not signal_timeout.is_set() and self._streams['out'].channel.recv_ready():
                data += self._streams['out'].channel.recv(1024)
        return data

    def read_until(self, text, timeout=2):
        data = b''
        signal_timeout = threading.Event()
        t1 = threading.Thread(
            target=self._set_timeout,
            args=(signal_timeout, timeout,)
        )
        t1.start()
        while not signal_timeout.is_set() and not self._streams['out'].channel.exit_status_ready():
            while not signal_timeout.is_set() and self._streams['out'].channel.recv_ready():
                data += self._streams['out'].channel.recv(1024)
                pos = data.find(bytes(text, 'utf8'))
                if pos > -1:
                    return data[:pos+len(text)]
        return data

    def expect(self, expr_list, timeout=2):
        if timeout is not None:
            data = b''
            signal_timeout = threading.Event()
            t1 = threading.Thread(
                target=self._set_timeout,
                args=(signal_timeout, timeout,)
            )
            t1.start()
        if isinstance(expr_list[0], type(re.compile(''))):
            expressions = expr_list
        else:
            expressions = []
            for expr in expr_list:
                expressions.append(re.compile(expr))
        while not signal_timeout.is_set() and not self._streams['out'].channel.exit_status_ready():
            while not signal_timeout.is_set() and self._streams['out'].channel.recv_ready():
                data += self._streams['out'].channel.recv(1)
                for i, expr in enumerate(expressions):
                    result = expr.match(str(data, 'utf8'))
                    if result is not None:
                        return i, result, data
        return -1, None, data

    def close(self):
        self._client.close()
