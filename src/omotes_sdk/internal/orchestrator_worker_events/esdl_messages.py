from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MessageSeverity(Enum):
    """Message severity options."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class EsdlMessage:
    """Esdl feedback message, optionally related to a specific object (asset)."""

    technical_message: str
    """Technical message."""
    severity: MessageSeverity
    """Message severity."""
    esdl_object_id: Optional[str] = None
    """Optional esdl object id, None implies a general energy system message."""
