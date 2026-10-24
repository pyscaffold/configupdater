"""Together with :mod:`~configupdater.container` this module forms the basis of
the class hierarchy in **ConfigUpdater**.

The :class:`Block` is the parent class of everything that can be nested inside a
configuration file, e.g. comments, sections, options and even sequences of white space.
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, Self, TypeVar

if TYPE_CHECKING:
    from .builder import BlockBuilder
    from .container import Container

T = TypeVar("T")


def _short_repr(block: object) -> str:
    if isinstance(block, str):
        return block
    name = getattr(block, "raw_key", None) or getattr(block, "name", None)
    name = f" {name!r}" if name else ""
    return f"<{block.__class__.__name__}{name}>"


class NotAttachedError(Exception):
    """Raised when a block needs a container but is not attached to one.

    Insert the block first, e.g. with ``section[key] = option`` or one of the
    ``add_before``/``add_after`` builders.
    """

    def __init__(self, block: str | Block = "The block"):
        super().__init__(
            f"{_short_repr(block)} is not attached to a container yet. "
            "Try to insert it first."
        )


class AlreadyAttachedError(Exception):
    """Raised when a block is inserted while it is attached to another container.

    A block belongs to exactly one container. Remove it from the old one first with
    ``detach`` or insert a copy made with :func:`copy.deepcopy`.
    """

    def __init__(self, block: str | Block = "The block"):
        super().__init__(
            f"{_short_repr(block)} has been already attached to a container. "
            "Try to remove it first using ``detach`` or create a copy using "
            "stdlib's ``copy.deepcopy``."
        )


class AssignMultilineValueError(Exception):
    """Raised when a multi-line value is assigned to an option's ``value``.

    Use the option's ``set_values`` or ``append`` method for multi-line values.
    """

    def __init__(self, block: str | Block = "The block"):
        super().__init__(
            f"Trying to assign a multi-line value to {_short_repr(block)}. "
            "Use the ``set_values`` or ``append`` method to accomplish that."
        )


class Block:
    """Abstract Block type holding lines

    Block objects hold original lines from the configuration file and hold
    a reference to a container wherein the object resides.

    The type variable ``T`` is a reference for the type of the sibling blocks
    inside the container.
    """

    def __init__(self, container: Container[Any] | None = None) -> None:
        self._container = container
        self._lines: list[str] = []
        self._updated = False

    def __str__(self) -> str:
        return "".join(self._lines)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {str(self)!r}>"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, self.__class__):
            return str(self) == str(other)
        else:
            return False

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        clone = self._instantiate_copy()
        clone._lines = deepcopy(self._lines, memo)
        clone._updated = self._updated
        memo[id(self)] = clone
        return clone

    def _instantiate_copy(self) -> Self:
        """Auxiliary method that allows subclasses calling ``__deepcopy__``"""
        return self.__class__(container=None)  # allow overwrite for different init args
        # ^  A fresh copy should always be made detached from any container

    def add_line(self, line: str) -> Self:
        """PRIVATE: this function is not part of the public API of Block.
        It is only used internally by other classes of the package during parsing.

        Add a line to the current block

        Args:
            line (str): one line to add
        """
        self._lines.append(line)
        return self

    @property
    def lines(self) -> list[str]:
        return self._lines

    @property
    def container(self) -> Container[Any]:
        """Container holding the block"""
        if self._container is None:
            raise NotAttachedError(self)
        return self._container

    @property
    def container_idx(self) -> int:
        """Index of the block within its container"""
        for idx, block in enumerate(self.container.structure):
            if block is self:
                return idx
        raise ValueError(f"{self!r} is not in the container")

    @property
    def updated(self) -> bool:
        """True if the block was changed/updated, otherwise False"""
        # if no lines were added, treat it as updated since we added it
        return self._updated or not self._lines

    def _builder(self, idx: int) -> BlockBuilder:
        from .builder import BlockBuilder

        return BlockBuilder(self.container, idx)

    @property
    def add_before(self) -> BlockBuilder:
        """Block builder inserting a new block before the current block"""
        return self._builder(self.container_idx)

    @property
    def add_after(self) -> BlockBuilder:
        """Block builder inserting a new block after the current block"""
        return self._builder(self.container_idx + 1)

    @property
    def next_block(self) -> Block | None:
        """Next block in the current container"""
        idx = self.container_idx + 1
        if idx < len(self.container):
            block: Block = self.container.structure[idx]
            return block
        else:
            return None

    @property
    def previous_block(self) -> Block | None:
        """Previous block in the current container"""
        idx = self.container_idx - 1
        if idx >= 0:
            block: Block = self.container.structure[idx]
            return block
        else:
            return None

    def detach(self) -> Self:
        """Remove this block from its container and return it"""
        self.container._remove_block(self.container_idx)
        self._container = None
        return self

    def has_container(self) -> bool:
        """Checks if this block has a container attached"""
        return self._container is not None

    def attach(self, container: Container[Any]) -> Self:
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
