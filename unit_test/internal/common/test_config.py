import unittest

from omotes_sdk.internal.common.config import EnvRabbitMQConfig


class TestEnvRabbitMQConfig(unittest.TestCase):
    def test__init__no_errors(self) -> None:
        # Act / Assert
        EnvRabbitMQConfig()
