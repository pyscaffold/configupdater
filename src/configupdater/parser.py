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
from collections import OrderedDict
from configparser import (
    DuplicateOptionError,
    DuplicateSectionError,
    MissingSectionHeaderError,
    NoOptionError,
    NoSectionError,
    ParsingError,
)
from typing import Optional, Tuple, Type, TypeVar, Union, cast, no_type_check

if sys.version_info[:2] >= (3, 9):
    from collections.abc import Iterable, MutableMapping

    List = list
else:
    from typing import Iterable, List, MutableMapping


__all__ = [
    "NoSectionError",
    "DuplicateOptionError",
    "DuplicateSectionError",
    "NoOptionError",
    "ParsingError",
    "MissingSectionHeaderError",
    "ConfigUpdater",
]

T = TypeVar("T")
E = TypeVar("E", bound=Exception)

ConfigContent = Union["Section", "Comment", "Space"]


class ConfigUpdater(Container[ConfigContent], MutableMapping[str, Section]):
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
        space_around_delimiters: bool = True,
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

    def _update_curr_block(
        self, block_type: Type[Union[Comment[T], Space[T]]]
    ) -> Union[Comment[T], Space[T]]:
        if isinstance(self.last_block, block_type):
            return self.last_block  # type: ignore[return-value]
            # ^  the type checker is not understanding the isinstance check
        else:
            new_block = block_type(container=self)  # type: ignore[arg-type]
            # ^  the type checker is forgetting ConfigUpdater <: Container[T]
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
            self.last_block.add_space(line)
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
            e.append(lineno, repr(line))  # type: ignore[union-attr]
            # ^  the typechecker cannot handle hasattr
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
