from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from typing import List, Optional, Dict, Any
from typing_extensions import Self

from omotes_sdk_protocol.work_flow_pb2 import (
    AvailableWorkflows,
    Workflow,
    WorkflowParameter as WorkflowParameterPb,
    WorkflowParameterSchema as WorkflowParameterSchemaPb,
)


class ParameterType(Enum):
    """Json forms supported types."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"


class ParameterStringFormat(Enum):
    """Json forms supported string formats."""

    TIME = "time"
    DATE = "date"
    DATETIME = "date-time"


@dataclass(eq=True, frozen=True)
class DataClassToDict:
    """Enable dictionary creation."""

    def to_dict(self) -> dict:
        """Create dictionary from dataclass."""

        def get_value(v: Any) -> Any:
            """Get the proper value based on the type of data."""
            if v is None or v == [] or v == "":
                return None
            elif isinstance(v, list):
                return [get_value(item) for item in v]
            elif is_dataclass(v):
                return v.to_dict()
            elif isinstance(v, Enum):
                return v.value
            else:
                return v

        return {
            _field.name: get_value(getattr(self, _field.name))
            for _field in fields(self)
            if get_value(getattr(self, _field.name)) is not None
        }


@dataclass(eq=True, frozen=True)
class ParameterSchema(DataClassToDict):
    """Define a json forms schema for a WorkflowParameter this SDK supports.

    This schema can be used directly by a frontend: https://jsonforms.io/.
    If needed additional schema properties can be added.
    """

    type: ParameterType = field(hash=False, compare=False)
    """Type of the parameter."""
    title: str | None = field(default=None, hash=True, compare=True)
    """Optionally override the 'snake_case to text' 'key_name' (displayed above the input field)."""
    description: str | None = field(default=None, hash=True, compare=True)
    """Optional description (displayed below the input field)."""
    default: str | None = field(default=None, hash=False, compare=False)
    """Optional default value (number as string)."""
    format: ParameterStringFormat | None = field(default=None, hash=False, compare=False)
    """Optional format of a string type parameter (for date-time)."""
    enum: list[str] | None = field(default=None, hash=False, compare=False)
    """Optional multiple choice values of a string type parameter."""
    minimum: float | None = field(default=None, hash=False, compare=False)
    """Optional minimum allowed value of an integer or number type parameter."""
    maximum: float | None = field(default=None, hash=False, compare=False)
    """Optional maximum allowed value of an integer or number type parameter."""


@dataclass(eq=True, frozen=True)
class WorkflowParameter(DataClassToDict):
    """Define a workflow parameter this SDK supports."""

    key_name: str = field(hash=True, compare=True)
    """Key name for the parameter."""
    schema: ParameterSchema = field(hash=False, compare=False)
    """json form schema for the parameter."""


@dataclass(eq=True, frozen=True)
class WorkflowType(DataClassToDict):
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

    def to_dict(self) -> dict:
        """Generate a dictionary representation of the available workflows.

        :return: dictionary representation.
        """
        available_work_flows_dict = {}
        for workflow_name, workflow_type in self._workflows.items():
            available_work_flows_dict[workflow_name] = workflow_type.to_dict()
        return available_work_flows_dict

    def to_pb_message(self) -> AvailableWorkflows:
        """Generate a protobuf message containing the available workflows.

        :return: AvailableWorkflows protobuf message.
        """
        available_work_flows_pb = AvailableWorkflows()
        for _workflow in self._workflows.values():
            workflow_pb = Workflow(
                type_name=_workflow.workflow_type_name,
                type_description=_workflow.workflow_type_description_name,
            )
            if _workflow.workflow_parameters:
                for _parameter in _workflow.workflow_parameters:
                    parameter_pb = WorkflowParameterPb(
                        key_name=_parameter.key_name,
                        schema=WorkflowParameterSchemaPb(
                            type=_parameter.schema.type.value,
                            title=_parameter.schema.title,
                            description=_parameter.schema.description,
                            default=_parameter.schema.default,
                            format=(
                                _parameter.schema.format.value if _parameter.schema.format else None
                            ),
                            enum=_parameter.schema.enum,
                            minimum=_parameter.schema.minimum,
                            maximum=_parameter.schema.maximum,
                        ),
                    )
                    workflow_pb.parameters.extend([parameter_pb])
            available_work_flows_pb.workflows.extend([workflow_pb])
        return available_work_flows_pb

    @classmethod
    def from_pb_message(cls, available_work_flows_pb: AvailableWorkflows) -> Self:
        """Create a WorkflowTypeManager instance from a protobuf message.

        :param available_work_flows_pb: protobuf message containing the available workflows.
        :return: WorkflowTypeManager instance.
        """
        workflow_types = []
        for workflow_pb in available_work_flows_pb.workflows:
            workflow_parameters = []
            for parameter_pb in workflow_pb.parameters:
                workflow_parameters.append(
                    WorkflowParameter(
                        key_name=parameter_pb.key_name,
                        schema=ParameterSchema(
                            type=ParameterType(parameter_pb.schema.type),
                            title=parameter_pb.schema.title,
                            description=parameter_pb.schema.description,
                            default=parameter_pb.schema.default,
                            format=(
                                ParameterStringFormat(parameter_pb.schema.format)
                                if parameter_pb.schema.HasField("format")
                                else None
                            ),
                            enum=parameter_pb.schema.enum,
                            minimum=(
                                parameter_pb.schema.minimum
                                if parameter_pb.schema.HasField("minimum")
                                else None  # to deal with possible '0' value properly
                            ),
                            maximum=(
                                parameter_pb.schema.maximum
                                if parameter_pb.schema.HasField("maximum")
                                else None  # to deal with possible '0' value properly
                            ),
                        ),
                    )
                )
            workflow_types.append(
                WorkflowType(
                    workflow_type_name=workflow_pb.type_name,
                    workflow_type_description_name=workflow_pb.type_description,
                    workflow_parameters=workflow_parameters,
                )
            )
        return cls(workflow_types)
