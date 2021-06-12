import sys
from abc import ABC
from typing import Generic, Optional, TypeVar

if sys.version_info[:2] >= (3, 9):
    from collections.abc import Iterator

    List = list
else:
    from typing import Iterator, List

T = TypeVar("T")
C = TypeVar("C", bound="Container")


class Container(ABC, Generic[T]):
    """Abstract Mixin Class describing a container that holds blocks of type ``T``"""

    def __init__(self):
        self._structure: List[T] = []

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

    def iter_blocks(self) -> Iterator[T]:
        """Iterate over all blocks inside container."""
        return iter(self._structure)

    def __len__(self) -> int:
        """Number of blocks in container"""
        return len(self._structure)
