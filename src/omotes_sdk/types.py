from typing import List, Union, Mapping

ParamsDictValues = Union[List["ParamsDictValues"], "ParamsDict", None, float, int, str, bool]
ParamsDict = Mapping[str, ParamsDictValues]
