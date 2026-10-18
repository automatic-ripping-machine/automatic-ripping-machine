"""
Disc camera daemon.

Watches the optical drive trays and, each time a tray closes, saves a webcam frame taken just
before it retracted into DISC_PHOTO_PATH. The ripper attaches that photo to the job it starts
for the same drive (see ``arm.ripper.utils.attach_disc_photo``).

The modules in this package do not import anything else from ``arm`` on purpose: importing the
``arm`` package loads the Flask app and the database, which a long-running camera process has
no use for. ``daemon.py`` is run directly (``python3 /opt/arm/arm/camera/daemon.py``).
"""
