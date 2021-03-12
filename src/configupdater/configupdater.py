"""Configuration file updater.

A configuration file consists of sections, lead by a "[section]" header,
and followed by "name: value" entries, with continuations and such in
the style of RFC 822.

The basic idea of ConfigUpdater is that a configuration file consists of
three kinds of building blocks: sections, comments and spaces for separation.
A section itself consists of three kinds of blocks: options, comments and
spaces. This gives us the corresponding data structures to describe a
configuration file.

A general block object contains the lines which were parsed and make up
the block. If a block object was not changed then during writing the same
lines that were parsed will be used to express the block. In case a block,
e.g. an option, was changed, it is marked as `updated` and its values will
be transformed into a corresponding string during an update of a
configuration file.


.. note::

   ConfigUpdater was created by starting from Python's ConfigParser source
   code and changing it according to my needs. Thus this source code
   is subject to the PSF License in a way but I am not a lawyer.
"""

import io
import os
import re
import sys
from abc import ABC
from collections import OrderedDict
from configparser import (
    ConfigParser,
    DuplicateOptionError,
    DuplicateSectionError,
    Error,
    MissingSectionHeaderError,
    NoOptionError,
    NoSectionError,
    ParsingError,
)
from typing import (
    Generic,
    Optional,
    TextIO,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    no_type_check,
    overload,
)

if sys.version_info[:2] >= (3, 9):
    from collections.abc import Iterable, Iterator

    List = list
    Dict = dict
else:
    from typing import Dict, Iterable, Iterator, List

__all__ = [
    "NoSectionError",
    "DuplicateOptionError",
    "DuplicateSectionError",
    "NoOptionError",
    "NoConfigFileReadError",
    "ParsingError",
    "MissingSectionHeaderError",
    "ConfigUpdater",
    "Option",
    "Section",
    "Comment",
    "Space",
]


class NoConfigFileReadError(Error):
    """Raised when no configuration file was read but update requested."""

    def __init__(self):
        super().__init__("No configuration file was yet read! Use .read(...) first.")


# Used in parser getters to indicate the default behaviour when a specific
# option is not found it to raise an exception. Created to enable 'None' as
# a valid fallback value.
_UNSET = object()

T = TypeVar("T")
E = TypeVar("E", bound=Exception)
C = TypeVar("C", bound="Container")
B = TypeVar("B", bound="Block")
S = TypeVar("S", bound="Section")
U = TypeVar("U", bound="ConfigUpdater")
BB = TypeVar("BB", bound="BlockBuilder")

ConfigContent = Union["Section", "Comment", "Space"]
SectionContent = Union["Option", "Comment", "Space"]


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

    def __len__(self) -> int:
        """Number of blocks in container"""
        return len(self._structure)


class Block(ABC, Generic[T]):
    """Abstract Block type holding lines

    Block objects hold original lines from the configuration file and hold
    a reference to a container wherein the object resides.

    The type variable ``T`` is a reference for the type of the sibling blocks
    inside the container.
    """

    def __init__(self, container: Container[T]):
        self._container = container
        self._lines: List[str] = []
        self._updated = False

    def __str__(self) -> str:
        return "".join(self._lines)

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return str(self) == str(other)
        else:
            return False

    def add_line(self: B, line: str) -> B:
        """Add a line to the current block

        Args:
            line (str): one line to add
        """
        self._lines.append(line)
        return self

    @property
    def lines(self) -> List[str]:
        return self._lines

    @property
    def container(self) -> Container[T]:
        """Container holding the block"""
        return self._container

    @property
    def container_idx(self) -> int:
        """Index of the block within its container"""
        return self._container.structure.index(self)  # type: ignore

    @property
    def updated(self) -> bool:
        """True if the option was changed/updated, otherwise False"""
        # if no lines were added, treat it as updated since we added it
        return self._updated or not self._lines

    @property
    def add_before(self) -> "BlockBuilder":
        """Block builder inserting a new block before the current block"""
        return BlockBuilder(self._container, self.container_idx)

    @property
    def add_after(self) -> "BlockBuilder":
        """Block builder inserting a new block after the current block"""
        return BlockBuilder(self._container, self.container_idx + 1)

    @property
    def next_block(self) -> Optional[T]:
        """Next block in the current container"""
        idx = self.container_idx + 1
        if idx < len(self._container):
            return self._container.structure[idx]
        else:
            return None

    @property
    def previous_block(self) -> Optional[T]:
        """Previous block in the current container"""
        idx = self.container_idx - 1
        if idx >= 0:
            return self._container.structure[idx]
        else:
            return None

    def remove(self: B) -> B:
        """Remove this block from container"""
        self.container._remove_block(self.container_idx)
        return self


class Comment(Block[T]):
    """Comment block"""

    def __init__(self, container: Container[T]):
        super().__init__(container=container)

    def __repr__(self) -> str:
        return "<Comment>"


class Space(Block[T]):
    """Vertical space block of new lines"""

    def __init__(self, container: Container[T]):
        super().__init__(container=container)

    def __repr__(self) -> str:
        return "<Space>"


class Section(Block[ConfigContent], Container[SectionContent]):
    """Section block holding options

    Attributes:
        name (str): name of the section
        updated (bool): indicates name change or a new section
    """

    def __init__(self, name: str, container: "ConfigUpdater"):
        self._container: "ConfigUpdater" = container
        self._name = name
        self._structure: List[SectionContent] = []
        self._updated = False
        super().__init__(container=container)

    def add_option(self: S, entry: "Option") -> S:
        """Add an Option object to the section

        Used during initial parsing mainly

        Args:
            entry (Option): key value pair as Option object
        """
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
        else:
            s = "[{}]\n".format(self._name)
        for entry in self._structure:
            s += str(entry)
        return s

    def __repr__(self) -> str:
        return "<Section: {}>".format(self.name)

    def __getitem__(self, key: str) -> "Option":
        key = self._container.optionxform(key)
        try:
            return next(o for o in self.iter_options() if o.key == key)
        except StopIteration:
            raise KeyError(key)

    def __setitem__(self, key: str, value: Optional[str]):
        if self._container.optionxform(key) in self:
            option = self.__getitem__(key)
            option.value = value
        else:
            option = Option(key, value, container=self)
            option.value = value
            self._structure.append(option)

    def __delitem__(self, key: str):
        try:
            idx = self._get_option_idx(key=key)
            del self._structure[idx]
        except StopIteration:
            raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        """Returns whether the given option exists.

        Args:
            option (str): name of option

        Returns:
            bool: whether the section exists
        """
        return next((True for o in self.iter_options() if o.key == key), False)

    def __iter__(self) -> Iterator[SectionContent]:
        """Return all entries, not just options"""
        return iter(self._structure)

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self.name == other.name and self._structure == other._structure
        else:
            return False

    def iter_options(self) -> Iterator["Option"]:
        """Iterate only over option blocks"""
        return (entry for entry in self._structure if isinstance(entry, Option))

    def option_blocks(self) -> List["Option"]:
        """Returns option blocks

        Returns:
            list: list of :class:`Option` blocks
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
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = str(value)
        self._updated = True

    def set(self: S, option: str, value: Optional[str] = None) -> S:
        """Set an option for chaining.

        Args:
            option (str): option name
            value (str): value, default None
        """
        option = self._container.optionxform(option)
        if option in self.options():
            self.__getitem__(option).value = value
        else:
            self.__setitem__(option, value)
        return self

    def items(self) -> List[Tuple[str, "Option"]]:
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


class Option(Block[SectionContent]):
    """Option block holding a key/value pair.

    Attributes:
        key (str): name of the key
        value (str): stored value
        updated (bool): indicates name change or a new section
    """

    def __init__(
        self,
        key: str,
        value: Optional[str],
        container: Section,
        delimiter: str = "=",
        space_around_delimiters: bool = True,
        line: Optional[str] = None,
    ):
        self._container: Section = container
        super().__init__(container=container)
        self._key = key
        self._values: List[Optional[str]] = [value]
        self._value_is_none = value is None
        self._delimiter = delimiter
        self._value: Optional[str] = None  # will be filled after join_multiline_value
        self._updated = False
        self._multiline_value_joined = False
        self._space_around_delimiters = space_around_delimiters
        if line:
            super().add_line(line)

    def add_line(self, line: str):
        super().add_line(line)
        self._values.append(line.strip())

    def _join_multiline_value(self):
        if not self._multiline_value_joined and not self._value_is_none:
            # do what `_join_multiline_value` in ConfigParser would do
            self._value = "\n".join(self._values).rstrip()
            self._multiline_value_joined = True

    def __str__(self) -> str:
        if not self.updated:
            return super().__str__()
        if self._value is None:
            return "{}{}".format(self._key, "\n")
        if self._space_around_delimiters:
            # no space is needed if we use multi-line arguments
            suffix = "" if str(self._value).startswith("\n") else " "
            delim = " {}{}".format(self._delimiter, suffix)
        else:
            delim = self._delimiter
        return "{}{}{}{}".format(self._key, delim, self._value, "\n")

    def __repr__(self) -> str:
        return "<Option: {} = {}>".format(self.key, self.value)

    @property
    def key(self) -> str:
        return self._container._container.optionxform(self._key)

    @key.setter
    def key(self, value: str):
        self._join_multiline_value()
        self._key = value
        self._updated = True

    @property
    def value(self) -> Optional[str]:
        self._join_multiline_value()
        return self._value

    @value.setter
    def value(self, value: str):
        self._updated = True
        self._multiline_value_joined = True
        self._value = value
        self._values = [value]

    def set_values(self, values: List[str], separator="\n", indent=4 * " "):
        """Sets the value to a given list of options, e.g. multi-line values

        Args:
            values (iterable): sequence of values
            separator (str): separator for values, default: line separator
            indent (str): indentation depth in case of line separator
        """
        values = list(values).copy()
        self._updated = True
        self._multiline_value_joined = True
        self._values = cast(List[Optional[str]], values)
        if separator == "\n":
            values = [""] + values
            separator = separator + indent
        self._value = separator.join(values)


class BlockBuilder:
    """Builder that injects blocks at a given index position."""

    def __init__(self, container: Container, idx: int):
        self._container = container
        self._idx = idx

    def comment(self: BB, text: str, comment_prefix="#") -> BB:
        """Creates a comment block

        Args:
            text (str): content of comment without #
            comment_prefix (str): character indicating start of comment

        Returns:
            self for chaining
        """
        comment = Comment(self._container)
        if not text.startswith(comment_prefix):
            text = "{} {}".format(comment_prefix, text)
        if not text.endswith("\n"):
            text = "{}{}".format(text, "\n")
        comment.add_line(text)
        self._container.structure.insert(self._idx, comment)
        self._idx += 1
        return self

    def section(self: BB, section) -> BB:
        """Creates a section block

        Args:
            section (str or :class:`Section`): name of section or object

        Returns:
            self for chaining
        """
        if not isinstance(self._container, ConfigUpdater):
            raise ValueError("Sections can only be added at section level!")
        if isinstance(section, str):
            # create a new section
            section = Section(section, container=self._container)
        elif not isinstance(section, Section):
            raise ValueError("Parameter must be a string or Section type!")
        if section.name in [
            block.name for block in self._container if isinstance(block, Section)
        ]:
            raise DuplicateSectionError(section.name)
        self._container.structure.insert(self._idx, section)
        self._idx += 1
        return self

    def space(self: BB, newlines=1) -> BB:
        """Creates a vertical space of newlines

        Args:
            newlines (int): number of empty lines

        Returns:
            self for chaining
        """
        space = Space(container=self._container)
        for _ in range(newlines):
            space.add_line("\n")
        self._container.structure.insert(self._idx, space)
        self._idx += 1
        return self

    def option(self: BB, key, value=None, **kwargs) -> BB:
        """Creates a new option inside a section

        Args:
            key (str): key of the option
            value (str or None): value of the option
            **kwargs: are passed to the constructor of :class:`Option`

        Returns:
            self for chaining
        """
        if not isinstance(self._container, Section):
            raise ValueError("Options can only be added inside a section!")
        option = Option(key, value, container=self._container, **kwargs)
        if option.key in self._container.options():
            raise DuplicateOptionError(self._container.name, option.key)
        option.value = value
        self._container.structure.insert(self._idx, option)
        self._idx += 1
        return self


class ConfigUpdater(Container[ConfigContent]):
    """Parser for updating configuration files.

    ConfigUpdater follows the API of ConfigParser with some differences:
      * inline comments are treated as part of a key's value,
      * only a single config file can be updated at a time,
      * the original case of sections and keys are kept,
      * control over the position of a new section/key.

    Following features are **deliberately not** implemented:

      * interpolation of values,
      * propagation of parameters from the default section,
      * conversions of values,
      * passing key/value-pairs with ``default`` argument,
      * non-strict mode allowing duplicate sections and keys.
    """

    # Regular expressions for parsing section headers and options
    _SECT_TMPL: str = r"""
        \[                                 # [
        (?P<header>[^]]+)                  # very permissive!
        \]                                 # ]
        """
    _OPT_TMPL: str = r"""
        (?P<option>.*?)                    # very permissive!
        \s*(?P<vi>{delim})\s*              # any number of space/tab,
                                           # followed by any of the
                                           # allowed delimiters,
                                           # followed by any space/tab
        (?P<value>.*)$                     # everything up to eol
        """
    _OPT_NV_TMPL: str = r"""
        (?P<option>.*?)                    # very permissive!
        \s*(?:                             # any number of space/tab,
        (?P<vi>{delim})\s*                 # optionally followed by
                                           # any of the allowed
                                           # delimiters, followed by any
                                           # space/tab
        (?P<value>.*))?$                   # everything up to eol
        """
    # Compiled regular expression for matching sections
    SECTCRE = re.compile(_SECT_TMPL, re.VERBOSE)
    # Compiled regular expression for matching options with typical separators
    OPTCRE = re.compile(_OPT_TMPL.format(delim="=|:"), re.VERBOSE)
    # Compiled regular expression for matching options with optional values
    # delimited using typical separators
    OPTCRE_NV = re.compile(_OPT_NV_TMPL.format(delim="=|:"), re.VERBOSE)
    # Compiled regular expression for matching leading whitespace in a line
    NONSPACECRE = re.compile(r"\S")

    def __init__(
        self,
        allow_no_value=False,
        *,
        delimiters: Tuple[str, ...] = ("=", ":"),
        comment_prefixes: Tuple[str, ...] = ("#", ";"),
        inline_comment_prefixes: Optional[Tuple[str, ...]] = None,
        strict: bool = True,
        empty_lines_in_values: bool = True,
        space_around_delimiters: bool = True
    ):
        """Constructor of ConfigUpdater

        Args:
            allow_no_value (bool): allow keys without a value, default False
            delimiters (tuple): delimiters for key/value pairs, default =, :
            comment_prefixes (tuple): prefix of comments, default # and ;
            inline_comment_prefixes (tuple): prefix of inline comment,
                default None
            strict (bool): each section must be unique as well as every key
                within a section, default True
            empty_lines_in_values (bool): each empty line marks the end of an option.
                Otherwise, internal empty lines of a multiline option are kept as part
                of the value, default: True.
            space_around_delimiters (bool): add a space before and after the
                delimiter, default True
        """
        self._filename: Optional[str] = None
        self._space_around_delimiters: bool = space_around_delimiters

        self._dict = OrderedDict  # no reason to let the user change this
        # keeping _sections to keep code aligned with ConfigParser but
        # _structure takes the actual role instead. Only use self._structure!
        self._sections: OrderedDict[str, List[str]] = self._dict()
        self._structure: List[Union[Comment, Space, Section]] = []
        self._delimiters: Tuple[str, ...] = tuple(delimiters)
        if delimiters == ("=", ":"):
            self._optcre = self.OPTCRE_NV if allow_no_value else self.OPTCRE
        else:
            d = "|".join(re.escape(d) for d in delimiters)
            if allow_no_value:
                self._optcre = re.compile(self._OPT_NV_TMPL.format(delim=d), re.VERBOSE)
            else:
                self._optcre = re.compile(self._OPT_TMPL.format(delim=d), re.VERBOSE)
        self._comment_prefixes: Tuple[str, ...] = tuple(comment_prefixes or ())
        self._inline_comment_prefixes: Tuple[str, ...] = tuple(
            inline_comment_prefixes or ()
        )
        self._strict = strict
        self._allow_no_value = allow_no_value
        self._empty_lines_in_values = empty_lines_in_values
        super().__init__()

    def _get_section_idx(self, name: str) -> int:
        return next(
            i
            for i, entry in enumerate(self._structure)
            if isinstance(entry, Section) and entry.name == name
        )

    def read(self, filename: str, encoding: Optional[str] = None):
        """Read and parse a filename.

        Args:
            filename (str): path to file
            encoding (str): encoding of file, default None
        """
        with open(filename, encoding=encoding) as fp:
            self._read(fp, filename)
        self._filename = os.path.abspath(filename)

    def read_file(self, f: Iterable[str], source: Optional[str] = None):
        """Like read() but the argument must be a file-like object.

        The ``f`` argument must be iterable, returning one line at a time.
        Optional second argument is the ``source`` specifying the name of the
        file being read. If not given, it is taken from f.name. If ``f`` has no
        ``name`` attribute, ``<???>`` is used.

        Args:
            f: file like object
            source (str): reference name for file object, default None
        """
        if isinstance(f, str):
            raise RuntimeError("f must be a file-like object, not string!")
        if source is None:
            try:
                source = cast(str, cast(io.FileIO, f).name)
            except AttributeError:
                source = "<???>"
        self._read(f, source)

    def read_string(self, string: str, source="<string>"):
        """Read configuration from a given string.

        Args:
            string (str): string containing a configuration
            source (str): reference name for file object, default '<string>'
        """
        sfile = io.StringIO(string)
        self.read_file(sfile, source)

    def optionxform(self, optionstr) -> str:
        """Converts an option key to lower case for unification

        Args:
             optionstr (str): key name

        Returns:
            str: unified option name
        """
        return optionstr.lower()

    def _update_curr_block(
        self, block_type: Type[Union[Comment[T], Space[T]]]
    ) -> Union[Comment[T], Space[T]]:
        if isinstance(self.last_block, block_type):
            return self.last_block  # type: ignore
        else:
            new_block = block_type(container=self)  # type: ignore
            self._structure.append(new_block)
            return new_block

    def _add_comment(self, line):
        if isinstance(self.last_block, Section):
            self.last_block.add_comment(line)
        else:
            self._update_curr_block(Comment).add_line(line)

    def _add_section(self, sectname, line):
        new_section = Section(sectname, container=self)
        new_section.add_line(line)
        self._structure.append(new_section)

    def _add_option(self, key, vi, value, line):
        entry = Option(
            key,
            value,
            delimiter=vi,
            container=self.last_block,
            space_around_delimiters=self._space_around_delimiters,
            line=line,
        )
        assert isinstance(self.last_block, Section)
        # TODO: Replace the assertion with proper handling
        #       Why last_block was not being checked before?
        self.last_block.add_option(entry)

    def _add_space(self, line):
        if isinstance(self.last_block, Section):
            self.last_block.add_space(line)  # type: ignore
        else:
            self._update_curr_block(Space).add_line(line)

    @no_type_check
    def _read(self, fp: Iterable[str], fpname: str):
        """Parse a sectioned configuration file.

        Each section in a configuration file contains a header, indicated by
        a name in square brackets (`[]`), plus key/value options, indicated by
        `name` and `value` delimited with a specific substring (`=` or `:` by
        default).

        Values can span multiple lines, as long as they are indented deeper
        than the first line of the value. Depending on the parser's mode, blank
        lines may be treated as parts of multiline values or ignored.

        Configuration files may include comments, prefixed by specific
        characters (`#` and `;` by default). Comments may appear on their own
        in an otherwise empty line or may be entered in lines holding values or
        section names.

        Note: This method was borrowed from ConfigParser and we keep this
        mess here as close as possible to the original messod (pardon
        this german pun) for consistency reasons and later upgrades.
        """
        self._structure = []
        elements_added = set()
        cursect = None  # None, or a dictionary
        sectname = None
        optname = None
        lineno = 0
        indent_level = 0
        e = None  # None, or an exception
        for lineno, line in enumerate(fp, start=1):
            comment_start = sys.maxsize
            # strip inline comments
            inline_prefixes = {p: -1 for p in self._inline_comment_prefixes}
            while comment_start == sys.maxsize and inline_prefixes:
                next_prefixes = {}
                for prefix, index in inline_prefixes.items():
                    index = line.find(prefix, index + 1)
                    if index == -1:
                        continue
                    next_prefixes[prefix] = index
                    if index == 0 or (index > 0 and line[index - 1].isspace()):
                        comment_start = min(comment_start, index)
                inline_prefixes = next_prefixes
            # strip full line comments
            for prefix in self._comment_prefixes:
                # configparser would do line.strip() here,
                # we do rstrip() to allow comments in multi-line options
                if line.rstrip().startswith(prefix):
                    comment_start = 0
                    self._add_comment(line)  # HOOK
                    break
            if comment_start == sys.maxsize:
                comment_start = None
            value = line[:comment_start].strip()
            if not value:
                if self._empty_lines_in_values:
                    # add empty line to the value, but only if there was no
                    # comment on the line
                    if (
                        comment_start is None
                        and cursect is not None
                        and optname
                        and cursect[optname] is not None
                    ):
                        cursect[optname].append("")  # newlines added at join
                        if line.strip():
                            self.last_block.last_block.add_line(line)  # HOOK
                else:
                    # empty line marks end of value
                    indent_level = sys.maxsize
                if comment_start is None:
                    self._add_space(line)
                continue
            # continuation line?
            first_nonspace = self.NONSPACECRE.search(line)
            cur_indent_level = first_nonspace.start() if first_nonspace else 0
            if cursect is not None and optname and cur_indent_level > indent_level:
                cursect[optname].append(value)
                self.last_block.last_block.add_line(line)  # HOOK
            # a section header or option header?
            else:
                indent_level = cur_indent_level
                # is it a section header?
                mo = self.SECTCRE.match(value)
                if mo:
                    sectname = mo.group("header")
                    if sectname in self._sections:
                        if self._strict and sectname in elements_added:
                            raise DuplicateSectionError(sectname, fpname, lineno)
                        cursect = self._sections[sectname]
                        elements_added.add(sectname)
                    else:
                        cursect = self._dict()
                        self._sections[sectname] = cursect
                        elements_added.add(sectname)
                    # So sections can't start with a continuation line
                    optname = None
                    self._add_section(sectname, line)  # HOOK
                # no section header in the file?
                elif cursect is None:
                    raise MissingSectionHeaderError(fpname, lineno, line)
                # an option line?
                else:
                    mo = self._optcre.match(value)
                    if mo:
                        optname, vi, optval = mo.group("option", "vi", "value")
                        if not optname:
                            e = self._handle_error(e, fpname, lineno, line)
                        # optname = self.optionxform(optname.rstrip())
                        # keep original case of key
                        optname = optname.rstrip()
                        if self._strict and (sectname, optname) in elements_added:
                            raise DuplicateOptionError(
                                sectname, optname, fpname, lineno
                            )
                        elements_added.add((sectname, optname))
                        # This check is fine because the OPTCRE cannot
                        # match if it would set optval to None
                        if optval is not None:
                            optval = optval.strip()
                            cursect[optname] = [optval]
                        else:
                            # valueless option handling
                            cursect[optname] = None
                        self._add_option(optname, vi, optval, line)  # HOOK
                    # handle indented comment
                    elif first_nonspace.group(0) in self._comment_prefixes:
                        self._add_comment(line)  # HOOK
                    else:
                        # a non-fatal parsing error occurred. set up the
                        # exception but keep going. the exception will be
                        # raised at the end of the file and will contain a
                        # list of all bogus lines
                        e = self._handle_error(e, fpname, lineno, line)
        # if any parsing errors occurred, raise an exception
        if e:
            raise e
        # if empty_lines_in_values is true, we have to eliminate spurious newlines
        if self._empty_lines_in_values:
            self._check_values_with_blank_lines()

    def _handle_error(
        self, exc: Optional[E], fpname: str, lineno: int, line: str
    ) -> Union[ParsingError, E]:
        e = exc or ParsingError(fpname)
        if hasattr(e, "append"):
            e.append(lineno, repr(line))  # type: ignore
        return e

    def _check_values_with_blank_lines(self):
        for section in self.section_blocks():
            for option in section.option_blocks():
                next_block = option.next_block
                if isinstance(next_block, Space):
                    # check if space is part of a multi-line value with blank lines
                    if "".join(next_block.lines).strip():
                        self._merge_option_with_space(option, next_block)

    def _merge_option_with_space(self, option: Option, space: Space):
        last_val_idx = max(i for i, line in enumerate(space.lines) if line.strip())
        value_lines = space.lines[: last_val_idx + 1]
        merge_vals = "".join(line.lstrip(" ") for line in value_lines)
        option._values.append(merge_vals)
        option._multiline_value_joined = False
        option.lines.extend(space.lines[: last_val_idx + 1])
        del space.lines[: last_val_idx + 1]

    def write(self, fp: TextIO, validate: bool = True):
        # TODO: For Python>=3.8 instead of TextIO we can define a Writeable protocol
        """Write an .ini-format representation of the configuration state.

        Args:
            fp (file-like object): open file handle
            validate (Boolean): validate format before writing
        """
        if validate:
            self.validate_format()
        fp.write(str(self))

    def update_file(self, validate: bool = True):
        """Update the read-in configuration file.

        Args:
            validate (Boolean): validate format before writing
        """
        if self._filename is None:
            raise NoConfigFileReadError()
        if validate:  # validate BEFORE opening the file!
            self.validate_format()
        with open(self._filename, "w") as fb:
            self.write(fb, validate=False)

    def validate_format(self, **kwargs):
        """Call ConfigParser to validate config

        Args:
            kwargs: are passed to :class:`configparser.ConfigParser`
        """
        args = dict(
            dict_type=self._dict,
            allow_no_value=self._allow_no_value,
            inline_comment_prefixes=self._inline_comment_prefixes,
            strict=self._strict,
            empty_lines_in_values=self._empty_lines_in_values,
        )
        args.update(kwargs)
        parser = ConfigParser(**args)
        updated_cfg = str(self)
        parser.read_string(updated_cfg)

    def iter_sections(self) -> Iterator[Section]:
        """Iterate only over section blocks"""
        return (block for block in self._structure if isinstance(block, Section))

    def section_blocks(self) -> List[Section]:
        """Returns all section blocks

        Returns:
            list: list of :class:`Section` blocks
        """
        return list(self.iter_sections())

    def sections(self) -> List[str]:
        """Return a list of section names

        Returns:
            list: list of section names
        """
        return [section.name for section in self.iter_sections()]

    def __str__(self) -> str:
        return "".join(str(block) for block in self._structure)

    def __getitem__(self, key) -> Section:
        for section in self.section_blocks():
            if section.name == key:
                return section

        raise KeyError(key)

    def __setitem__(self, key: str, value: Section):
        if not isinstance(value, Section):
            raise ValueError("Value must be of type Section!")
        if isinstance(key, str) and key in self:
            idx = self._get_section_idx(key)
            del self._structure[idx]
            self._structure.insert(idx, value)
        else:
            # name the section by the key
            value.name = key
            self.add_section(value)

    def __delitem__(self, section: str):
        if not self.has_section(section):
            raise KeyError(section)
        self.remove_section(section)

    def __contains__(self, key: str) -> bool:
        """Returns whether the given section exists.

        Args:
            key (str): name of section

        Returns:
            bool: wether the section exists
        """
        return next((True for s in self.iter_sections() if s.name == key), False)

    has_section = __contains__

    def __iter__(self) -> Iterator[ConfigContent]:
        """Iterate over all blocks, not just sections"""
        return iter(self._structure)

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self._structure == other._structure
        else:
            return False

    def add_section(self, section: Union[str, Section]):
        """Create a new section in the configuration.

        Raise DuplicateSectionError if a section by the specified name
        already exists. Raise ValueError if name is DEFAULT.

        Args:
            section (str or :class:`Section`): name or Section type
        """
        if isinstance(section, str):
            # create a new section
            section_obj = Section(section, container=self)
        elif isinstance(section, Section):
            section_obj = section
        else:
            raise ValueError("Parameter must be a string or Section type!")

        if self.has_section(section_obj.name):
            raise DuplicateSectionError(section_obj.name)

        self._structure.append(section_obj)

    def options(self, section: str) -> List[str]:
        """Returns list of configuration options for the named section.

        Args:
            section (str): name of section

        Returns:
            list: list of option names
        """
        if not self.has_section(section):
            raise NoSectionError(section) from None
        return self.__getitem__(section).options()

    @overload
    def get(self, section: str, option: str) -> Option:
        ...

    @overload
    def get(self, section: str, option: str, fallback: None) -> None:  # noqa
        ...

    @overload
    def get(self, section: str, option: str, fallback: Option) -> Option:  # noqa
        ...

    def get(self, section, option, fallback=_UNSET):  # noqa
        """Gets an option value for a given section.

        Args:
            section (str): section name
            option (str): option name
            fallback: if the key is not found and fallback is provided, it will
                be returned. ``None`` is a valid fallback value.

        Returns:
            :class:`Option`: Option object holding key/value pair
        """
        if not self.has_section(section):
            raise NoSectionError(section) from None

        section_obj = self.__getitem__(section)
        option = self.optionxform(option)
        try:
            return section_obj[option]
        except KeyError:
            if fallback is _UNSET:
                raise NoOptionError(option, section)
            return fallback

    @overload
    def items(self) -> List[Tuple[str, Section]]:
        ...

    @overload
    def items(self, section: str) -> List[Tuple[str, Option]]:  # noqa
        ...

    def items(self, section=_UNSET):  # noqa
        """Return a list of (name, value) tuples for options or sections.

        If section is given, return a list of tuples with (name, value) for
        each option in the section. Otherwise, return a list of tuples with
        (section_name, section_type) for each section.

        Args:
            section (str): optional section name, default UNSET

        Returns:
            list: list of :class:`Section` or :class:`Option` objects
        """
        if section is _UNSET:
            return [(sect.name, sect) for sect in self.iter_sections()]

        section = self.__getitem__(section)
        return [(opt.key, opt) for opt in section.iter_options()]

    def has_option(self, section: str, option: str) -> bool:
        """Checks for the existence of a given option in a given section.

        Args:
            section (str): name of section
            option (str): name of option

        Returns:
            bool: whether the option exists in the given section
        """
        key = self.optionxform(option)
        return next(
            (s.has_option(key) for s in self.iter_sections() if s.name == section),
            False,
        )

    def set(self: U, section: str, option: str, value: Optional[str] = None) -> U:
        """Set an option.

        Args:
            section (str): section name
            option (str): option name
            value (str): value, default None
        """
        try:
            section_obj = self.__getitem__(section)
        except KeyError:
            raise NoSectionError(section) from None
        option = self.optionxform(option)
        if option in section_obj:
            section_obj[option].value = value
        else:
            section_obj[option] = value
        return self

    def remove_option(self, section: str, option: str) -> bool:
        """Remove an option.

        Args:
            section (str): section name
            option (str): option name

        Returns:
            bool: whether the option was actually removed
        """
        try:
            section_obj = self.__getitem__(section)
        except KeyError:
            raise NoSectionError(section) from None
        option = self.optionxform(option)
        existed = option in section_obj.options()
        if existed:
            del section_obj[option]
        return existed

    def remove_section(self, name: str) -> bool:
        """Remove a file section.

        Args:
            name: name of the section

        Returns:
            bool: whether the section was actually removed
        """
        existed = self.has_section(name)
        if existed:
            idx = self._get_section_idx(name)
            del self._structure[idx]
        return existed

    def to_dict(self) -> Dict[str, Dict[str, Optional[str]]]:
        """Transform to dictionary

        Returns:
            dict: dictionary with same content
        """
        return {sect.name: sect.to_dict() for sect in self.iter_sections()}
