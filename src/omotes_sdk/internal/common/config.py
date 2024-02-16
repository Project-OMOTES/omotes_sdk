import os
from omotes_sdk.config import RabbitMQConfig as RabbitMQConfig


class EnvRabbitMQConfig(RabbitMQConfig):
    """Retrieve RabbitMQ configuration from environment variables."""

    def __init__(self, prefix: str = ""):
        """Create the RabbitMQ configuration and retrieve values from env vars.

        :param prefix: Prefix to the name environment variables.
        """
        super().__init__(
            host=os.environ.get(f"{prefix}RABBITMQ_HOSTNAME", RabbitMQConfig.host),
            port=int(os.environ.get(f"{prefix}RABBITMQ_PORT", RabbitMQConfig.port)),
            username=os.environ.get(f"{prefix}RABBITMQ_USERNAME", RabbitMQConfig.username),
            password=os.environ.get(f"{prefix}RABBITMQ_PASSWORD", RabbitMQConfig.password),
            virtual_host=os.environ.get(
                f"{prefix}RABBITMQ_VIRTUALHOST", RabbitMQConfig.virtual_host
            ),
        )
