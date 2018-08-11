from sdncore.vty.session import Session


class Profile:
    """Represents a profile providing generic access credentials in form of a dictionary"""
    def __init__(self):
        self.pack = {}


class CliProfile(Profile):
    """Represents a set of credentials to access a device through CLI/VTY"""
    def __init__(self, proto, username, password, port=None, stop_character="#", driver_parameters={}):
        """Creates the Profile

        :param proto: Protocol to use, either SSH or Telnet
        :type proto: str
        :param username: Username to use for logging in
        :type username: str
        :param password: Password to use for logging in
        :type password: str
        :param port: Port to make the session on, if None (default) will use the default port for the protocol
        :type port: Union[int, None]
        :param stop_character: Character that identifies a command was received correctly and processed
        :type stop_character: str
        :param driver_parameters: Driver-specific parameters
        :type driver_parameters: dict"""
        super(Profile).__init__()
        proto = proto.lower()
        if proto == 'ssh':
            proto = Session.SSH
            if port is None:
                port = 22
        elif proto == 'telnet':
            proto = Session.Telnet
            if port is None:
                port = 23
        else:
            raise Exception
        self.pack = {
            'driver': proto,
            'username': username,
            'password': password,
            'port': port,
            'stop_character': stop_character,
            'driver_parameters': driver_parameters
        }
