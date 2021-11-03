from channels.testing import WebsocketCommunicator
from django.test import TestCase

from notification.consumers import NotificationConsumer


class MyTests(TestCase):
    async def test_my_consumer(self):
        communicator = WebsocketCommunicator(NotificationConsumer, "/ws/notif/12/")
        connected, subprotocol = await communicator.connect()
        assert connected
        # Test sending text
        await communicator.send_to(text_data="hello")
        response = await communicator.receive_from()
        assert response == "hello"
        # Close
        await communicator.disconnect()
