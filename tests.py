from unittest import TestCase
from unittest.mock import patch, MagicMock

from websocket import Client, WebSocketServer, run


class MockSocket:
    def __init__(self, open):
        self.open = open


class TestWebSocket(TestCase):

    def test_cient(self):
        self.assertFalse(Client(None).is_active())
        self.assertFalse(Client(MockSocket(False)).is_active())
        self.assertTrue(Client(MockSocket(True)).is_active())
        client = Client(MockSocket(True))
        self.assertFalse(client.is_tag('tag1'))
        self.assertEqual(client.name, 'unknown')
        client.init_tags(['tag1', 'tag2'])
        self.assertTrue(client.is_tag('tag1'))
        self.assertEqual(client.name, 'tag1, tag2')

    def test_server(self):
        server = WebSocketServer()
        # test run
        with patch('asyncio.async') as mock,\
                patch('asyncio.base_events.BaseEventLoop.run_until_complete') as mock1,\
                patch('asyncio.base_events.BaseEventLoop.run_forever') as mock2:
            run(MagicMock, MagicMock, 'localhost', 999, 'localhost', 6379, 0, 'ws-channel')
            mock.assert_called_once()
            mock1.assert_called_once()
            mock2.assert_called_once()
        # test receiver
        client = Client(MockSocket(True))
        server.receiver(client, 'msg')
        self.assertEqual(client.name, 'unknown')
        server.receiver(client, '{"message": "msg", "tags": ["tag1", "tag2"]}')
        server.receiver(client, 'msg')
        self.assertEqual(client.name, 'tag1, tag2')
