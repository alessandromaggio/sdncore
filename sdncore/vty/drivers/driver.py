"""Defines the skeleton for a driver to connect to a device in VTY"""


class Driver:
    """Abstract class all drivers must inherit from"""
    def __init__(self, target, port, username, password):
        """Creates an object ready for the connection

        :param str target: IP or name of the target device
        :param int port: Port to execute the connection on
        :param str username: Username to use with authentication, if available
        :param str password: Password to use with authentication, if available
        """
        raise NotImplementedError()

    def open(self):
        """Opens the connection to the target device"""
        raise NotImplementedError()

    def send_text(self, text):
        """Send text in terminal emulation to the target device

        :param str text: Text to send to the target device
        :return: True on success
        """
        raise NotImplementedError()

    def read_until(self, text, timeout):
        """Read text coming from the remote device until the given text is found

        :param str text: Text that will interrupt
        :param int timeout: Seconds after which stop reading even if text was not found
        :return: Text that was read
        :rtype: str
        """
        raise NotImplementedError()

    def read_eof(self):
        """Read text until End of File

        :return: Text that was read
        :rtype: str
        """
        raise NotImplementedError()

    def expect(self, expr_list, timeout):
        """Wait until a given text is received or the timeout

        :param list expr_list: List of texts that will count as match
        :param int timeout: Time after which stop the execution even if expected test was not seen, in seconds
        :return: Text that was read
        :rtype: str
        """
        raise NotImplementedError

    def close(self):
        """Terminates the connection"""
        raise NotImplementedError()


class DriverError(Exception):
    """Collects and standardizes errors coming from

    All errors that may raise during the execution of a driver should be converted into DriverError"""
    pass
