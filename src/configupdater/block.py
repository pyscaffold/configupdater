"""Together with :mod:`~configupdater.container` this module forms the basis of
the class hierarchy in **ConfigUpdater**.

The :class:`Block` is the parent class of everything that can be nested inside a
configuration file, e.g. comments, sections, options and even sequences of white space.
"""
import sys
from abc import ABC
from typing import TYPE_CHECKING, Generic, Optional, TypeVar

if sys.version_info[:2] >= (3, 9):  # pragma: no cover
    List = list
else:  # pragma: no cover
    from typing import List

if TYPE_CHECKING:
    from .builder import BlockBuilder
    from .container import Container

T = TypeVar("T")
B = TypeVar("B", bound="Block")


class NotAttachedError(Exception):
    """The block is not attached to a container yet. Try to insert it first."""

    def __init__(self):
        super().__init__(self.__class__.__doc__)


class Block(ABC, Generic[T]):
    """Abstract Block type holding lines

    Block objects hold original lines from the configuration file and hold
    a reference to a container wherein the object resides.

    The type variable ``T`` is a reference for the type of the sibling blocks
    inside the container.
    """

    def __init__(self, container: Optional["Container[T]"] = None):
        self._container = container
        self._lines: List[str] = []
        self._updated = False

    def __str__(self) -> str:
        return "".join(self._lines)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {str(self)!r}>"

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return str(self) == str(other)
        else:
            return False

    def add_line(self: B, line: str) -> B:
        """PRIVATE: this function is not part of the public API of Block.
        It is only used internally by other classes of the package during parsing.

        Add a line to the current block

        Args:
            line (str): one line to add
        """
        self._lines.append(line)
        return self

    @property
    def lines(self) -> List[str]:
        return self._lines

    @property
    def container(self) -> "Container[T]":
        """Container holding the block"""
        if self._container is None:
            raise NotAttachedError
        return self._container

    @property
    def container_idx(self: B) -> int:
        """Index of the block within its container"""
        return self.container.structure.index(self)

    @property
    def updated(self) -> bool:
        """True if the option was changed/updated, otherwise False"""
        # if no lines were added, treat it as updated since we added it
        return self._updated or not self._lines

    def _builder(self, idx: int) -> "BlockBuilder":
        from .builder import BlockBuilder

        return BlockBuilder(self.container, idx)

    @property
    def add_before(self) -> "BlockBuilder":
        """Block builder inserting a new block before the current block"""
        return self._builder(self.container_idx)

    @property
    def add_after(self) -> "BlockBuilder":
        """Block builder inserting a new block after the current block"""
        return self._builder(self.container_idx + 1)

    @property
    def next_block(self) -> Optional[T]:
        """Next block in the current container"""
        idx = self.container_idx + 1
        if idx < len(self.container):
            return self.container.structure[idx]
        else:
            return None

    @property
    def previous_block(self) -> Optional[T]:
        """Previous block in the current container"""
        idx = self.container_idx - 1
        if idx >= 0:
            return self.container.structure[idx]
        else:
            return None

    def remove(self: B) -> B:
        """Remove this block from container"""
        self.container._remove_block(self.container_idx)
        return self._detach()

    def is_attached(self) -> bool:
        return not (self._container is None)

    def _attach(self: B, container: "Container[T]") -> B:
        self._container = container
        return self

    def _detach(self: B) -> B:
        self._container = None
        return self


class Comment(Block[T]):
    """Comment block"""


class Space(Block[T]):
    """Vertical space block of new lines"""
