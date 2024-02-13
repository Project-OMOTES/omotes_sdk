import os
from dataclasses import dataclass

from omotes_sdk.config import RabbitMQConfig
from omotes_sdk.internal.common.config import (
    EnvRabbitMQConfig,
)


@dataclass
class WorkerConfig:
    rabbitmq_config: RabbitMQConfig
    task_result_queue_name: str
    task_progress_queue_name: str
    log_level: str

    def __init__(self):
        self.rabbitmq_config = EnvRabbitMQConfig()
        self.task_result_queue_name = os.environ.get(
            "TASK_RESULT_QUEUE_NAME", "omotes_task_result_events"
        )
        self.task_progress_queue_name = os.environ.get(
            "TASK_PROGRESS_QUEUE_NAME", "omotes_task_progress_events"
        )
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")
