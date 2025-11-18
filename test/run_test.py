#!/usr/bin/env python3
"""Test runner that uses setup config."""
import sys
import os
import shutil

# Copy config to /etc/arm/config if it doesn't exist
config_dir = '/etc/arm/config'
config_file = os.path.join(config_dir, 'arm.yaml')
setup_file = '/home/betan/repo/automatic-ripping-machine/setup/arm.yaml'

if not os.path.exists(config_file):
    print(f"Config not found at {config_file}")
    print("Please run: sudo mkdir -p /etc/arm/config && sudo cp setup/arm.yaml /etc/arm/config/")
    print("\nOR set up a mock config by modifying arm/config/config.py to handle missing config")
    sys.exit(1)

# Now run the test
sys.path.insert(0, '/opt/arm')
sys.path.insert(0, '/home/betan/repo/automatic-ripping-machine')

# Import after path is set
import unittest

loader = unittest.TestLoader()
suite = loader.discover('/home/betan/repo/automatic-ripping-machine/test/unittest', pattern='test_disc_label_tv.py')
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
