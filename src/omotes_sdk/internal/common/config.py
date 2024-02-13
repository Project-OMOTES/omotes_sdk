import os
from omotes_sdk.config import RabbitMQConfig as RabbitMQConfig


class EnvRabbitMQConfig(RabbitMQConfig):
    def __init__(self, prefix: str = ""):
        super().__init__(
            host=os.environ.get(f"{prefix}RABBITMQ_HOSTNAME", "localhost"),
            port=int(os.environ.get(f"{prefix}RABBITMQ_PORT", "5672")),
            username=os.environ.get(f"{prefix}RABBITMQ_USERNAME"),
            password=os.environ.get(f"{prefix}RABBITMQ_PASSWORD"),
            virtual_host=os.environ.get(f"{prefix}RABBITMQ_VIRTUALHOST", "omotes_celery"),
        )
