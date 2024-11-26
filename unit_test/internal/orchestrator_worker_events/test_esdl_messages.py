import unittest

from omotes_sdk.internal.orchestrator_worker_events.esdl_messages import (
    EsdlMessage,
    MessageSeverity,
)
from omotes_sdk_protocol.job_pb2 import EsdlMessage as EsdlMessagePb


class TestEsdlMessages(unittest.TestCase):
    def test__esdl_message__to_protobuf_message(self) -> None:
        # Arrange
        esdl_message = EsdlMessage(
            technical_message="message 1",
            severity=MessageSeverity.ERROR,
            esdl_object_id="uuid",
        )

        # Act
        esdl_message_pb = esdl_message.to_protobuf_message()

        # Assert
        assert esdl_message_pb.technical_message == "message 1"
        assert esdl_message_pb.severity == EsdlMessagePb.Severity.ERROR
        assert esdl_message_pb.esdl_object_id == "uuid"

    def test__esdl_message__to_protobuf_message_no_esdl_object_id(self) -> None:
        # Arrange
        esdl_message_esdl_object_id_none = EsdlMessage(
            technical_message="message 2",
            severity=MessageSeverity.WARNING,
            esdl_object_id=None,
        )
        esdl_message_esdl_object_id_omitted = EsdlMessage(
            technical_message="message 3",
            severity=MessageSeverity.INFO,
        )

        # Act
        esdl_message_esdl_object_id_none_pb = esdl_message_esdl_object_id_none.to_protobuf_message()
        esdl_message_esdl_object_id_omitted_pb = (
            esdl_message_esdl_object_id_omitted.to_protobuf_message()
        )

        # Assert
        assert esdl_message_esdl_object_id_none_pb.technical_message == "message 2"
        assert esdl_message_esdl_object_id_none_pb.severity == EsdlMessagePb.Severity.WARNING
        assert esdl_message_esdl_object_id_none_pb.esdl_object_id == ""
        assert esdl_message_esdl_object_id_omitted_pb.technical_message == "message 3"
        assert esdl_message_esdl_object_id_omitted_pb.severity == EsdlMessagePb.Severity.INFO
        assert esdl_message_esdl_object_id_omitted_pb.esdl_object_id == ""
