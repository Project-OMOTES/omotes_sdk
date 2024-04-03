import logging
from typing import Type, Optional, TypeVar, cast

from omotes_sdk.types import ParamsDict, ParamsDictValues

logger = logging.getLogger("omotes_sdk_internal")

Expected = TypeVar("Expected", bound=ParamsDictValues)


class WrongFieldTypeException(Exception):
    """Thrown when param_dict contains a value of the wrong type for some parameter."""

    ...


class MissingFieldTypeException(Exception):
    """Thrown when param_dict does not contain the value for some parameter."""

    ...


def parse_workflow_config_parameter(
    workflow_config: ParamsDict,
    field_key: str,
    expected_type: Type[Expected],
    default_value: Optional[Expected],
) -> Expected:
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

    if is_present and isinstance(maybe_value, expected_type):
        # cast is necessary here as Expected type var may not have the same type as
        # `workflow_config[field_key]` according to the type checker. However, we have confirmed
        # the type already so we may cast it.
        result = cast(Expected, maybe_value)
    elif default_value:
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
                "%s field was missing in workflow configuration. Using default value %d",
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
