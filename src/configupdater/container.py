"""Together with :mod:`~configupdater.block` this module forms the basis of
the class hierarchy in **ConfigUpdater**.

The :class:`Container` is the parent class of everything that can contain configuration
blocks, e.g. a section or the entire file itself.
"""

import sys
from copy import deepcopy
from textwrap import indent
from typing import TYPE_CHECKING, Generic, TypeVar

from typing_extensions import Self

if sys.version_info[:2] >= (3, 9):  # pragma: no cover
    from collections.abc import Iterator

    List = list
else:  # pragma: no cover
    from collections.abc import Iterator

if TYPE_CHECKING:
    from .block import Block

T = TypeVar("T", bound="Block")
C = TypeVar("C", bound="Container")


class Container(Generic[T]):
    """Abstract Mixin Class describing a container that holds blocks of type ``T``"""

    _structure: list[T]

    def __init__(self):
        self._structure = []

    def _repr_blocks(self) -> str:
        blocks = "\n".join(repr(block) for block in self._structure)
        blocks = indent(blocks, " " * 4)
        return f"[\n{blocks.rstrip()}\n]" if blocks.strip() else "[]"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self._repr_blocks()}>"

    def __deepcopy__(self, memo: dict) -> Self:
        clone = self._instantiate_copy()
        memo[id(self)] = clone
        return clone._copy_structure(self._structure, memo)

    def _copy_structure(self, structure: list[T], memo: dict) -> Self:
        """``__deepcopy__`` auxiliary method also useful with multi-inheritance"""
        self._structure = [b.attach(self) for b in deepcopy(structure, memo)]
        return self

    def _instantiate_copy(self) -> Self:
        """Auxiliary method that allows subclasses calling ``__deepcopy__``"""
        return self.__class__()  # allow overwrite for different init args

    @property
    def structure(self) -> list[T]:
        return self._structure

    @property
    def first_block(self) -> T | None:
        if self._structure:
            return self._structure[0]
        else:
            return None

    @property
    def last_block(self) -> T | None:
        if self._structure:
            return self._structure[-1]
        else:
            return None

    def _remove_block(self, idx: int) -> Self:
        """Remove block at index idx within container

        Use `.container_idx` of a block to get the index.
        Not meant for users, rather use block.detach() instead!
        """
        del self._structure[idx]
        return self

    def iter_blocks(self) -> Iterator[T]:
        """Iterate over all blocks inside container."""
        return iter(self._structure)

    def __len__(self) -> int:
        """Number of blocks in container"""
        return len(self._structure)

    def append(self, block: T) -> Self:
        self._structure.append(block)
        return self
