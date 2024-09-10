import unittest
from datetime import timedelta
from omotes_sdk.internal.common.broker_interface import QueueMessageTTLArguments


class TestQueueMessageTTLArguments(unittest.TestCase):
    def test__to_argument__no_arguments(self) -> None:
        # Arrange / Act
        args = QueueMessageTTLArguments()

        # Assert
        self.assertEqual(args.to_argument(), {})

    def test__to_argument__queue_ttl(self) -> None:
        # Arrange
        q_ttl = timedelta(seconds=60)

        # Act
        args = QueueMessageTTLArguments(queue_ttl=q_ttl)

        # Assert
        self.assertEqual(args.to_argument(), {"x-expires": 60000})

    def test__to_argument__negative_queue_ttl(self) -> None:
        # Arrange
        q_ttl = timedelta(seconds=-60)

        # Act / Assert
        with self.assertRaises(ValueError):
            QueueMessageTTLArguments(queue_ttl=q_ttl).to_argument()

    def test__to_argument__zero_queue_ttl(self) -> None:
        # Arrange
        q_ttl = timedelta(seconds=0)

        # Act / Assert
        with self.assertRaises(ValueError):
            QueueMessageTTLArguments(queue_ttl=q_ttl).to_argument()

    def test__to_argument__message_ttl(self) -> None:
        # Arrange
        msg_ttl = timedelta(seconds=30)

        # Act
        args = QueueMessageTTLArguments(message_ttl=msg_ttl)

        # Assert
        self.assertEqual(args.to_argument(), {"x-message-ttl": 30000})

    def test__to_argument__negative_message_ttl(self) -> None:
        # Arrange
        msg_ttl = timedelta(seconds=-30)

        # Act / Assert
        with self.assertRaises(ValueError):
            QueueMessageTTLArguments(message_ttl=msg_ttl).to_argument()

    def test__to_argument__message_ttl_larger_than_queue_ttl(self) -> None:
        # Arrange
        q_ttl = timedelta(seconds=30)
        msg_ttl = timedelta(seconds=60)

        # Act / Assert
        with self.assertRaises(ValueError):
            QueueMessageTTLArguments(
                queue_ttl=q_ttl,
                message_ttl=msg_ttl
            ).to_argument()

    def test__to_argument__dead_letter_routing_key(self) -> None:
        # Arrange
        dl_routing_key = "test-dlq"

        # Act
        args = QueueMessageTTLArguments(dead_letter_routing_key=dl_routing_key)

        # Assert
        self.assertEqual(args.to_argument(), {"x-dead-letter-routing-key": "test-dlq"})

    def test__to_argument__dead_letter_exchange(self) -> None:
        # Arrange
        dl_exchange = "test-exchange"

        # Act
        args = QueueMessageTTLArguments(dead_letter_exchange=dl_exchange)

        # Assert
        self.assertEqual(args.to_argument(), {"x-dead-letter-exchange": "test-exchange"})

    def test__to_argument__all_arguments(self) -> None:
        # Arrange
        q_ttl = timedelta(minutes=2)
        msg_ttl = timedelta(minutes=1)
        dl_routing_key = "test-dlq"
        dl_exchange = "test-exchange"

        # Act
        args = QueueMessageTTLArguments(
            queue_ttl=q_ttl,
            message_ttl=msg_ttl,
            dead_letter_routing_key=dl_routing_key,
            dead_letter_exchange=dl_exchange
        )

        # Assert
        self.assertEqual(args.to_argument(), {
            "x-expires": 120000,
            "x-message-ttl": 60000,
            "x-dead-letter-routing-key": "test-dlq",
            "x-dead-letter-exchange": "test-exchange"
        })
