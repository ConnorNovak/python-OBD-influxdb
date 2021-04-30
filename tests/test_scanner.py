import time
import unittest

import obd
from obd_influx.scanner import Scanner, OBD_MAX_FREQUENCY
from obd_influx.storage import _RECORDERS, AbstractRecorder


STORAGE_VAR: str = ""

class UnittestRecorder(AbstractRecorder):
    """Recorder used to unittest Scanner without InfluxDB."""

    def record(self, data: str) -> None:
        STORAGE_VAR = data

    def close(self) -> None:
        STORAGE_VAR = ""

_RECORDERS['unittest'] = UnittestRecorder


class TestScanner(unittest.TestCase):
    """Unittests for OBD port scanner."""

    def test_frequency(self):
        """Verify frequency getting/setting works."""
        obd.logger.setLevel(50)  # Throttle bad connection warnings
        # Test default frequency
        scanner = Scanner(
            portstr='/dev/ttyUSB0',
            baudrate=11250,
            commands=[obd.commands.SPEED],
            recorder_config={'name': 'unittest'},
            frequency=None)
        self.assertTrue(scanner.frequency, OBD_MAX_FREQUENCY)

        # Test custom frequency after init
        scanner.frequency = 21.55
        self.assertTrue(scanner.frequency, 21.55)

        # Test zero frequency
        with self.assertRaises(ValueError):
            scanner.frequency = 0.0

        self.assertTrue(scanner.frequency, 21.55)

        # Test negative frequency
        with self.assertRaises(ValueError):
            scanner.frequency = -10.0

        self.assertTrue(scanner.frequency, 21.55)


if __name__ == '__main__':
    unittest.main()
