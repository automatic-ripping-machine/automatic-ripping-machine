import pyudev

class Disc(object):
    """A disc class


    Attributes:
        path
        videotitle
        videoyear
        videotype
        hasnicetitle
        label
        disctype
    """

    def __init__(self, devpath):
        """Return a disc object"""
        self.devpath = devpath
        self.mountpoint = "/mnt" + devpath
        self.mkvoutpath = None
        self.basepath = None
        self.videotitle = None
        self.videoyear = None
        self.videotype = None
        self.hasnicetitle = False
        self.label = None
        self.disctype = None
        self.parse_udev()

    def parse_udev(self):
        """Parse udev for properties of current disc"""

        # isbluray, isdvd, ismusic = False, False, False
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

        # if isbluray:
        #     self.disctype = "bluray"
        # elif isdvd:
        #     self.disctype = "dvd"
        # elif ismusic:
        #     self.disctype = "music"

    def __str__(self):
        """Returns a string of the object"""

        s = self.__class__.__name__ + ": "
        for attr, value in self.__dict__.items():
            s = s + "(" + str(attr) + "=" +  str(value) + ") "

        return s



