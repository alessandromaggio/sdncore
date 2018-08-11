from .accessprofiles import Profile
from sdncore.vty.session import Session


class Device:
    """Represents a device that can be controlled with SDNCore"""
    def __init__(self, host, access_profile=Profile(), name=None):
        """Creates the entity representing the device

        :param host: Target IP or hostname the host will be reachable on
        :type host: str
        :param access_profile: Profile defining credential set
        :type access_profile: Profile
        :param name: Explicative name representing this device
        :type name: str"""
        self.manage_host = host
        self.access_profile = access_profile
        self.name = name
        self.cli = Session(self.manage_host, **self.access_profile.pack)
