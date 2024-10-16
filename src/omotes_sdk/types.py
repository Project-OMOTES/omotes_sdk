from datetime import timedelta, datetime
from typing import List, Union, Dict

ParamsDictValues = Union[
    List["ParamsDictValues"], "ParamsDict", None, float, int, str, bool, datetime, timedelta
]
ParamsDict = Dict[str, ParamsDictValues]
PBStructCompatibleTypes = Union[list, float, str, bool]
ProtobufDict = Dict[str, PBStructCompatibleTypes]
