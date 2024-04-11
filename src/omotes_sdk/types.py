from typing import List, Union, Mapping

ParamsDictValues = Union[List["ParamsDictValues"], "ParamsDict", None, float, str, bool]
ParamsDict = Mapping[str, ParamsDictValues]
