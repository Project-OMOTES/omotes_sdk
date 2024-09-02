from datetime import timedelta, datetime
from typing import List, Union, Mapping, TypeVar

ParamsDictValues = Union[
    List["ParamsDictValues"], "ParamsDict", None, float, int, str, bool, datetime, timedelta
]
ParamsDict = Mapping[str, ParamsDictValues]
PBStructCompatibleTypes = Union[list, float, str, bool]
