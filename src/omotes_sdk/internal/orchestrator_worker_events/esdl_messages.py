from dataclasses import dataclass
from enum import Enum
from typing import Optional

from omotes_sdk_protocol.job_pb2 import EsdlMessage as EsdlMessagePb


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

    def to_protobuf_message(self) -> EsdlMessagePb:
        """Generate a protobuf message from this class.

        :return: Protobuf message representation.
        """
        return EsdlMessagePb(
            technical_message=self.technical_message,
            severity=EsdlMessagePb.Severity.Value(self.severity.value),
            esdl_object_id=self.esdl_object_id,
        )
