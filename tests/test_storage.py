import time
import unittest

from obd_influx.storage import InfluxPacketBuilder, InfluxDBRecorder


class TestInfluxPacketBuilder(unittest.TestCase):
    """Unittests for influx measurement creation interface."""

    def test_add_tags_errors(self):
        """Check that add_tags() raises appropriate errors."""
        serializer = InfluxPacketBuilder()
        serializer.start_packet('m1')

        with self.assertRaisesRegex(
                TypeError, "different numbers of tags and values"):
            serializer.add_tags('t1', ["value1", "value2"])

        with self.assertRaisesRegex(
                TypeError, "different numbers of tags and values"):
            serializer.add_tags(['t1', 't2'], "value1")

        with self.assertRaisesRegex(
                TypeError, "different numbers of tags and values"):
            serializer.add_tags(['t1', 't2', 't3'], ["value1", "value3"])

    def test_command_order_errors(self):
        """Check that serializer warns if commands called in bad order."""
        serializer = InfluxPacketBuilder()
        with self.assertRaisesRegex(
                RuntimeError, "start_packet()"):
            serializer.to_json()

        serializer.start_packet('m1')
        with self.assertRaisesRegex(
                RuntimeError, "add_timestamp()"):
            serializer.to_json()

        serializer.add_timestamp()
        with self.assertRaisesRegex(
                RuntimeError, "add_fields()"):
            serializer.to_json()

        serializer.add_fields('f1', "value1")
        result = serializer.to_json()
        # TODO (connor): check result

    def test_add_timestamp(self):
        """Verify behavior of add_timestamp() method."""
        # No timestamp on initialization
        serializer = InfluxPacketBuilder()
        self.assertEqual(serializer.timestamp, None)

        # No timestamp on start_packet
        serializer.start_packet('m1')
        self.assertEqual(serializer.timestamp, None)

        # Auto-timestamp with time.time
        t = time.time()
        serializer.add_timestamp()
        self.assertAlmostEqual(serializer.timestamp / 1e9, t, places=3)

        # Provided timestamp overrides auto-timestamp
        self.assertFalse(t == time.time())
        serializer.add_timestamp(t)
        self.assertEqual(serializer.timestamp / 1e9, t)

        # New packet clears timestamp
        serializer.start_packet('m2')
        self.assertEqual(serializer.timestamp, None)


if __name__ == '__main__':
    unittest.main()
