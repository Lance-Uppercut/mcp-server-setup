import importlib.util
import pathlib
import unittest


SERVER_PATH = pathlib.Path(__file__).resolve().parents[1] / "server.py"
spec = importlib.util.spec_from_file_location("asus_server", SERVER_PATH)
asus_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(asus_server)


class TestAsusMapping(unittest.TestCase):
    def test_pick_data_name_prefers_first_available(self):
        asus_server.ASUS_DATA_NAMES = {"CLIENTS", "WAN", "WLAN"}
        self.assertEqual(asus_server._pick_data_name("CLIENTS", "DEVICEMAP"), "CLIENTS")

    def test_pick_data_name_fallback(self):
        asus_server.ASUS_DATA_NAMES = {"DEVICEMAP", "WAN"}
        self.assertEqual(asus_server._pick_data_name("CLIENTS", "DEVICEMAP"), "DEVICEMAP")

    def test_pick_data_name_none_when_missing(self):
        asus_server.ASUS_DATA_NAMES = {"WAN"}
        self.assertIsNone(asus_server._pick_data_name("CLIENTS", "DEVICEMAP"))

    def test_wifi_client_detection(self):
        wifi_device = {"name": "Phone", "rssi": -60, "radio": "5G"}
        wired_device = {"name": "NAS", "connection": "ethernet"}
        self.assertTrue(asus_server._is_wifi_client(wifi_device))
        self.assertFalse(asus_server._is_wifi_client(wired_device))


if __name__ == "__main__":
    unittest.main()
