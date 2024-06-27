import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Union
from typing_extensions import Self

from omotes_sdk_protocol.workflow_pb2 import (
    AvailableWorkflows,
    Workflow,
    WorkflowParameter as WorkflowParameterPb,
    StringParameter as StringParameterPb,
    StringEnum as StringEnumPb,
    BooleanParameter as BooleanParameterPb,
    IntegerParameter as IntegerParameterPb,
    FloatParameter as FloatParameterPb,
    DateTimeParameter as DateTimeParameterPb,
)


@dataclass(eq=True, frozen=True)
class WorkflowParameter:
    """Define a workflow parameter this SDK supports."""

    key_name: str = field(hash=True, compare=True)
    """Key name for the parameter."""
    title: str | None = field(default=None, hash=True, compare=True)
    """Optionally override the 'snake_case to text' 'key_name' (displayed above the input field)."""
    description: str | None = field(default=None, hash=True, compare=True)
    """Optional description (displayed below the input field)."""

    def __post_init__(self) -> None:
        """Check parameter format."""
        for name, field_type in self.__annotations__.items():
            # Do not check dataclasses (like KeyDisplayPair)
            # TODO better way of checking that 'field_type' is dataclass?
            if "KeyDisplayPair" not in str(field_type) and not isinstance(
                self.__dict__[name], field_type
            ):
                current_type = type(self.__dict__[name])
                raise TypeError(
                    f"The field `{name}` was assigned by `{current_type}` ('{self.__dict__[name]}')"
                    f" instead of `{field_type}`"
                )


@dataclass(eq=True, frozen=True)
class KeyDisplayPair:
    """Define a key display pair this SDK supports."""

    key_name: str = field(hash=True, compare=True)
    """Key name."""
    display_name: str = field(hash=True, compare=True)
    """Display name."""


@dataclass(eq=True, frozen=True)
class StringParameter(WorkflowParameter):
    """Define a string parameter this SDK supports."""

    type_name: str = "string"
    """Parameter type name."""
    default: str | None = field(default=None, hash=False, compare=False)
    """Optional default value."""
    enum_options: list[KeyDisplayPair] | None = field(default=None, hash=False, compare=False)
    """Optional multiple choice values."""


@dataclass(eq=True, frozen=True)
class BooleanParameter(WorkflowParameter):
    """Define a boolean parameter this SDK supports."""

    type_name: str = "boolean"
    """Parameter type name."""
    default: bool | None = field(default=None, hash=False, compare=False)
    """Optional default value."""


@dataclass(eq=True, frozen=True)
class IntegerParameter(WorkflowParameter):
    """Define an integer parameter this SDK supports."""

    type_name: str = "integer"
    """Parameter type name."""
    default: int | None = field(default=None, hash=False, compare=False)
    """Optional default value."""
    minimum: int | None = field(default=None, hash=False, compare=False)
    """Optional minimum allowed value."""
    maximum: int | None = field(default=None, hash=False, compare=False)
    """Optional maximum allowed value."""


@dataclass(eq=True, frozen=True)
class FloatParameter(WorkflowParameter):
    """Define a float parameter this SDK supports."""

    type_name: str = "float"
    """Parameter type name."""
    default: float | None = field(default=None, hash=False, compare=False)
    """Optional default value."""
    minimum: float | None = field(default=None, hash=False, compare=False)
    """Optional minimum allowed value."""
    maximum: float | None = field(default=None, hash=False, compare=False)
    """Optional maximum allowed value."""


@dataclass(eq=True, frozen=True)
class DateTimeParameter(WorkflowParameter):
    """Define a datetime parameter this SDK supports."""

    type_name: str = "datetime"
    """Parameter type name."""
    default: datetime | None = field(default=None, hash=False, compare=False)
    """Optional default value."""


@dataclass(eq=True, frozen=True)
class WorkflowType:
    """Define a type of workflow this SDK supports."""

    workflow_type_name: str = field(hash=True, compare=True)
    """Technical name for the workflow."""
    workflow_type_description_name: str = field(hash=False, compare=False)
    """Human-readable name for the workflow."""
    workflow_parameters: List[WorkflowParameter] | None = field(
        default=None, hash=False, compare=False
    )
    """Optional list of non-ESDL workflow parameters."""


class WorkflowTypeManager:
    """Container for all possible workflows."""

    _workflows: Dict[str, WorkflowType]
    """The possible workflows this SDK supports."""

    def __init__(self, possible_workflows: List[WorkflowType]):
        """Create the workflow type manager.

        :param possible_workflows: The workflows to manage.
        """
        self._workflows = {workflow.workflow_type_name: workflow for workflow in possible_workflows}

    def get_workflow_by_name(self, name: str) -> Optional[WorkflowType]:
        """Find the workflow type using the name.

        :param name: Name of the workflow type to find.
        :return: The workflow type if it exists.
        """
        return self._workflows.get(name)

    def get_all_workflows(self) -> List[WorkflowType]:
        """List all workflows.

        :return: The workflows.
        """
        return list(self._workflows.values())

    def workflow_exists(self, workflow: WorkflowType) -> bool:
        """Check if the workflow exists within this manager.

        :param workflow: Check if this workflow exists within the manager.
        :return: If the workflow exists.
        """
        return workflow.workflow_type_name in self._workflows

    def to_pb_message(self) -> AvailableWorkflows:
        """Generate a protobuf message containing the available workflows.

        :return: AvailableWorkflows protobuf message.
        """
        available_workflows_pb = AvailableWorkflows()
        for _workflow in self._workflows.values():
            workflow_pb = Workflow(
                type_name=_workflow.workflow_type_name,
                type_description=_workflow.workflow_type_description_name,
            )
            if _workflow.workflow_parameters:
                for _parameter in _workflow.workflow_parameters:
                    parameter_pb = WorkflowParameterPb(
                        key_name=_parameter.key_name,
                        title=_parameter.title,
                        description=_parameter.description,
                    )
                    if isinstance(_parameter, StringParameter):
                        string_parameter = StringParameterPb(default=_parameter.default)
                        if _parameter.enum_options:
                            for _string_enum in _parameter.enum_options:
                                string_parameter.enum_options.extend(
                                    [
                                        StringEnumPb(
                                            key_name=_string_enum.key_name,
                                            display_name=_string_enum.display_name,
                                        )
                                    ]
                                )
                        parameter_pb.string_parameter.CopyFrom(string_parameter)
                    elif isinstance(_parameter, BooleanParameter):
                        parameter_pb.boolean_parameter.CopyFrom(
                            BooleanParameterPb(
                                default=_parameter.default,
                            )
                        )
                    elif isinstance(_parameter, IntegerParameter):
                        parameter_pb.integer_parameter.CopyFrom(
                            IntegerParameterPb(
                                default=_parameter.default,
                                minimum=_parameter.minimum,
                                maximum=_parameter.maximum,
                            )
                        )
                    elif isinstance(_parameter, FloatParameter):
                        parameter_pb.float_parameter.CopyFrom(
                            FloatParameterPb(
                                default=_parameter.default,
                                minimum=_parameter.minimum,
                                maximum=_parameter.maximum,
                            )
                        )
                    elif isinstance(_parameter, DateTimeParameter):
                        if _parameter.default is None:
                            default_value = None
                        else:
                            default_value = _parameter.default.isoformat()
                        parameter_pb.datetime_parameter.CopyFrom(
                            DateTimeParameterPb(default=default_value)
                        )
                    else:
                        raise NotImplementedError(
                            f"Parameter type {type(_parameter)} not supported"
                        )
                    workflow_pb.parameters.extend([parameter_pb])
            available_workflows_pb.workflows.extend([workflow_pb])
        return available_workflows_pb

    @classmethod
    def from_pb_message(cls, available_workflows_pb: AvailableWorkflows) -> Self:
        """Create a WorkflowTypeManager instance from a protobuf message.

        :param available_workflows_pb: protobuf message containing the available workflows.
        :return: WorkflowTypeManager instance.
        """
        workflow_types = []
        for workflow_pb in available_workflows_pb.workflows:
            workflow_parameters: list[WorkflowParameter] = []
            for parameter_pb in workflow_pb.parameters:
                base_args = dict(
                    key_name=parameter_pb.key_name,
                    title=parameter_pb.title,
                    description=parameter_pb.description,
                )
                parameter_type_name = parameter_pb.WhichOneof("parameter_type")
                if parameter_type_name is None:
                    raise TypeError(f"Parameter protobuf message with invalid type: {parameter_pb}")
                else:
                    parameter_type = getattr(parameter_pb, parameter_type_name)

                parameter: Union[
                    StringParameter,
                    BooleanParameter,
                    IntegerParameter,
                    FloatParameter,
                    DateTimeParameter,
                ]
                if isinstance(parameter_type, StringParameterPb):
                    parameter = StringParameter(
                        **base_args, default=parameter_type.default, enum_options=[]
                    )
                    for enum_option_pb in parameter_type.enum_options:
                        if parameter.enum_options:
                            parameter.enum_options.append(
                                KeyDisplayPair(
                                    key_name=enum_option_pb.key_name,
                                    display_name=enum_option_pb.display_name,
                                )
                            )
                elif isinstance(parameter_type, BooleanParameterPb):
                    parameter = BooleanParameter(**base_args, default=parameter_type.default)
                elif isinstance(parameter_type, IntegerParameterPb):
                    parameter = IntegerParameter(
                        **base_args,
                        default=parameter_type.default,
                        minimum=(
                            parameter_type.minimum if parameter_type.HasField("minimum") else None
                        ),  # protobuf has '0' default value for int instead of None
                        maximum=(
                            parameter_type.maximum if parameter_type.HasField("maximum") else None
                        ),  # protobuf has '0' default value for int instead of None
                    )
                elif isinstance(parameter_type, FloatParameterPb):
                    parameter = FloatParameter(
                        **base_args,
                        default=parameter_type.default,
                        minimum=(
                            parameter_type.minimum if parameter_type.HasField("minimum") else None
                        ),  # protobuf has '0' default value for float instead of None
                        maximum=(
                            parameter_type.maximum if parameter_type.HasField("maximum") else None
                        ),  # protobuf has '0' default value for float instead of None
                    )
                elif isinstance(parameter_type, DateTimeParameterPb):
                    if parameter_type.HasField("default"):
                        try:
                            default = datetime.fromisoformat(parameter_type.default)
                        except TypeError:
                            raise TypeError(
                                f"Invalid default datetime format, should be string:"
                                f" {parameter_type.default}"
                            )
                        except ValueError:
                            raise ValueError(
                                f"Invalid default datetime value: {parameter_type.default}"
                            )
                    else:
                        default = None
                    parameter = DateTimeParameter(**base_args, default=default)
                else:
                    raise NotImplementedError(
                        f"Protobuf parameter type {type(parameter_pb)} not supported"
                    )
                workflow_parameters.append(parameter)
            workflow_types.append(
                WorkflowType(
                    workflow_type_name=workflow_pb.type_name,
                    workflow_type_description_name=workflow_pb.type_description,
                    workflow_parameters=workflow_parameters,
                )
            )
        return cls(workflow_types)

    @classmethod
    def from_json_config_file(cls, json_config_file_path: str) -> Self:
        """Create a WorkflowTypeManager instance from a json configuration file.

        :param json_config_file_path: path to the json workflow configuration file.
        :return: WorkflowTypeManager instance.
        """
        with open(json_config_file_path, "r") as f:
            json_config_dict = json.load(f)
        workflow_types = []
        for _workflow in json_config_dict:
            workflow_parameters = []
            if "workflow_parameters" in _workflow:
                for _parameter in _workflow["workflow_parameters"]:
                    parameter_type = _parameter["parameter_type"]
                    _parameter.pop("parameter_type")

                    parameter: WorkflowParameter
                    if parameter_type == StringParameter.type_name:
                        if "enum_options" in _parameter:
                            enum_options = []
                            for enum_option in _parameter["enum_options"]:
                                enum_options.append(
                                    KeyDisplayPair(
                                        key_name=enum_option["key_name"],
                                        display_name=enum_option["display_name"],
                                    )
                                )
                            _parameter.pop("enum_options")
                            parameter = StringParameter(**_parameter, enum_options=enum_options)
                        else:
                            parameter = StringParameter(**_parameter)
                    elif parameter_type == BooleanParameter.type_name:
                        parameter = BooleanParameter(**_parameter)
                    elif parameter_type == IntegerParameter.type_name:
                        parameter = IntegerParameter(**_parameter)
                    elif parameter_type == FloatParameter.type_name:
                        parameter = FloatParameter(**_parameter)
                    elif parameter_type == DateTimeParameter.type_name:
                        parameter = DateTimeParameter(**_parameter)
                    else:
                        raise NotImplementedError(f"Parameter type {parameter_type} not supported")
                    workflow_parameters.append(parameter)
            workflow_types.append(
                WorkflowType(
                    workflow_type_name=_workflow["workflow_type_name"],
                    workflow_type_description_name=_workflow["workflow_type_description_name"],
                    workflow_parameters=workflow_parameters,
                )
            )
        return cls(workflow_types)
