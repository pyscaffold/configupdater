"""Sections are intermediate containers in **ConfigUpdater**'s data model for
configuration files.

They are at the same time :class:`containers <Container>` that hold :mod:`options
<Option>` and :class:`blocks <Block>` nested inside the top level configuration
:class:`~configupdater.document.Document`.

Note:
    Please remember that :meth:`Section.get` method is implemented to mirror the
    :meth:`ConfigParser API <configparser.ConfigParser.set>` and do not correspond to
    the more usual :meth:`~collections.abc.Mapping.get` method of *dict-like* objects.
"""
import sys
from typing import TYPE_CHECKING, Optional, Tuple, TypeVar, Union, cast, overload

if sys.version_info[:2] >= (3, 9):  # pragma: no cover
    from collections.abc import Iterable, Iterator, MutableMapping

    List = list
    Dict = dict
else:  # pragma: no cover
    from typing import Dict, Iterable, Iterator, List, MutableMapping

if TYPE_CHECKING:
    from .document import Document

from .block import Block, Comment, Space
from .builder import BlockBuilder
from .container import Container
from .option import Option

T = TypeVar("T")
S = TypeVar("S", bound="Section")

Content = Union["Option", "Comment", "Space"]
Value = Union["Option", str]


class Section(Block, Container[Content], MutableMapping[str, "Option"]):
    """Section block holding options"""

    def __init__(
        self, name: str, container: Optional["Document"] = None, raw_comment: str = ""
    ):
        self._container: Optional["Document"] = container
        self._name = name
        self._raw_comment = raw_comment
        self._structure: List[Content] = []
        self._updated = False
        super().__init__(container=container)

    @property
    def document(self) -> "Document":
        return cast("Document", self.container)

    def add_option(self: S, entry: "Option") -> S:
        """Add an Option object to the section

        Used during initial parsing mainly

        Args:
            entry (Option): key value pair as Option object
        """
        entry.attach(self)
        self._structure.append(entry)
        return self

    def add_comment(self: S, line: str) -> S:
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

    def add_space(self: S, line: str) -> S:
        """Add a Space object to the section

        Used during initial parsing mainly

        Args:
            line (str): one line that defines the space, maybe whitespaces
        """
        if isinstance(self.last_block, Space):
            space = self.last_block
        else:
            space = Space(container=self)
            self._structure.append(space)

        space.add_line(line)
        return self

    def _get_option_idx(self, key: str) -> int:
        return next(
            i
            for i, entry in enumerate(self._structure)
            if isinstance(entry, Option) and entry.key == key
        )

    def __str__(self) -> str:
        if not self.updated:
            s = super().__str__()
            if self._structure and not s.endswith("\n"):
                s += "\n"
        else:
            s = "[{}]{}\n".format(self._name, self.raw_comment)
        for entry in self._structure:
            s += str(entry)
        return s

    def __repr__(self) -> str:
        return f"<Section: {self.name!r} {super()._repr_blocks()}>"

    def _instantiate_copy(self: S) -> S:
        """Will be called by :meth:`Block.__deepcopy__`"""
        clone = self.__class__(self._name, container=None)
        # ^  A fresh copy should always be made detached from any container
        clone._raw_comment = self._raw_comment
        return clone

    def __deepcopy__(self: S, memo: dict) -> S:
        clone = Block.__deepcopy__(self, memo)  # specific due to multi-inheritance
        return clone._copy_structure(self._structure, memo)

    def __getitem__(self, key: str) -> "Option":
        key = self.document.optionxform(key)
        try:
            return next(o for o in self.iter_options() if o.key == key)
        except StopIteration as ex:
            raise KeyError(f"No option `{key}` found", {"key": key}) from ex

    def __setitem__(self, key: str, value: Optional[Value] = None):
        """Set the value of an option.

        Please notice that this method used
        :meth:`~configupdater.document.Document.optionxform` to verify if the given
        option already exists inside the section object.
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

        if given_key in self:  # Replace an existing option
            if isinstance(value, Option):
                curr_value = self.__getitem__(given_key)
                idx = curr_value.container_idx
                curr_value.detach()
                value.attach(self)
                self._structure.insert(idx, value)
            else:
                option = self.__getitem__(given_key)
                option.value = value
        else:  # Append a new option
            option.attach(self)
            self._structure.append(option)

    def __delitem__(self, key: str):
        try:
            idx = self._get_option_idx(key=key)
            del self._structure[idx]
        except StopIteration as ex:
            raise KeyError(f"No option `{key}` found", {"key": key}) from ex

    # MutableMapping[str, Option] for some reason accepts key: object
    # it actually doesn't matter for the implementation, so we omit the typing
    def __contains__(self, key) -> bool:
        """Returns whether the given option exists.

        Args:
            option (str): name of option

        Returns:
            bool: whether the section exists
        """
        return next((True for o in self.iter_options() if o.key == key), False)

    # Omit typing so it can represent any object
    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self.name == other.name and self._structure == other._structure
        else:
            return False

    def __iter__(self) -> Iterator[str]:
        return (b.key for b in self.iter_blocks() if isinstance(b, Option))

    def iter_options(self) -> Iterator["Option"]:
        """Iterate only over option blocks"""
        return (entry for entry in self.iter_blocks() if isinstance(entry, Option))

    def option_blocks(self) -> List["Option"]:
        """Returns option blocks

        Returns:
            list: list of :class:`~configupdater.option.Option` blocks
        """
        return list(self.iter_options())

    def options(self) -> List[str]:
        """Returns option names

        Returns:
            list: list of option names as strings
        """
        return [option.key for option in self.iter_options()]

    has_option = __contains__

    def to_dict(self) -> Dict[str, Optional[str]]:
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
    def name(self, value: str):
        self._name = str(value)
        self._updated = True

    @property
    def raw_comment(self):
        """Raw comment (includes comment mark) inline with the section header"""
        return self._raw_comment

    @raw_comment.setter
    def raw_comment(self, value: str):
        """Add/replace a single comment inline with the section header.
        The given value should be a raw comment, i.e. it needs to contain the
        comment mark.
        """
        self._raw_comment = value
        self._updated = True

    def set(self: S, option: str, value: Union[None, str, Iterable[str]] = None) -> S:
        """Set an option for chaining.

        Args:
            option: option name
            value: value, default None
        """
        option = self.document.optionxform(option)
        if option not in self.options():
            self[option] = self.create_option(option)
        if not isinstance(value, Iterable) or isinstance(value, str):
            self[option].value = value
        else:
            self[option].set_values(value)
        return self

    def create_option(self, key: str, value: Optional[str] = None) -> "Option":
        """Creates an option with kwargs that respect syntax options given to
        the parent ConfigUpdater object (e.g. ``space_around_delimiters``).

        Warning:
            This is a low level API, not intended for public use.
            Prefer :meth:`set` or :meth:`__setitem__`.
        """
        syntax_opts = getattr(self._container, "syntax_options", {})
        kwargs_: dict = {
            "value": value,
            "container": self,
            "space_around_delimiters": syntax_opts.get("space_around_delimiters"),
            "delimiter": next(iter(syntax_opts.get("delimiters", [])), None),
        }
        kwargs = {k: v for k, v in kwargs_.items() if v is not None}
        return Option(key, **kwargs)

    @overload
    def get(self, key: str) -> Optional["Option"]:
        ...

    @overload
    def get(self, key: str, default: T) -> Union["Option", T]:
        ...

    def get(self, key, default=None):
        """This method works similarly to :meth:`dict.get`, and allows you
        to retrieve an option object by its key.
        """
        return next((o for o in self.iter_options() if o.key == key), default)

    # The following is a pragmatic violation of Liskov substitution principle
    # For some reason MutableMapping.items return a Set-like object
    # but we want to preserve ordering
    def items(self) -> List[Tuple[str, "Option"]]:  # type: ignore[override]
        """Return a list of (name, option) tuples for each option in
        this section.

        Returns:
            list: list of (name, :class:`Option`) tuples
        """
        return [(opt.key, opt) for opt in self.option_blocks()]

    def insert_at(self, idx: int) -> "BlockBuilder":
        """Returns a builder inserting a new block at the given index

        Args:
            idx (int): index where to insert
        """
        return BlockBuilder(self, idx)

    def clear(self):
        for block in self._structure:
            block.detach()
        self._structure.clear()
