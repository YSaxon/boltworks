from __future__ import annotations
from typing import Iterable, Tuple, Union, overload


class ExpandPointer:
    """
    An ExpandPointer is a series of indexes into a Node Tree which recursively indicates which nodes to expand.
    This class is just a wrapper around Tuple. It exists as a seperate class mostly to avoid the somewhat more confusing tuple syntax for tuple literals.
    """
    def __init__(self, values: Iterable[int]) -> None:
        self._values: Tuple[int,...] = tuple(values)
    @overload
    def __getitem__(self, index: int) -> int: ...
    @overload
    def __getitem__(self, index: slice) -> ExpandPointer: ...
    def __getitem__(self, index: Union[int, slice]) -> Union[int, ExpandPointer]:
        if isinstance(index, int):
            return self._values[index]
        elif isinstance(index, slice):
            return ExpandPointer(self._values[index])
        else:
            raise TypeError('Index must be an int or slice')

    def __hash__(self) -> int:
        return self._values.__hash__()
    def __len__(self) -> int:
        return self._values.__len__()
    def __iter__(self): return self._values.__iter__()

    def append(self, val: int) -> ExpandPointer:
        return ExpandPointer(self._values + (val,))

    def extend(self, obj: Iterable[int]) -> ExpandPointer:
        return ExpandPointer(self._values + tuple(obj))

    def __getstate__(self):
        return self._values
    def __setstate__(self, state):
        self._values = state