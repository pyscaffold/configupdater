"""Parser for configuration files (normally ``*.cfg/*.ini``)

A configuration file consists of sections, lead by a "[section]" header,
and followed by "name: value" entries, with continuations and such in
the style of RFC 822.

The basic idea of **ConfigUpdater** is that a configuration file consists of
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

   ConfigUpdater is based on Python's ConfigParser source code, specially regarding the
   ``parser`` module.
   The main parsing rules and algorithm are preserved, however ConfigUpdater implements
   its own modified version of the abstract syntax tree to support retaining comments
   and whitespace in an attempt to provide format-preserving document manipulation.
   The copyright and license of the original ConfigParser code is included as an
   attachment to ConfigUpdater's own license, at the root of the source code repository;
   see the file LICENSE for details.
"""

import io
import os
import re
import sys
from configparser import (
    DuplicateOptionError,
    DuplicateSectionError,
    MissingSectionHeaderError,
    NoOptionError,
    NoSectionError,
    ParsingError,
)
from types import MappingProxyType as ReadOnlyMapping
from typing import Callable, Optional, Tuple, Type, TypeVar, Union, cast, overload

if sys.version_info[:2] >= (3, 9):  # pragma: no cover
    from collections.abc import Iterable, Mapping

    List = list
    Dict = dict
else:  # pragma: no cover
    from typing import Iterable, List, Dict, Mapping

from .block import Comment, Space
from .document import Document
from .option import Option
from .section import Section

__all__ = [
    "NoSectionError",
    "DuplicateOptionError",
    "DuplicateSectionError",
    "NoOptionError",
    "ParsingError",
    "MissingSectionHeaderError",
    "InconsistentStateError",
    "Parser",
]

T = TypeVar("T")
E = TypeVar("E", bound=Exception)
D = TypeVar("D", bound=Document)

if sys.version_info[:2] >= (3, 7):  # pragma: no cover
    PathLike = Union[str, bytes, os.PathLike]
else:  # pragma: no cover
    PathLike = Union[str, os.PathLike]

ConfigContent = Union["Section", "Comment", "Space"]


class InconsistentStateError(Exception):  # pragma: no cover (not expected to happen)
    """Internal parser error, some of the parsing algorithm assumptions was violated,
    and the internal state machine ended up in an unpredicted state.
    """

    def __init__(self, msg, fpname="<???>", lineno: int = -1, line: str = "???"):
        super().__init__(msg)
        self.args = (msg, fpname, lineno, line)

    def __str__(self):
        (msg, fpname, lineno, line) = self.args
        return f"{msg}\n{fpname}({lineno}): {line!r}"


class Parser:
    """Parser for updating configuration files.

    ConfigUpdater's parser follows ConfigParser with some differences:

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
        (?P<header>.+)                     # very permissive!
        \]                                 # ]
        (?P<raw_comment>.*)                # match any suffix
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
        space_around_delimiters: bool = True,
        optionxform: Callable[[str], str] = str,
    ):
        """Constructor of the Parser

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
        self._document: Document  # bind later
        self._optionxform_fn = optionxform
        self._lineno = -1
        self._fpname = "<???>"

        self._filename: Optional[str] = None
        self._space_around_delimiters: bool = space_around_delimiters

        self._dict = dict  # no reason to let the user change this
        # keeping _sections to keep code aligned with ConfigParser but
        # _document takes the actual role instead. Only use self._document!
        self._sections: Dict[str, Dict[str, List[str]]] = self._dict()
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

    def _get_args(self) -> dict:
        args = (
            "allow_no_value",
            "delimiters",
            "comment_prefixes",
            "inline_comment_prefixes",
            "strict",
            "empty_lines_in_values",
            "space_around_delimiters",
        )
        return {attr: getattr(self, f"_{attr}") for attr in args}

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self._get_args()!r}>"

    @property
    def syntax_options(self) -> Mapping:
        return ReadOnlyMapping(self._get_args())

    @overload
    def read(self, filename: PathLike, encoding: Optional[str] = None) -> Document:
        ...

    @overload
    def read(self, filename: PathLike, encoding: str, into: D) -> D:
        ...

    @overload
    def read(self, filename: PathLike, *, into: D, encoding: Optional[str] = None) -> D:
        ...

    def read(self, filename, encoding=None, into=None):
        """Read and parse a filename.

        Args:
            filename (str): path to file
            encoding (Optional[str]): encoding of file, default None
            into (Optional[Document]): object to be populated with the parsed config
        """
        document = Document() if into is None else into
        with open(filename, encoding=encoding) as fp:
            self._read(fp, str(filename), document)
        self._filename = os.path.abspath(filename)
        return document

    @overload
    def read_file(self, f: Iterable[str], source: Optional[str]) -> Document:
        ...

    @overload
    def read_file(self, f: Iterable[str], source: Optional[str], into: D) -> D:
        ...

    @overload
    def read_file(
        self, f: Iterable[str], *, into: D, source: Optional[str] = None
    ) -> D:
        ...

    def read_file(self, f, source=None, into=None):
        """Like read() but the argument must be a file-like object.

        The ``f`` argument must be iterable, returning one line at a time.
        Optional second argument is the ``source`` specifying the name of the
        file being read. If not given, it is taken from f.name. If ``f`` has no
        ``name`` attribute, ``<???>`` is used.

        Args:
            f: file like object
            source (Optional[str]): reference name for file object, default None
            into (Optional[Document]): object to be populated with the parsed config
        """
        if isinstance(f, str):
            raise RuntimeError("f must be a file-like object, not string!")
        document = Document() if into is None else into
        if source is None:
            try:
                source = cast(str, cast(io.FileIO, f).name)
            except AttributeError:
                source = "<???>"
        self._read(f, source, document)
        return document

    @overload
    def read_string(self, string: str, source: str = "<string>") -> Document:
        ...

    @overload
    def read_string(self, string: str, source: str, into: D) -> D:
        ...

    @overload
    def read_string(self, string: str, *, into: D, source: str = "<string>") -> D:
        ...

    def read_string(self, string, source="<string>", into=None):
        """Read configuration from a given string.

        Args:
            string (str): string containing a configuration
            source (str): reference name for file object, default '<string>'
            into (Optional[Document]): object to be populated with the parsed config
        """
        sfile = io.StringIO(string)
        return self.read_file(sfile, source, into)

    def optionxform(self, string: str) -> str:
        fn = self._optionxform_fn
        return fn(string)

    @property
    def _last_block(self):
        return self._document.last_block

    def _update_curr_block(
        self, block_type: Type[Union[Comment, Space]]
    ) -> Union[Comment, Space]:
        if isinstance(self._last_block, block_type):
            return self._last_block
        else:
            new_block = block_type(container=self._document)
            self._document.append(new_block)
            return new_block

    def _add_comment(self, line: str):
        if isinstance(self._last_block, Section):
            self._last_block.add_comment(line)
        else:
            self._update_curr_block(Comment).add_line(line)

    def _add_section(self, sectname: str, raw_comment: str, line: str):
        new_section = Section(
            sectname, container=self._document, raw_comment=raw_comment
        )
        new_section.add_line(line)
        self._document.append(new_section)

    def _add_option(self, key: str, vi: str, value: Optional[str], line: str):
        if not isinstance(self._last_block, Section):  # pragma: no cover
            msg = f"{self._last_block!r} should be Section"
            raise InconsistentStateError(msg, self._fpname, self._lineno, line)
        entry = Option(
            key,
            value=None,
            delimiter=vi,
            container=self._last_block,
            space_around_delimiters=self._space_around_delimiters,
            line=line,
        )
        # Initially add the value as further lines might follow
        entry.add_value(value)
        self._last_block.add_option(entry)

    def _add_option_line(self, line: str):
        last_section = self._last_block
        if not isinstance(last_section, Section):  # pragma: no cover
            msg = f"{last_section!r} should be Section"
            raise InconsistentStateError(msg, self._fpname, self._lineno, line)
        # if empty_lines_in_values is true, we later will merge options and whitespace
        # (in the _check_values_with_blank_lines function called at the end).
        # This allows option values to have empty new lines inside them
        # So for now we can add parts of option values to Space nodes, than we check if
        # that is an error or not.
        last_option = last_section.last_block
        # handle special case of unindented comment in multi-line value
        if isinstance(last_option, Comment):
            last_option, comment = (
                cast(Option, last_option.previous_block),
                last_option.detach(),
            )
            # move lines from comment to last option to keep it.
            for comment_line in comment.lines:
                last_option.add_line(comment_line)
        if not isinstance(last_option, (Option, Space)):  # pragma: no cover
            msg = f"{last_option!r} should be Option or Space"
            raise InconsistentStateError(msg, self._fpname, self._lineno, line)
        last_option.add_line(line)

    def _add_space(self, line: str):
        if isinstance(self._last_block, Section):
            self._last_block.add_space(line)
        else:
            self._update_curr_block(Space).add_line(line)

    def _read(self, fp: Iterable[str], fpname: str, into: Document):
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
        self._document = into
        elements_added: set = set()
        cursect: Optional[Dict[str, List[str]]] = None  # None or dict
        sectname: Optional[str] = None
        optname: Optional[str] = None
        lineno = 0
        indent_level = 0
        e: Optional[Exception] = None  # None, or an exception
        self._fpname = fpname
        for lineno, line in enumerate(fp, start=1):
            self._lineno = lineno
            comment_start: Optional[int] = sys.maxsize
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
                            self._add_option_line(line)  # HOOK
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
                self._add_option_line(line)  # HOOK
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
                    self._add_section(sectname, mo.group("raw_comment"), line)  # HOOK
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
                        if sectname is None:  # pragma: no cover
                            msg = f"Could not find the section name for {optname}"
                            raise InconsistentStateError(msg, fpname, lineno, line)
                        if self._strict and (sectname, optname) in elements_added:
                            args = (sectname, optname, fpname, lineno)
                            raise DuplicateOptionError(*args)
                        elements_added.add((sectname, optname))
                        # This check is fine because the OPTCRE cannot
                        # match if it would set optval to None
                        if optval is not None:
                            optval = optval.strip()
                            cursect[optname] = [optval]
                        else:
                            # valueless option handling
                            cursect[optname] = []  # None in Configparser
                        self._add_option(optname, vi, optval, line)  # HOOK
                    # handle indented comment
                    elif (
                        first_nonspace is not None
                        and first_nonspace.group(0) in self._comment_prefixes
                    ):
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
            e.append(lineno, repr(line))
            # ^  the typechecker cannot handle hasattr
        return e

    def _check_values_with_blank_lines(self):
        for section in self._document.section_blocks():
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
