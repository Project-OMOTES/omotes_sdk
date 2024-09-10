from datetime import timedelta, datetime
from typing import List, Union, Mapping

ParamsDictValues = Union[
    List["ParamsDictValues"], "ParamsDict", None, float, int, str, bool, datetime, timedelta
]
ParamsDict = Mapping[str, ParamsDictValues]
PBStructCompatibleTypes = Union[list, float, str, bool]
ProtobufDict = Mapping[str, PBStructCompatibleTypes]
