"""Together with :mod:`~configupdater.block` this module forms the basis of
the class hierarchy in **ConfigUpdater**.

The :class:`Container` is the parent class of everything that can contain configuration
blocks, e.g. a section or the entire file itself.
"""
import sys
import warnings
from abc import ABC
from copy import copy
from textwrap import indent
from typing import TYPE_CHECKING, Generic, Optional, TypeVar

if sys.version_info[:2] >= (3, 9):  # pragma: no cover
    from collections.abc import Iterator

    List = list
else:  # pragma: no cover
    from typing import Iterator, List

if TYPE_CHECKING:
    from .block import Block  # noqa

T = TypeVar("T", bound="Block")
C = TypeVar("C", bound="Container")


class AlreadyAttachedWarning(UserWarning):
    """The provided block is already attached to a different container.
    A copy of the block will be created.

    Please run ``node.remove()`` before attempting any insert.
    """

    def __init__(self):
        super().__init__(self.__class__.__doc__)


class Container(ABC, Generic[T]):
    """Abstract Mixin Class describing a container that holds blocks of type ``T``"""

    def __init__(self):
        self._structure: List[T] = []

    def _repr_blocks(self) -> str:
        blocks = "\n".join(repr(block) for block in self._structure)
        blocks = indent(blocks, " " * 4)
        return f"[\n{blocks.rstrip()}\n]" if blocks.strip() else "[]"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self._repr_blocks()}>"

    @property
    def structure(self) -> List[T]:
        return self._structure

    @property
    def first_block(self) -> Optional[T]:
        if self._structure:
            return self._structure[0]
        else:
            return None

    @property
    def last_block(self) -> Optional[T]:
        if self._structure:
            return self._structure[-1]
        else:
            return None

    def _remove_block(self: C, idx: int) -> C:
        """Remove block at index idx within container

        Use `.container_idx` of a block to get the index.
        Not meant for users, rather use block.remove() instead!
        """
        del self._structure[idx]
        return self

    def _remove_all(self: C) -> C:
        for block in self._structure:
            block._detach()
        self._structure.clear()
        return self

    def iter_blocks(self) -> Iterator[T]:
        """Iterate over all blocks inside container."""
        return iter(self._structure)

    def __len__(self) -> int:
        """Number of blocks in container"""
        return len(self._structure)

    def append(self: C, block: T) -> C:
        self._structure.append(self._adopt_or_copy(block))
        return self

    def insert(self: C, idx: int, block: T) -> C:
        self._structure.insert(idx, self._adopt_or_copy(block))
        return self

    def _adopt_or_copy(self, block: T) -> T:
        """Run this function before adopting any block inside the structure"""
        if block._container == self:
            return block

        if block.is_attached():
            warnings.warn(AlreadyAttachedWarning())
            block = copy(block)

        return block._attach(self)
