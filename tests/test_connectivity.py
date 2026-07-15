import unittest
from unittest.mock import patch

from upload_plugg.services.connectivity import GOOGLE_ENDPOINTS, internet_available


class ConnectivityTests(unittest.TestCase):
    def test_second_google_endpoint_can_confirm_connection(self):
        with patch(
            "upload_plugg.services.connectivity._https_reachable",
            side_effect=[False, True],
        ) as probe:
            self.assertTrue(internet_available())
        self.assertEqual(probe.call_count, 2)
        self.assertEqual(probe.call_args_list[0].args[0], GOOGLE_ENDPOINTS[0])

    def test_socket_fallback_can_confirm_connection(self):
        with (
            patch("upload_plugg.services.connectivity._https_reachable", return_value=False),
            patch("upload_plugg.services.connectivity.socket.create_connection") as connect,
        ):
            connect.return_value.__enter__.return_value = object()
            self.assertTrue(internet_available())


if __name__ == "__main__":
    unittest.main()
