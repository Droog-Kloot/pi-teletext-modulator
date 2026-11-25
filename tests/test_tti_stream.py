"""Regression checks for packet generation; no Raspberry Pi required."""
import importlib.util
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "src" / "tti_stream.py"
spec = importlib.util.spec_from_file_location("tti_stream", SCRIPT)
tti = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tti)


class TestTTI(unittest.TestCase):
    def test_odd_parity(self):
        for value in range(128):
            self.assertEqual(tti.odd_parity(value).bit_count() % 2, 1)
            self.assertEqual(tti.odd_parity(value) & 0x7f, value)

    def test_control_codes(self):
        out = tti.decode_tti_line(b"A\x1bAB")
        self.assertEqual(out[:3], b"A\x01B")
        self.assertEqual(len(out), 40)

    def test_parse_and_packets(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "P100-0000.tti"
            path.write_bytes(b"PN,10000\nSC,0000\nOL,0,        TEST HEADER\nOL,1,HELLO\n")
            page = tti.parse_file(path)
            self.assertEqual(page[0], 0x100)
            packets = list(tti.make_packets(page))
            self.assertEqual(len(packets), 24)
            self.assertTrue(all(len(packet) == 42 for packet in packets))
            self.assertEqual(packets[0][:2], tti.packet_address(1, 0))
            self.assertEqual(packets[1][:2], tti.packet_address(1, 1))
            self.assertEqual(bytes(x & 0x7f for x in packets[1][2:7]), b"HELLO")
            self.assertTrue(all(b.bit_count() % 2 == 1 for p in packets[1:] for b in p[2:]))


if __name__ == "__main__":
    unittest.main()
