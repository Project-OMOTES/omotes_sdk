import logging
from datetime import datetime, timedelta
from typing import Type, Optional, TypeVar, cast, Union, Dict, get_args

from google.protobuf.struct_pb2 import Struct

from omotes_sdk.types import ParamsDict, ParamsDictValues

logger = logging.getLogger("omotes_sdk_internal")

ParamsDictValue = TypeVar("ParamsDictValue", bound=ParamsDictValues)


class WrongFieldTypeException(Exception):
    """Thrown when param_dict contains a value of the wrong type for some parameter."""

    ...


class MissingFieldTypeException(Exception):
    """Thrown when param_dict does not contain the value for some parameter."""

    ...


PBStructCompatibleTypes = Union[list, float, str, bool]


def convert_params_dict_to_struct(params_dict: ParamsDict) -> Struct:
    """Convert all values to Struct-compatible value types.

    If a value is already a Struct-compatible type, then it isn't convert.

    :param params_dict: The params dict to convert.
    :return: The protobuf Struct loaded with converted values.
    """
    normalized_dict: Dict[str, PBStructCompatibleTypes] = {}

    for key, value in params_dict.items():
        if type(value) is datetime:
            normalized_dict[key] = value.timestamp()
        elif type(value) is timedelta:
            normalized_dict[key] = value.total_seconds()
        elif type(value) is int:
            normalized_dict[key] = float(value)
        elif isinstance(value, get_args(PBStructCompatibleTypes)):
            normalized_dict[key] = value
        else:
            raise RuntimeError(
                f"Incompatible type {type(value)} with key {key} and value {value} in params_dict"
            )

    params_dict_struct = Struct()
    params_dict_struct.update(normalized_dict)

    return params_dict_struct


def parse_workflow_config_parameter(
    workflow_config: ParamsDict,
    field_key: str,
    expected_type: Type[ParamsDictValue],
    default_value: Optional[ParamsDictValue],
) -> ParamsDictValue:
    """Parse the workflow config parameter according to the expected key and type.

    If either the key is missing or the value has the wrong type, the default value is used
    if available.

    :param workflow_config: The workflow config to parse the field from.
    :param field_key: The key or name of the variable in workflow_config.
    :param expected_type: The expected Python type of the value.
    :param default_value: In case the key is missing or cannot be parsed properly, this value is
        used instead.
    :raises WrongFieldTypeException: If the key is available but has the wrong type and no default
        value is available, this exception is thrown.
    :raises MissingFieldTypeException: If the key is missing and no default value is available,
        this exception is thrown.
    :return: The value for the key or the default value.
    """
    maybe_value = workflow_config.get(field_key)
    of_type = type(maybe_value)
    is_present = field_key in workflow_config

    result: ParamsDictValue
    if is_present and isinstance(maybe_value, expected_type):
        # cast is necessary here as Expected type var may not have the same type as
        # `workflow_config[field_key]` according to the type checker. However, we have confirmed
        # the type already so we may cast it.
        result = cast(ParamsDictValue, maybe_value)
    elif is_present and type(maybe_value) is float and expected_type is datetime:
        result = cast(ParamsDictValue, datetime.fromtimestamp(maybe_value))
    elif is_present and type(maybe_value) is float and expected_type is timedelta:
        result = cast(ParamsDictValue, timedelta(seconds=maybe_value))
    elif is_present and type(maybe_value) is float and expected_type is int:
        # when the field value type is float but the Expected type is an integer,
        # round the value to an integer and log the warning message
        # if the non-rounded value is received.
        rounded_maybe_value = round(maybe_value)
        result = cast(ParamsDictValue, rounded_maybe_value)
        if rounded_maybe_value != maybe_value:
            logger.warning(
                "%s field was passed in workflow configuration but as a %s instead of %s. "
                "Rounding the field value from %s to %s.",
                field_key,
                of_type,
                expected_type,
                maybe_value,
                result,
            )
    elif default_value is not None:
        result = default_value
        if is_present and not isinstance(maybe_value, expected_type):
            logger.warning(
                "%s field was passed in workflow configuration but as a %s instead of %s. "
                "Using default value %d",
                field_key,
                of_type,
                expected_type,
                default_value,
            )
        else:
            logger.warning(
                "%s field was missing in workflow configuration. Using default value %s",
                field_key,
                default_value,
            )
    else:
        if is_present and not isinstance(maybe_value, expected_type):
            logger.error(
                "%s field was passed in workflow configuration but as a %s instead of %s. "
                "No default available.",
                field_key,
                of_type,
                expected_type,
            )
            raise WrongFieldTypeException()
        else:
            logger.error(
                "%s field was missing in workflow configuration. No default available.", field_key
            )
            raise MissingFieldTypeException()

    return result
