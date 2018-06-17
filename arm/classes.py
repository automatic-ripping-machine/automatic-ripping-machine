import pyudev
import os


class Disc(object):
    """A disc class


    Attributes:
        devpath
        mountpoint
        videotitle
        videoyear
        videotype
        hasnicetitle
        label
        disctype
        ejected
        errors
    """

    def __init__(self, devpath):
        """Return a disc object"""
        self.devpath = devpath
        self.mountpoint = "/mnt" + devpath
        self.videotitle = ""
        self.videoyear = ""
        self.videotype = ""
        self.hasnicetitle = False
        self.label = ""
        self.disctype = ""
        self.ejected = False
        self.errors = []

        self.parse_udev()

    def parse_udev(self):
        """Parse udev for properties of current disc"""

        # print("Entering disc")
        context = pyudev.Context()
        device = pyudev.Devices.from_device_file(context, self.devpath)
        self.disctype = "unknown"
        for key, value in device.items():
            if key == "ID_FS_LABEL":
                self.label = value
                if value == "iso9660":
                    self.disctype = "data"
            elif key == "ID_CDROM_MEDIA_BD":
                self.disctype = "bluray"
            elif key == "ID_CDROM_MEDIA_DVD":
                self.disctype = "dvd"
            elif key == "ID_CDROM_MEDIA_TRACK_COUNT_AUDIO":
                self.disctype = "music"
            else:
                pass

    def __str__(self):
        """Returns a string of the object"""

        s = self.__class__.__name__ + ": "
        for attr, value in self.__dict__.items():
            s = s + "(" + str(attr) + "=" + str(value) + ") "

        return s

    def eject(self):
        """Eject disc if it hasn't previously been ejected"""

        # print("Value is " + str(self.ejected))
        if not self.ejected:
            os.system("eject " + self.devpath)
            self.ejected = True
