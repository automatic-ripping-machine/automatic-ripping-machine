#!/usr/bin/env python3
"""Test runner that uses setup config."""
import sys
import os

# Copy config to /etc/arm/config if it doesn't exist
config_dir = '/etc/arm/config'
config_file = os.path.join(config_dir, 'arm.yaml')
setup_file = '/home/betan/repo/automatic-ripping-machine/setup/arm.yaml'


def ensure_config():
    """Ensure the expected config file exists before running tests."""
    if os.path.exists(config_file):
        return
    print(f"Config not found at {config_file}")
    print("Please run: sudo mkdir -p /etc/arm/config && sudo cp setup/arm.yaml /etc/arm/config/")
    print("\nOR set up a mock config by modifying arm/config/config.py to handle missing config")
    sys.exit(1)


def main():
    """Configure paths and execute the unit tests."""
    ensure_config()

    # Remove the local test/ directory (which shadows stdlib unittest)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir in sys.path:
        sys.path.remove(script_dir)

    sys.path.insert(0, '/opt/arm')
    sys.path.insert(0, '/home/betan/repo/automatic-ripping-machine')

    # Import after sys.path adjustments
    import unittest  # pylint: disable=import-error

    loader = unittest.TestLoader()
    suite = loader.discover('/home/betan/repo/automatic-ripping-machine/test/unittest',
                            pattern='test_disc_label_tv.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__':
    main()
