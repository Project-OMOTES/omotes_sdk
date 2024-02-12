import os
from typing import Optional

from omotes_sdk.config import RabbitMQConfig as EmptyRabbitMQConfig


class RabbitMQConfig(EmptyRabbitMQConfig):
    def __init__(self):
        super().__init__(
            host=os.environ.get("RABBITMQ_HOST", "localhost"),
            port=int(os.environ.get("RABBITMQ_PORT", "5672")),
            username=os.environ.get("RABBITMQ_USERNAME"),
            password=os.environ.get("RABBITMQ_PASSWORD"),
            virtual_host=os.environ.get("RABBITMQ_VIRTUALHOST", "omotes_celery"),
        )


class PostgreSQLConfig:
    host: str = os.environ.get("POSTGRESQL_HOST", "localhost")
    port: int = int(os.environ.get("POSTGRESQL_PORT", "5672"))
    database: str = os.environ.get("POSTGRESQL_DATABASE", "omotes_celery")
    username: Optional[str] = os.environ.get("POSTGRESQL_USERNAME")
    password: Optional[str] = os.environ.get("POSTGRESQL_PASSWORD")


class WorkerConfig:
    rabbitmq: RabbitMQConfig = RabbitMQConfig()
    postgresql: PostgreSQLConfig = PostgreSQLConfig()
    task_event_queue_name: str = os.environ.get("TASK_EVENT_QUEUE_NAME", "omotes_task_events")
    log_level: str = os.environ.get("LOG_LEVEL", "INFO")
