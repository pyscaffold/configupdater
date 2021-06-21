"""Together with :mod:`~configupdater.block` this module forms the basis of
the class hierarchy in **ConfigUpdater**.

The :class:`Container` is the parent class of everything that can contain configuration
blocks, e.g. a section or the entire file itself.
"""
import sys
from abc import ABC
from textwrap import indent
from typing import Generic, Optional, TypeVar

if sys.version_info[:2] >= (3, 9):  # pragma: no cover
    from collections.abc import Iterator

    List = list
else:  # pragma: no cover
    from typing import Iterator, List

T = TypeVar("T")
C = TypeVar("C", bound="Container")


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

    def append(self: C, block: T) -> C:
        self._structure.append(block)
        return self
