from dataclasses import dataclass


@dataclass
class RabbitMQConfig:
    """Configuration for connect to RabbitMQ"""

    password: str
    """RabbitMQ account password"""
    host: str = "localhost"
    """RabbitMQ hostname"""
    port: int = 5672
    """RabbitMQ port"""
    username: str = "omotes"
    """RabbitMQ username"""
    virtual_host: str = "omotes"
    """RabbitMQ virtual host"""
