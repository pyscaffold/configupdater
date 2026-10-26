"""Sections are intermediate containers in **ConfigUpdater**'s data model for
configuration files.

They are at the same time :class:`containers <Container>` that hold :class:`options
<Option>` and :class:`blocks <Block>` nested inside the top-level configuration
:class:`~configupdater.document.Document`.

Note:
    :meth:`Section.get` works like the :meth:`~collections.abc.Mapping.get` method of
    *dict-like* objects. Like ``section[key]``, it returns an :class:`Option` object,
    whereas the sections of :class:`~configparser.ConfigParser` return the value as a
    string.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, MutableMapping
from typing import TYPE_CHECKING, Any, Self, TypeVar, cast, overload

if TYPE_CHECKING:
    from .document import Document

from .block import Block, Comment, Space
from .builder import BlockBuilder
from .container import Container
from .option import Option

T = TypeVar("T")

Content = Option | Comment | Space
Value = Option | str


class Section(Block, Container[Content], MutableMapping[str, Option]):
    """Section block holding options"""

    def __init__(
        self, name: str, container: Document | None = None, raw_comment: str = ""
    ):
        self._container: Document | None = container
        self._name = name
        self._raw_comment = raw_comment
        self._structure: list[Content] = []
        self._updated = False
        super().__init__(container=container)

    @property
    def document(self) -> Document:
        return cast("Document", self.container)

    @property
    def add_before_skip_comments(self) -> BlockBuilder:
        """Insert before this section and its preceding comment blocks.

        Only consecutive comments in the document are skipped. A space or
        another section stops the search; comments inside a previous section
        are left in place. The existing :attr:`add_before` behavior is unchanged.
        """
        idx = self.container_idx
        structure = self.container.structure
        while idx > 0 and isinstance(structure[idx - 1], Comment):
            idx -= 1
        return self._builder(idx)

    def add_option(self, entry: Option) -> Self:
        """Add an Option object to the section

        Used during initial parsing mainly

        Args:
            entry (Option): key value pair as Option object
        """
        entry.attach(self)

        # Ensure a newline before the new option if the last block
        # doesn't end with one (e.g. file without trailing newline)
        if self._structure and not str(self._structure[-1]).endswith("\n"):
            space = Space(container=self)
            space.add_line("\n")
            self._structure.append(space)

        self._structure.append(entry)
        return self

    def add_comment(self, line: str) -> Self:
        """Add a Comment object to the section

        Used during initial parsing mainly

        Args:
            line (str): one line in the comment
        """
        if isinstance(self.last_block, Comment):
            comment: Comment = self.last_block
        else:
            comment = Comment(container=self)
            self._structure.append(comment)

        comment.add_line(line)
        return self

    def add_space(self, line: str) -> Self:
        """Add a Space object to the section

        Used during initial parsing mainly

        Args:
            line (str): one line that defines the space, possibly containing whitespace
        """
        if isinstance(self.last_block, Space):
            space = self.last_block
        else:
            space = Space(container=self)
            self._structure.append(space)

        space.add_line(line)
        return self

    # The following private helpers expect a key that was already transformed with
    # `optionxform`. Public methods transform the given key exactly once and then
    # use them, so a key is never transformed twice.
    def _get_option_idx(self, key: str) -> int:
        return next(
            i
            for i, entry in enumerate(self._structure)
            if isinstance(entry, Option) and entry.key == key
        )

    def _find_option(self, key: str) -> Option | None:
        return next((o for o in self.iter_options() if o.key == key), None)

    def __str__(self) -> str:
        if not self.updated:
            s = super().__str__()
            if self._structure and not s.endswith("\n"):
                s += "\n"
        else:
            s = f"[{self._name}]{self.raw_comment}\n"
        for entry in self._structure:
            s += str(entry)
        return s

    def __repr__(self) -> str:
        return f"<Section: {self.name!r} {super()._repr_blocks()}>"

    def _instantiate_copy(self) -> Self:
        """Will be called by :meth:`Block.__deepcopy__`"""
        clone = self.__class__(self._name, container=None)
        # ^  A fresh copy should always be made detached from any container
        clone._raw_comment = self._raw_comment
        return clone

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        clone = Block.__deepcopy__(self, memo)  # specific due to multi-inheritance
        return clone._copy_structure(self._structure, memo)

    def __getitem__(self, key: str) -> Option:
        key = self.document.optionxform(key)
        option = self._find_option(key)
        if option is None:
            raise KeyError(f"No option `{key}` found", {"key": key})
        return option

    def __setitem__(self, key: str, value: Value | None = None) -> None:
        """Set the value of an option.

        Please notice that this method uses
        :meth:`~configupdater.document.Document.optionxform` to verify if the given
        option already exists inside the section object. A new option keeps the
        given ``key`` as :attr:`~configupdater.Option.raw_key`.
        """
        # First we check for inconsistencies
        given_key = self.document.optionxform(key)
        if isinstance(value, Option):
            value_key = self.document.optionxform(value.raw_key)
            # ^ Calculate value_key according to the optionxform of the current
            #   document, in the case the option is imported from a document with a
            #   different optionxform
            option = value
            if value_key != given_key:
                msg = f"Set key `{given_key}` does not equal option key `{value_key}`"
                raise ValueError(msg)
        else:
            option = self.create_option(key, value)

        curr_option = self._find_option(given_key)
        if curr_option is not None:  # Replace an existing option
            if isinstance(value, Option):
                idx = curr_option.container_idx
                curr_option.detach()
                value.attach(self)
                self._structure.insert(idx, value)
            else:
                curr_option.value = value
        else:  # Append a new option
            self.add_option(option)

    def __delitem__(self, key: str) -> None:
        key = self.document.optionxform(key)
        try:
            idx = self._get_option_idx(key=key)
            del self._structure[idx]
        except StopIteration as ex:
            raise KeyError(f"No option `{key}` found", {"key": key}) from ex

    # MutableMapping[str, Option] accepts key: object. As in ConfigParser, the key is
    # passed to optionxform, which usually expects a string.
    def __contains__(self, key: object) -> bool:
        """Returns whether the given option exists.

        Like ``section[key]``, this applies
        :meth:`~configupdater.ConfigUpdater.optionxform` to ``key``.

        Args:
            key (str): name of option

        Returns:
            bool: whether the option exists
        """
        return self._find_option(self.document.optionxform(cast(str, key))) is not None

    def __eq__(self, other: object) -> bool:
        if isinstance(other, self.__class__):
            return self.name == other.name and self._structure == other._structure
        else:
            return False

    def __iter__(self) -> Iterator[str]:
        return (b.key for b in self.iter_blocks() if isinstance(b, Option))

    def iter_options(self) -> Iterator[Option]:
        """Iterate only over option blocks"""
        return (entry for entry in self.iter_blocks() if isinstance(entry, Option))

    def option_blocks(self) -> list[Option]:
        """Returns option blocks

        Returns:
            list: list of :class:`~configupdater.option.Option` blocks
        """
        return list(self.iter_options())

    def options(self) -> list[str]:
        """Returns option names

        Returns:
            list: list of option names as strings
        """
        return [option.key for option in self.iter_options()]

    has_option = __contains__

    def to_dict(self) -> dict[str, str | None]:
        """Transform to dictionary

        Returns:
            dict: dictionary with same content
        """
        return {opt.key: opt.value for opt in self.iter_options()}

    @property
    def name(self) -> str:
        """Name of the section"""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = str(value)
        self._updated = True

    @property
    def raw_comment(self) -> str:
        """Raw comment (includes comment mark) inline with the section header"""
        return self._raw_comment

    @raw_comment.setter
    def raw_comment(self, value: str) -> None:
        """Add/replace a single comment inline with the section header.
        The given value should be a raw comment, i.e. it needs to contain the
        comment mark.
        """
        self._raw_comment = value
        self._updated = True

    def set(self, option: str, value: str | Iterable[str] | None = None) -> Self:
        """Set an option for chaining.

        A new option keeps the given ``option`` name as
        :attr:`~configupdater.Option.raw_key`, like ``section[option] = value``.
        Unlike :meth:`configparser.ConfigParser.set`, which writes the key transformed
        by ``optionxform`` (lowercase by default), the file gets the given spelling.

        Args:
            option: option name
            value: value, default None
        """
        opt = self._find_option(self.document.optionxform(option))
        if opt is None:
            opt = self.create_option(option)
            self.add_option(opt)
        if not isinstance(value, Iterable) or isinstance(value, str):
            opt.value = value
        else:
            opt.set_values(value)
        return self

    def create_option(
        self,
        key: str,
        value: str | None = None,
        *,
        delimiter: str | None = None,
        space_around_delimiters: bool | None = None,
    ) -> Option:
        """Creates an option with kwargs that respect syntax options given to
        the parent ConfigUpdater object (e.g. ``space_around_delimiters``).

        ``delimiter`` and ``space_around_delimiters`` override the syntax options
        unless they are ``None``. With ``space_around_delimiters=None`` the option
        keeps following the syntax options of the ConfigUpdater it belongs to.

        Warning:
            This is a low level API, not intended for public use.
            Prefer :meth:`set` or :meth:`__setitem__`.
        """
        syntax_opts = getattr(self._container, "syntax_options", {})
        if delimiter is None:
            delimiter = next(iter(syntax_opts.get("delimiters", [])), None)
        kwargs_: dict[str, Any] = {
            "value": value,
            "container": self,
            "space_around_delimiters": space_around_delimiters,
            "delimiter": delimiter,
        }
        kwargs = {k: v for k, v in kwargs_.items() if v is not None}
        return Option(key, **kwargs)

    @overload
    def get(self, key: str) -> Option | None: ...

    @overload
    def get(self, key: str, default: T) -> Option | T: ...

    def get(self, key: str, default: T | None = None) -> Option | T | None:
        """This method works similarly to :meth:`dict.get`, and allows you
        to retrieve an option object by its key.

        Like ``section[key]``, this applies
        :meth:`~configupdater.ConfigUpdater.optionxform` to ``key``.
        """
        option = self._find_option(self.document.optionxform(key))
        return default if option is None else option

    # The following is a pragmatic violation of Liskov substitution principle
    # For some reason MutableMapping.items return a Set-like object
    # but we want to preserve ordering
    def items(self) -> list[tuple[str, Option]]:  # type: ignore[override]
        """Return a list of (name, option) tuples for each option in
        this section.

        Returns:
            list: list of (name, :class:`Option`) tuples
        """
        return [(opt.key, opt) for opt in self.option_blocks()]

    def insert_at(self, idx: int) -> BlockBuilder:
        """Returns a builder inserting a new block at the given index

        Args:
            idx (int): index where to insert
        """
        return BlockBuilder(self, idx)

    def clear(self) -> None:
        for block in self._structure:
            block.detach()
        self._structure.clear()
