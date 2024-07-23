import unittest
from datetime import datetime, timedelta
from typing import Type

from google.protobuf import json_format

from omotes_sdk.internal.worker.params_dict import (
    convert_params_dict_to_struct,
    parse_workflow_config_parameter,
    MissingFieldTypeException,
    WrongFieldTypeException,
)
from omotes_sdk.types import ParamsDict


class TestModule(unittest.TestCase):
    def test__convert_params_dict_to_struct__list_bool_float_int_datetime_timedelta(self) -> None:
        # Arrange
        params_dict: ParamsDict = {
            "list": [1, 2, 3],
            "bool": True,
            "str": "some-str",
            "float": 2.0,
            "int": 3,
            "datetime": datetime.fromisoformat("2019-01-01T01:00:00"),
            "timedelta": timedelta(hours=1, seconds=15),
        }

        # Act
        converted = convert_params_dict_to_struct(params_dict)

        # Assert
        expected_converted = {
            "list": [1.0, 2.0, 3.0],
            "bool": True,
            "str": "some-str",
            "float": 2.0,
            "int": 3.0,
            "datetime": datetime.fromisoformat("2019-01-01T01:00:00").timestamp(),
            "timedelta": 3615.0,
        }

        self.assertEqual(json_format.MessageToDict(converted), expected_converted)

    def test__parse_workflow_config_parameter__list(self) -> None:
        # Arrange
        workflow_config: ParamsDict = {"some-key": [1.0, 2.0, 3.0]}
        field_key: str = "some-key"
        expected_type: Type[list] = list
        default_value: list[float] = []

        # Act
        param = parse_workflow_config_parameter(
            workflow_config, field_key, expected_type, default_value
        )

        # Assert
        expected_param = [1.0, 2.0, 3.0]
        self.assertEqual(param, expected_param)

    def test__parse_workflow_config_parameter__bool(self) -> None:
        # Arrange
        workflow_config = {"some-key": True}
        field_key = "some-key"
        expected_type = bool
        default_value = False

        # Act
        param = parse_workflow_config_parameter(
            workflow_config, field_key, expected_type, default_value
        )

        # Assert
        self.assertTrue(param)

    def test__parse_workflow_config_parameter__str(self) -> None:
        # Arrange
        workflow_config = {"some-key": "some-str"}
        field_key = "some-key"
        expected_type = str
        default_value = "default"

        # Act
        param = parse_workflow_config_parameter(
            workflow_config, field_key, expected_type, default_value
        )

        # Assert
        expected_param = "some-str"
        self.assertEqual(param, expected_param)

    def test__parse_workflow_config_parameter__float(self) -> None:
        # Arrange
        workflow_config = {"some-key": 2.0}
        field_key = "some-key"
        expected_type = float
        default_value = 1

        # Act
        param = parse_workflow_config_parameter(
            workflow_config, field_key, expected_type, default_value
        )

        # Assert
        expected_param = 2.0
        self.assertEqual(param, expected_param)

    def test__parse_workflow_config_parameter__int(self) -> None:
        # Arrange
        workflow_config = {"some-key": 2.0}
        field_key = "some-key"
        expected_type = int
        default_value = 3

        # Act
        param = parse_workflow_config_parameter(
            workflow_config, field_key, expected_type, default_value
        )

        # Assert
        expected_param = 2
        self.assertEqual(param, expected_param)

    def test__parse_workflow_config_parameter__datetime(self) -> None:
        # Arrange
        workflow_config = {"some-key": datetime.fromisoformat("2019-01-01T01:00:00").timestamp()}
        field_key = "some-key"
        expected_type = datetime
        default_value = datetime.fromisoformat("2019-01-01T00:00:00")

        # Act
        param = parse_workflow_config_parameter(
            workflow_config, field_key, expected_type, default_value
        )

        # Assert
        expected_param = datetime.fromisoformat("2019-01-01T01:00:00")
        self.assertEqual(param, expected_param)

    def test__parse_workflow_config_parameter__timedelta(self) -> None:
        # Arrange
        workflow_config = {"some-key": 3615.0}
        field_key = "some-key"
        expected_type = timedelta
        default_value = timedelta(hours=1)

        # Act
        param = parse_workflow_config_parameter(
            workflow_config, field_key, expected_type, default_value
        )

        # Assert
        expected_param = timedelta(hours=1, seconds=15)
        self.assertEqual(param, expected_param)

    def test__parse_workflow_config_parameter__key_available_and_correct_type(self) -> None:
        # Arrange
        workflow_config = {"some-key": 1.0}
        field_key = "some-key"
        expected_type = float
        default_value = 2.0

        # Act
        param = parse_workflow_config_parameter(
            workflow_config, field_key, expected_type, default_value
        )

        # Assert
        expected_param = 1.0
        self.assertEqual(param, expected_param)

    def test__parse_workflow_config_parameter__key_available_expect_int_but_get_float(self) -> None:
        # Arrange
        workflow_config = {"some-key": 1.4}
        field_key = "some-key"
        expected_type = int
        default_value = 2.0

        # Act
        param = parse_workflow_config_parameter(
            workflow_config, field_key, expected_type, default_value
        )

        # Assert
        expected_param = 1
        self.assertEqual(param, expected_param)

    def test__parse_workflow_config_parameter__key_unavailable_but_default(self) -> None:
        # Arrange
        workflow_config = {"no-key": 1.0}
        field_key = "some-key"
        expected_type = float
        default_value = 2.0

        # Act
        param = parse_workflow_config_parameter(
            workflow_config, field_key, expected_type, default_value
        )

        # Assert
        expected_param = 2.0
        self.assertEqual(param, expected_param)

    def test__parse_workflow_config_parameter__key_wrong_type_but_default(self) -> None:
        # Arrange
        workflow_config = {"some-key": True}
        field_key = "some-key"
        expected_type = float
        default_value = 2.0

        # Act
        param = parse_workflow_config_parameter(
            workflow_config, field_key, expected_type, default_value
        )

        # Assert
        expected_param = 2.0
        self.assertEqual(param, expected_param)

    def test__parse_workflow_config_parameter__key_missing_and_no_default(self) -> None:
        # Arrange
        workflow_config = {"no-key": 1.0}
        field_key = "some-key"
        expected_type = float
        default_value = None

        # Act / Asert
        with self.assertRaises(MissingFieldTypeException):
            parse_workflow_config_parameter(
                workflow_config, field_key, expected_type, default_value
            )

    def test__parse_workflow_config_parameter__key_wrong_type_and_no_default(self) -> None:
        # Arrange
        workflow_config = {"some-key": True}
        field_key = "some-key"
        expected_type = float
        default_value = None

        # Act / Assert
        with self.assertRaises(WrongFieldTypeException):
            parse_workflow_config_parameter(
                workflow_config, field_key, expected_type, default_value
            )
