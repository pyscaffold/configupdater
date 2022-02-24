"""Together with :mod:`~configupdater.container` this module forms the basis of
the class hierarchy in **ConfigUpdater**.

The :class:`Block` is the parent class of everything that can be nested inside a
configuration file, e.g. comments, sections, options and even sequences of white space.
"""
import sys
from abc import ABC
from copy import deepcopy
from inspect import cleandoc
from typing import TYPE_CHECKING, Optional, TypeVar, Union, cast

if sys.version_info[:2] >= (3, 9):  # pragma: no cover
    List = list
else:  # pragma: no cover
    from typing import List

if TYPE_CHECKING:
    from .builder import BlockBuilder
    from .container import Container

T = TypeVar("T")
B = TypeVar("B", bound="Block")


def _short_repr(block) -> str:
    if isinstance(block, str):
        return block
    name = getattr(block, "raw_key", None) or getattr(block, "name", None)
    name = f" {name!r}" if name else ""
    return f"<{block.__class__.__name__}{name}>"


class NotAttachedError(Exception):
    """{block} is not attached to a container yet. Try to insert it first."""

    def __init__(self, block: Union[str, "Block"] = "The block"):
        doc = cleandoc(cast(str, self.__class__.__doc__))
        msg = doc.format(block=_short_repr(block))
        super().__init__(msg)


class AlreadyAttachedError(Exception):
    """{block} has been already attached to a container.

    Try to remove it first using ``detach`` or create a copy using stdlib's
    ``copy.deepcopy``.
    """

    def __init__(self, block: Union[str, "Block"] = "The block"):
        doc = cleandoc(cast(str, self.__class__.__doc__))
        msg = doc.format(block=_short_repr(block))
        super().__init__(msg)


class AssignMultilineValueError(Exception):
    """Trying to assign a multi-line value to {block}.
    Use the ``set_values`` or ``append`` method to accomplish that.
    """

    def __init__(self, block: Union[str, "Block"] = "The block"):
        doc = cleandoc(cast(str, self.__class__.__doc__))
        msg = doc.format(block=_short_repr(block))
        super().__init__(msg)


class Block(ABC):
    """Abstract Block type holding lines

    Block objects hold original lines from the configuration file and hold
    a reference to a container wherein the object resides.

    The type variable ``T`` is a reference for the type of the sibling blocks
    inside the container.
    """

    def __init__(self, container: Optional["Container"] = None):
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

    def __deepcopy__(self: B, memo: dict) -> B:
        clone = self._instantiate_copy()
        clone._lines = deepcopy(self._lines, memo)
        clone._updated = self._updated
        memo[id(self)] = clone
        return clone

    def _instantiate_copy(self: B) -> B:
        """Auxiliary method that allows subclasses calling ``__deepcopy__``"""
        return self.__class__(container=None)  # allow overwrite for different init args
        # ^  A fresh copy should always be made detached from any container

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
    def container(self) -> "Container":
        """Container holding the block"""
        if self._container is None:
            raise NotAttachedError(self)
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
    def next_block(self) -> Optional["Block"]:
        """Next block in the current container"""
        idx = self.container_idx + 1
        if idx < len(self.container):
            return self.container.structure[idx]
        else:
            return None

    @property
    def previous_block(self) -> Optional["Block"]:
        """Previous block in the current container"""
        idx = self.container_idx - 1
        if idx >= 0:
            return self.container.structure[idx]
        else:
            return None

    def detach(self: B) -> B:
        """Remove and return this block from container"""
        self.container._remove_block(self.container_idx)
        self._container = None
        return self

    def has_container(self) -> bool:
        """Checks if this block has a container attached"""
        return not (self._container is None)

    def attach(self: B, container: "Container") -> B:
        """PRIVATE: Don't use this as a user!

        Rather use `add_*` or the bracket notation
        """
        if self._container is not None and self._container is not container:
            raise AlreadyAttachedError(self)
        self._container = container
        return self


class Comment(Block):
    """Comment block"""


class Space(Block):
    """Vertical space block of new lines"""
