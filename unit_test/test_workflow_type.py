import unittest
from datetime import datetime

from google.protobuf import json_format

from omotes_sdk.workflow_type import (
    convert_params_dict_to_struct,
    parse_workflow_config_parameter,
    MissingFieldException,
    WrongFieldTypeException,
    BooleanParameter,
    StringParameter,
    DateTimeParameter,
    IntegerParameter,
    FloatParameter,
    WorkflowType,
    WorkflowTypeManager,
)
from omotes_sdk.types import ParamsDict


class WorkflowTypeTest(unittest.TestCase):
    def test__eq__same_id_but_different_description_should_still_be_same(self) -> None:
        # Arrange
        type_1 = WorkflowType("some-name", "some descript 1")
        type_2 = WorkflowType("some-name", "some descript 2")

        # Act
        is_same = type_1 == type_2

        # Assert
        self.assertTrue(is_same)

    def test__eq__different_id_but_same_description_should_not_be_same(self) -> None:
        # Arrange
        type_1 = WorkflowType("some-name-1", "some descript")
        type_2 = WorkflowType("some-name-2", "some descript")

        # Act
        is_same = type_1 == type_2

        # Assert
        self.assertFalse(is_same)

    def test__hash__same_id_but_different_descript_should_have_same_hash(self) -> None:
        # Arrange
        type_1 = WorkflowType("some-name", "some descript-1")
        type_2 = WorkflowType("some-name", "some descript-2")

        # Act
        hash_1 = hash(type_1)
        hash_2 = hash(type_2)

        # Assert
        self.assertEqual(hash_1, hash_2)

    def test__hash__same_descript_but_different_id_should_have_different_hash(self) -> None:
        # Arrange
        type_1 = WorkflowType("some-name-1", "some descript")
        type_2 = WorkflowType("some-name-2", "some descript")

        # Act
        hash_1 = hash(type_1)
        hash_2 = hash(type_2)

        # Assert
        self.assertNotEqual(hash_1, hash_2)

    def test__from_json_config_file__happy(self) -> None:
        # Arrange
        workflow_json_file = "./unit_test/test_config/workflow_config_happy.json"

        # Act
        workflow_type_manager = WorkflowTypeManager.from_json_config_file(workflow_json_file)

        # Assert
        self.assertEqual(len(workflow_type_manager.get_all_workflows()), 2)

    def test__from_json_config_file__integer_minimum_as_float(self) -> None:
        # Arrange
        workflow_json_file = "./unit_test/test_config/workflow_config_int_min_as_float.json"

        # Act / Assert
        with self.assertRaises(TypeError) as error_context:
            WorkflowTypeManager.from_json_config_file(workflow_json_file)
        self.assertEqual(
            str(error_context.exception),
            "'minimum' for IntegerParameter must be in 'int' format: '1.5'",
        )

    def test__from_json_config_file__enum_option_missing_key(self) -> None:
        # Arrange
        workflow_json_file = "./unit_test/test_config/workflow_config_enum_option_missing_key.json"

        # Act / Assert
        with self.assertRaises(TypeError) as error_context:
            WorkflowTypeManager.from_json_config_file(workflow_json_file)
        self.assertEqual(
            str(error_context.exception), "A string enum option must contain a 'display_name'"
        )

    def test__from_json_config_file__enum_options_not_as_list(self) -> None:
        # Arrange
        workflow_json_file = "./unit_test/test_config/workflow_config_enum_options_not_as_list.json"

        # Act / Assert
        with self.assertRaises(TypeError) as error_context:
            WorkflowTypeManager.from_json_config_file(workflow_json_file)
        self.assertEqual(
            str(error_context.exception), "'enum_options' for StringParameter must be a 'list'"
        )

    def test__from_json_config_file__wrong_datetime_format(self) -> None:
        # Arrange
        workflow_json_file = "./unit_test/test_config/workflow_config_wrong_datetime_format.json"

        # Act / Assert
        with self.assertRaises(ValueError) as error_context:
            WorkflowTypeManager.from_json_config_file(workflow_json_file)
        self.assertEqual(
            str(error_context.exception), "Invalid isoformat string: '2023-12-31T0:00:00'"
        )

    def test__to_pb_message__happy(self) -> None:
        # Arrange
        workflow_json_file = "./unit_test/test_config/workflow_config_happy.json"

        # Act
        workflow_type_manager = WorkflowTypeManager.from_json_config_file(workflow_json_file)
        pb_message = workflow_type_manager.to_pb_message()

        # Assert
        self.assertEqual(pb_message.workflows[0].type_name, "workflow_1")

    def test__from_pb_message__happy(self) -> None:
        # Arrange
        workflow_json_file = "./unit_test/test_config/workflow_config_happy.json"

        # Act
        workflow_type_manager = WorkflowTypeManager.from_json_config_file(workflow_json_file)
        pb_message = workflow_type_manager.to_pb_message()
        workflow_type_manager_from_pb = WorkflowTypeManager.from_pb_message(pb_message)

        # Assert
        self.assertEqual(len(workflow_type_manager_from_pb.get_all_workflows()), 2)


class TestModule(unittest.TestCase):
    def test__convert_params_dict_to_struct__list_bool_float_int_datetime_timedelta(self) -> None:
        # Arrange
        params_dict: ParamsDict = {
            # TODO "list": [1, 2, 3],
            "bool": True,
            "str": "some-str",
            "float": 2.0,
            "int": 3,
            "datetime": datetime.fromisoformat("2019-01-01T01:00:00"),
            # TODO "timedelta": timedelta(hours=1, seconds=15),
        }

        workflow_type = WorkflowType(
            workflow_type_name="some-workflow",
            workflow_type_description_name="description",
            workflow_parameters=[
                BooleanParameter(key_name="bool"),
                StringParameter(key_name="str"),
                FloatParameter(key_name="float"),
                IntegerParameter(key_name="int"),
                DateTimeParameter(key_name="datetime"),
            ],
        )

        # Act
        converted = convert_params_dict_to_struct(workflow_type, params_dict)

        # Assert
        expected_converted = {
            # TODO "list": [1.0, 2.0, 3.0],
            "bool": True,
            "str": "some-str",
            "float": 2.0,
            "int": 3.0,
            "datetime": datetime.fromisoformat("2019-01-01T01:00:00").timestamp(),
            # TODO "timedelta": 3615.0,
        }

        self.assertEqual(json_format.MessageToDict(converted), expected_converted)

    # TODO Reenable when list is integrated as a workflow parameter
    # def test__parse_workflow_config_parameter__list(self) -> None:
    #     # Arrange
    #     workflow_config: ParamsDict = {"some-key": [1.0, 2.0, 3.0]}
    #     field_key: str = "some-key"
    #     expected_type: Type[list] = list
    #     default_value: list[float] = []
    #
    #     # Act
    #     param = parse_workflow_config_parameter(
    #         workflow_config, field_key, expected_type, default_value
    #     )
    #
    #     # Assert
    #     expected_param = [1.0, 2.0, 3.0]
    #     self.assertEqual(param, expected_param)

    def test__parse_workflow_config_parameter__bool(self) -> None:
        # Arrange
        workflow_config = {"some-key": True}
        field_key = "some-key"
        expected_type = BooleanParameter
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
        expected_type = StringParameter
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
        expected_type = FloatParameter
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
        expected_type = IntegerParameter
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
        expected_type = DateTimeParameter
        default_value = datetime.fromisoformat("2019-01-01T00:00:00")

        # Act
        param = parse_workflow_config_parameter(
            workflow_config, field_key, expected_type, default_value
        )

        # Assert
        expected_param = datetime.fromisoformat("2019-01-01T01:00:00")
        self.assertEqual(param, expected_param)

    # TODO Enable when timedelta integration is added back in
    # def test__parse_workflow_config_parameter__timedelta(self) -> None:
    #     # Arrange
    #     workflow_config = {"some-key": 3615.0}
    #     field_key = "some-key"
    #     expected_type = timedelta
    #     default_value = timedelta(hours=1)
    #
    #     # Act
    #     param = parse_workflow_config_parameter(
    #         workflow_config, field_key, expected_type, default_value
    #     )
    #
    #     # Assert
    #     expected_param = timedelta(hours=1, seconds=15)
    #     self.assertEqual(param, expected_param)

    def test__parse_workflow_config_parameter__key_available_expect_int_but_get_float(self) -> None:
        # Arrange
        workflow_config = {"some-key": 1.4}
        field_key = "some-key"
        expected_type = IntegerParameter
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
        expected_type = FloatParameter
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
        expected_type = FloatParameter
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
        expected_type = FloatParameter
        default_value = None

        # Act / Asert
        with self.assertRaises(MissingFieldException):
            parse_workflow_config_parameter(
                workflow_config, field_key, expected_type, default_value
            )

    def test__parse_workflow_config_parameter__key_wrong_type_and_no_default(self) -> None:
        # Arrange
        workflow_config = {"some-key": True}
        field_key = "some-key"
        expected_type = FloatParameter
        default_value = None

        # Act / Assert
        with self.assertRaises(WrongFieldTypeException):
            parse_workflow_config_parameter(
                workflow_config, field_key, expected_type, default_value
            )
