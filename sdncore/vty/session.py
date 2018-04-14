from .drivers import telnet, ssh


class Session:
    class Driver:
        """Abstract representation of a driver, may not be instantiated"""
        def __init__(self):
            ReferenceError('Session.Driver may not be instantiated')

    class SSH(Driver):
        """Abstract representation of an SSH driver, may not be instantiated"""
        def __init__(self):
            super().__init__()

    class Telnet(Driver):
        """Abstract representation of a Telnet driver, may not be instantiated"""
        def __init__(self):
            super().__init__()

    def __init__(self, target, port=None,
                 username='', password='', driver=SSH, driver_parameters={},
                 stop_character='#'):
        """Creates a VTY session to a remote device

        :param target: IP or hostname of the remote device
        :type target: str
        :param port: Port of the remote device to attempt the connection on
        :type port: Union[None, int]
        :param username: Username to authenticate with the remote device, leave blank if no username is required
        :type username: str
        :param password: Password to authenticate with the remote device, leave blank if no password is required
        :type password: str
        """
        self.target = target
        self.port = port
        self.username = username
        self.password = password
        self.stop_character = stop_character
        self.buffer = ''
        self.prompt = self.stop_character
        if driver == self.SSH:
            self.driver = ssh.SSHDriver
            if self.port is None:
                self.port = 22
        elif driver == self.Telnet:
            self.driver = telnet.TelnetDriver
            if self.port is None:
                self.port = 23
        self.hook = self.driver(
            target=self.target,
            port=self.port,
            username=self.username,
            password=self.password,
            **driver_parameters
        )

    def open(self):
        """Opens the connection to the remote device and detects the prompt"""
        self.hook.open()
        self.buffer = self.hook.read_until(self.stop_character)
        self.detect_prompt()

    def close(self):
        """Terminates the connection with the remote device"""
        self.hook.close()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def cleaned_buffer(self, remove_first=True):
        """Returns the buffer without the prompt string, and optionally without the first line

        :param remove_first: Flag to remove the first line
        :type remove_first: True
        :return: The cleaned buffer
        :rtype: str"""
        lines = self.buffer.split('\n')
        if remove_first and len(lines) > 0:
            lines.pop(0)
        last = lines.pop()
        if last != self.prompt:
            lines.append(last)
        return '\n'.join(lines)

    def command(self, command, timeout=None, custom_stopper=None, changes_prompt=False, show_command=False):
        """Executes a command, put the output in the buffer and returns it

        :param command: The command to execute, new line will be appended
        :type command: str
        :param timeout: Timeout to execute the command and store the output
        :type timeout: Union[None, int]
        :param custom_stopper: If not none, use a different stop string than the normal prompt
        :type custom_stopper: Union[None, str]
        :param changes_prompt: Flag to indicate that this command causes the prompt to change
        :type changes_prompt: bool
        :param show_command: Flag to indicate whether to show the command given in the returned output
        :type show_command: bool"""
        self.hook.send_text(command + '\n')
        if changes_prompt:
            self.detect_prompt()
            return
        stopper = self.prompt
        if custom_stopper is not None:
            stopper = custom_stopper
        pass_timeout = {}
        if timeout is not None:
            pass_timeout = {'timeout': timeout}
        self.buffer = self.hook.read_until(stopper, **pass_timeout)
        return self.cleaned_buffer(remove_first=not show_command)

    def detect_prompt(self):
        """Finds the full prompt the device is currently using

        :return: The prompt the device is using
        :rtype: str"""
        lines = self.buffer.split('\n')
        if len(lines) > 0:
            last_line = lines.pop()
            if len(last_line) > 0:
                self.prompt = last_line
        return self.prompt
