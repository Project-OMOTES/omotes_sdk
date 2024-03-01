from dataclasses import dataclass


@dataclass
class RabbitMQConfig:
    """Configuration for connect to RabbitMQ."""

    host: str = "localhost"
    """RabbitMQ hostname"""
    port: int = 5672
    """RabbitMQ port"""
    username: str = "omotes"
    """RabbitMQ username"""
    password: str = "guest"
    """RabbitMQ account password"""
    virtual_host: str = "omotes"
    """RabbitMQ virtual host"""
