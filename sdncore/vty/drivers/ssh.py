from paramiko import client
from paramiko.ssh_exception import AuthenticationException
import threading
import queue
import time
import re
from .driver import Driver, DriverError
from .driver import set_timeout


class SSHDriver(Driver):
    """Represents a connection with SSH"""
    class SubDriver:
        """Represents a generic type of SSH actual driver"""
        def __init__(self, ssh_client, chunk_size):
            """Instantiates a driver over an established SSH session

            :param paramiko.client ssh_client: The client for the session
            :param int chunk_size: How many bytes to read in a single cycle of output"""
            raise NotImplementedError()

        def open(self, target, port, username, password, look_for_keys):
            """Opens the connection

            :param str target: Target host
            :param int port: Target TCP port
            :param str username: Username to use for authentication
            :param str password: Password to use for authentication
            :param bool look_for_keys: Whether to look for keys on the local host

            :returns: None

            :raises AuthenticationException: If authentication fails
            :raises paramiko.client.SSHException: If encounters error when validating the keys"""
            raise NotImplementedError()

        def send_text(self, text):
            """Executes a command on the remote device

            :param str text: Text to execute on the remote device
            :return: None"""
            raise NotImplementedError()

        def read_eof(self, timeout=2):
            """Reads text from the standard output until timeout expires

            :param int timeout: How long to wait before terminating execution, in seconds
            :return: Text as read from the stream
            :rtype: bytes"""
            raise NotImplementedError()

        def read_until(self, text, timeout=2):
            """Reads text from the standard output until some text is found or the timeout expires

            :param str text: Text that, if found, will interrupt the reading
            :param int timeout: How long to wait before terminating the execution if text is not found, in seconds
            :return: Text as read from the stream
            :rtype: bytes"""
            raise NotImplementedError()

        def expect(self, expr_list, timeout=2):
            """Wait until a given text is received or the timeout

            :param list expr_list: List of texts that will count as match
            :param int timeout: Time after which stop the execution even if expected test was not seen, in seconds
            :return: Text that was read
            :rtype: str"""
            raise NotImplementedError()

        def close(self):
            raise NotImplementedError()

    class ChannelSubDriver(SubDriver):
        def __init__(self, ssh_client, chunk_size):
            self.client = ssh_client
            self.chunk_size = chunk_size
            self.stream_in = None
            self.stream_out = None
            self.stream_err = None

        def open(self, target, port, username, password, look_for_keys):
            self.client.connect(
                target,
                port=port,
                username=username,
                password=password,
                look_for_keys=look_for_keys
            )

        def send_text(self, text):
            self.stream_in, self.stream_out, self.stream_err = self.client.exec_command(text)

        def read_eof(self, timeout=2):
            data = b''
            signal_timeout = threading.Event()
            t1 = threading.Thread(
                target=set_timeout,
                args=(signal_timeout, timeout,)
            )
            t1.start()
            while not signal_timeout.is_set() and not self.stream_out.channel.exit_status_ready():
                while not signal_timeout.is_set() and self.stream_out.channel.recv_ready():
                    data += self.stream_out.channel.recv(self.chunk_size)
            return data

        def read_until(self, text, timeout=2):
            data = b''
            signal_timeout = threading.Event()
            t1 = threading.Thread(
                target=set_timeout,
                args=(signal_timeout, timeout,)
            )
            t1.start()
            while not signal_timeout.is_set() and not self.stream_out.channel.exit_status_ready():
                while not signal_timeout.is_set() and self.stream_out.channel.recv_ready():
                    data += self.stream_out.channel.recv(1024)
                    pos = data.find(bytes(text, 'utf8'))
                    if pos > -1:
                        return data[:pos + len(text)]
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
            while not signal_timeout.is_set() and not self.stream_out.channel.exit_status_ready():
                while not signal_timeout.is_set() and self.stream_out.channel.recv_ready():
                    data += self.stream_out.channel.recv(1)
                    for i, expr in enumerate(expressions):
                        result = expr.match(str(data, 'utf8'))
                        if result is not None:
                            return i, result, data
            return -1, None, data

        def close(self):
            self._client.close()

    class ShellSubDriver(SubDriver):
        READ_DELAY = 0.1    # Time to wait before processing data read (stored) and not yet processed

        def __init__(self, ssh_client, chunk_size):
            self.client = ssh_client
            self.chunk_size = chunk_size
            self.shell = None
            self.stream_queue = queue.Queue()
            self.terminate_reading = threading.Event()
            self.reading_thread = None

        def _launch_reader(self):
            """Starts reading data from the device and putting them in a queue"""
            def reader(shell, store_queue, chunk_size, terminator_event, max_wait):
                """Continuously read data from the device as soon as they are available and put them in the queue

                Eventually terminates when the terminator event is set.

                :param paramiko.channel shell: Shell to fetch output from
                :param queue.Queue store_queue: Queue to store the output into
                :param int chunk_size: How much data to read with a single cycle
                :param threading.Event terminator_event: Event that will stop the execution
                :param int max_wait: What is the maximum wait time before a cycle and another, in seconds"""
                wait = 0
                while not terminator_event.is_set():
                    time.sleep(wait)
                    # Read only if there is something to read
                    if shell.recv_ready():
                        start = time.time()
                        store_queue.put(shell.recv(chunk_size))
                        # Calculate the wait to approximately fit the time the device needs to generate output
                        wait = time.time() - start
                    # If this cycle generated no output, we increase the waiting time
                    else:
                        wait += 0.01
                    # Waiting time should never exceed its maximum
                    if wait > max_wait:
                        wait = max_wait
            self.terminate_reading = threading.Event()
            self.reading_thread = threading.Thread(
                target=reader,
                args=(self.shell, self.stream_queue, self.chunk_size, self.terminate_reading, 2)
            )
            self.reading_thread.daemon = True
            self.reading_thread.start()

        def _get_ready_text(self):
            """Returns the the device returned and that was not read yet

            :return: Text ready but not yet processed
            :rtype: str"""
            ret = b''
            while not self.stream_queue.empty():
                ret += self.stream_queue.get()
            return str(ret, 'utf8')

        def open(self, target, port, username, password, look_for_keys):
            self.client.connect(
                target,
                port=port,
                username=username,
                password=password,
                look_for_keys=look_for_keys
            )
            self.shell = self.client.invoke_shell()
            self._launch_reader()

        def send_text(self, text):
            self.shell.send(text)

        def read_eof(self, timeout=2):
            data = ''
            signal_timeout = threading.Event()
            t1 = threading.Thread(
                target=set_timeout,
                args=(signal_timeout, timeout,)
            )
            t1.start()
            # While timeout has not expired and there is data to read
            while not signal_timeout.is_set():
                data += self._get_ready_text()
                time.sleep(self.READ_DELAY)

            return data

        def read_until(self, text, timeout=2):
            data = ''
            signal_timeout = threading.Event()
            t1 = threading.Thread(
                target=set_timeout,
                args=(signal_timeout, timeout,)
            )
            t1.start()
            # While timeout has not expired and there is data to read
            while not signal_timeout.is_set():
                got = self._get_ready_text()
                data += got
                pos = data.find(text)
                if pos > -1:
                    return data[:pos + len(text)]
                time.sleep(self.READ_DELAY)
            return data

        def expect(self, expr_list, timeout=2):
            data = ''
            signal_timeout = threading.Event()
            if isinstance(expr_list[0], type(re.compile(''))):
                expressions = expr_list
            else:
                expressions = []
                for expr in expr_list:
                    expressions.append(re.compile(expr))
            if timeout is not None:
                t1 = threading.Thread(
                    target=self._set_timeout,
                    args=(signal_timeout, timeout,)
                )
                t1.start()
            # While timeout has not expired and there is data to read
            while not signal_timeout.is_set():
                data += self._get_ready_text()
                for i, expr in enumerate(expressions):
                    result = expr.match(data)
                    if result is not None:
                        return i, result, data
                time.sleep(self.READ_DELAY)
            return -1, None, data

        def close(self):
            self.terminate_reading.set()
            self.client.close()

    def __init__(self, target, username='', password='', port=22, auto_add_keys=True, shell_mode=True,
                 look_for_keys=False, chunk_size=1024):
        """Instantiates the connection, but does not open it

        :param str target: Target host
        :param str username: Username to use if authentication is available
        :param str password: Password to use if authentication is available
        :param int port: Port on which connection should be attempted
        :param bool auto_add_keys: If true, automatically populate the known_hosts with discovered keys
        :param bool shell_mode: If true, use a single channel for all commands
        :param bool look_for_keys: Whether to look for keys in the known_hosts file
        :param int chunk_size: How many bytes read from the device in a single cycle"""
        self.target = target
        self.username = username
        self.password = password
        self.port = port
        self.shell_mode = shell_mode
        self.look_for_keys = look_for_keys
        self._client = client.SSHClient()
        if auto_add_keys:
            self._client.set_missing_host_key_policy(client.AutoAddPolicy())
        if shell_mode:
            sub_driver = self.ShellSubDriver
        else:
            sub_driver = self.ChannelSubDriver
        self._driver = sub_driver(self._client, chunk_size)

    def open(self):
        try:
            self._driver.open(self.target,
                              port=self.port,
                              username=self.username,
                              password=self.password,
                              look_for_keys=self.look_for_keys)
        except AuthenticationException as ex:
            raise DriverError("Authentication failed") from ex
        except client.SSHException as ex:
            raise DriverError("Keys error when attempting connection to " + self.target) from ex

    def send_text(self, text):
        try:
            self._driver.send_text(text)
            return True
        except AttributeError as ex:
            raise DriverError('Attempting to use a session that was not opened') from ex

    def read_eof(self, timeout=2):
        return self._driver.read_eof(timeout)

    def read_until(self, text, timeout=2):
        return self._driver.read_until(text, timeout)

    def expect(self, expr_list, timeout=2):
        return self._driver.expect(expr_list, timeout)

    def close(self):
        self._driver.close()
