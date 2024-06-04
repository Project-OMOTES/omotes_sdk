import unittest

from omotes_sdk.internal.worker.params_dict import (
    parse_workflow_config_parameter,
    MissingFieldTypeException,
    WrongFieldTypeException,
)


class TestModule(unittest.TestCase):
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
