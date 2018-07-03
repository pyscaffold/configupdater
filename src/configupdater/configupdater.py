"""Configuration file updater.

A configuration file consists of sections, lead by a "[section]" header,
and followed by "name: value" entries, with continuations and such in
the style of RFC 822.

Intrinsic defaults can be specified by passing them into the
ConfigParser constructor as a dictionary.

class:

ConfigParser -- responsible for parsing a list of
                    configuration files, and managing the parsed database.

    methods:

    __init__(defaults=None, dict_type=_default_dict, allow_no_value=False,
             delimiters=('=', ':'), comment_prefixes=('#', ';'),
             inline_comment_prefixes=None, strict=True,
             empty_lines_in_values=True, default_section='DEFAULT',
             interpolation=<unset>, converters=<unset>):
        Create the parser. When `defaults' is given, it is initialized into the
        dictionary or intrinsic defaults. The keys must be strings, the values
        must be appropriate for %()s string interpolation.

        When `dict_type' is given, it will be used to create the dictionary
        objects for the list of sections, for the options within a section, and
        for the default values.

        When `delimiters' is given, it will be used as the set of substrings
        that divide keys from values.

        When `comment_prefixes' is given, it will be used as the set of
        substrings that prefix comments in empty lines. Comments can be
        indented.

        When `inline_comment_prefixes' is given, it will be used as the set of
        substrings that prefix comments in non-empty lines.

        When `strict` is True, the parser won't allow for any section or option
        duplicates while reading from a single source (file, string or
        dictionary). Default is True.

        When `empty_lines_in_values' is False (default: True), each empty line
        marks the end of an option. Otherwise, internal empty lines of
        a multiline option are kept as part of the value.

        When `allow_no_value' is True (default: False), options without
        values are accepted; the value presented for these is None.

        When `default_section' is given, the name of the special section is
        named accordingly. By default it is called ``"DEFAULT"`` but this can
        be customized to point to any other valid section name. Its current
        value can be retrieved using the ``parser_instance.default_section``
        attribute and may be modified at runtime.

        When `interpolation` is given, it should be an Interpolation subclass
        instance. It will be used as the handler for option value
        pre-processing when using getters. RawConfigParser object s don't do
        any sort of interpolation, whereas ConfigParser uses an instance of
        BasicInterpolation. The library also provides a ``zc.buildbot``
        inspired ExtendedInterpolation implementation.

        When `converters` is given, it should be a dictionary where each key
        represents the name of a type converter and each value is a callable
        implementing the conversion from string to the desired datatype. Every
        converter gets its corresponding get*() method on the parser object and
        section proxies.

    sections()
        Return all the configuration section names, sans DEFAULT.

    has_section(section)
        Return whether the given section exists.

    has_option(section, option)
        Return whether the given option exists in the given section.

    options(section)
        Return list of configuration options for the named section.

    read(filenames, encoding=None)
        Read and parse the list of named configuration files, given by
        name.  A single filename is also allowed.  Non-existing files
        are ignored.  Return list of successfully read files.

    read_file(f, filename=None)
        Read and parse one configuration file, given as a file object.
        The filename defaults to f.name; it is only used in error
        messages (if f has no `name' attribute, the string `<???>' is used).

    read_string(string)
        Read configuration from a given string.

    read_dict(dictionary)
        Read configuration from a dictionary. Keys are section names,
        values are dictionaries with keys and values that should be present
        in the section. If the used dictionary type preserves order, sections
        and their keys will be added in order. Values are automatically
        converted to strings.

    get(section, option, raw=False, vars=None, fallback=_UNSET)
        Return a string value for the named option.  All % interpolations are
        expanded in the return values, based on the defaults passed into the
        constructor and the DEFAULT section.  Additional substitutions may be
        provided using the `vars' argument, which must be a dictionary whose
        contents override any pre-existing defaults. If `option' is a key in
        `vars', the value from `vars' is used.

    getint(section, options, raw=False, vars=None, fallback=_UNSET)
        Like get(), but convert value to an integer.

    getfloat(section, options, raw=False, vars=None, fallback=_UNSET)
        Like get(), but convert value to a float.

    getboolean(section, options, raw=False, vars=None, fallback=_UNSET)
        Like get(), but convert value to a boolean (currently case
        insensitively defined as 0, false, no, off for False, and 1, true,
        yes, on for True).  Returns False or True.

    items(section=_UNSET, raw=False, vars=None)
        If section is given, return a list of tuples with (name, value) for
        each option in the section. Otherwise, return a list of tuples with
        (section_name, section_proxy) for each section, including DEFAULTSECT.

    remove_section(section)
        Remove the given file section and all its options.

    remove_option(section, option)
        Remove the given option from the given section.

    set(section, option, value)
        Set the given option.

    write(fp, space_around_delimiters=True)
        Write the configuration state in .ini format. If
        `space_around_delimiters' is True (the default), delimiters
        between keys and values are surrounded by spaces.
"""

import io
import os
import re
import sys
from abc import ABC
from collections import OrderedDict as _default_dict
from collections.abc import MutableMapping
from configparser import (ConfigParser, DuplicateOptionError,
                          DuplicateSectionError, Error,
                          MissingSectionHeaderError, NoOptionError,
                          NoSectionError, ParsingError)

__all__ = ["NoSectionError", "DuplicateOptionError", "DuplicateSectionError",
           "NoOptionError", "NoConfigFileReadError", "ParsingError",
           "MissingSectionHeaderError", "ConfigUpdater"]


class NoConfigFileReadError(Error):
    """Raised when no configuration file was read but update requested."""
    def __init__(self):
        super().__init__(
            "No configuration file was yet read! Use .read(...) first.")


# Used in parser getters to indicate the default behaviour when a specific
# option is not found it to raise an exception. Created to enable `None' as
# a valid fallback value.
_UNSET = object()


class Block(ABC):
    def __init__(self, container=None):
        self._container = container
        self.lines = []
        self._updated = False

    def __str__(self):
        return ''.join(self.lines)

    def __len__(self):
        return len(self.lines)

    def _add_line(self, line):
        self.lines.append(line)

    @property
    def add_before(self):
        idx = self._container.index(self)
        return BlockBuilder(self._container, type(self), idx)

    @property
    def add_after(self):
        idx = self._container.index(self)
        return BlockBuilder(self._container, type(self), idx+1)


class BlockBuilder(object):
    def __init__(self, container, block_type, idx):
        self._container = container
        self._block_type = block_type
        self._idx = idx

    def comment(self, text):
        comment = Comment(self._container)
        if not text.startswith('#'):
            text = "# {}".format(text)
        if not text.endswith(os.linesep):
            text = "{}{}".format(text, os.linesep)
        comment._add_line(text)
        self._container.insert(self._idx, comment)
        return self

    def section(self, section_name):
        if self._block_type is not Section:
            raise ValueError("Sections can only be added at the section level!")
        section = Section(section_name, container=self._container)
        self._container.insert(self._idx, section)
        return self

    def space(self, newlines=1):
        space = Space()
        for line in range(newlines):
            space._add_line(os.linesep)
        self._container.insert(self._idx, space)
        return self

    def option(self, key, value=None, **kwargs):
        """Remaining options will be passed to the constructor of Option"""
        if self._block_type is not Option:
            raise ValueError("Options can only be added inside a section!")
        option = Option(key, value, container=self._container, **kwargs)
        option.value = value
        self._container.insert(self._idx, option)
        return self


class Comment(Block):
    def __init__(self, container=None):
        super().__init__(container)

    def __repr__(self):
        return '<Comment>'


class Space(Block):
    def __init__(self, container=None):
        super().__init__(container)

    def __repr__(self):
        return '<Space>'


class Section(Block, MutableMapping):
    def __init__(self, name, container):
        self._name = name
        self._structure = list()
        self._updated = False
        super().__init__(container)

    # used when constructing the section
    def _add_option(self, entry):
        self._structure.append(entry)

    def _add_comment(self):
        if not isinstance(self._curr_entry, Comment):
            comment = Comment(self._structure)
            self._structure.append(comment)

    def _add_space(self):
        if not isinstance(self._curr_entry, Space):
            space = Space(self._structure)
            self._structure.append(space)

    @property
    def _curr_entry(self):
        if self._structure:
            return self._structure[-1]
        else:
            return None

    def _get_option_idx(self, key):
        idx = [i for i, entry in enumerate(self._structure)
               if isinstance(entry, Option) and entry.key == key]
        if idx:
            return idx[0]
        else:
            raise ValueError

    def __str__(self):
        if not self.updated:
            s = super().__str__()
        else:
            s = "[{}]\n".format(self._name)
        for entry in self._structure:
            s += str(entry)
        return s

    def __repr__(self):
        return '<Section: {}>'.format(self.name)

    def __getitem__(self, key):
        if key not in self.options():
            raise KeyError(key)
        return self._structure[self._get_option_idx(key=key)]

    def __setitem__(self, key, value):
        if key in self:
            option = self.__getitem__(key)
            option.value = value
        else:
            option = Option(key, value, container=self._structure)
            option.value = value
            self._structure.append(option)

    def __delitem__(self, key):
        if key not in self.options():
            raise KeyError(key)
        idx = self._get_option_idx(key=key)
        del self._structure[idx]

    def __contains__(self, key):
        return key in self.options()

    def __len__(self):
        return len(self._structure)

    def __iter__(self):
        """Return all entries, not just options"""
        return self._structure.__iter__()

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._structure == other._structure
        else:
            return False

    def option_blocks(self):
        return [entry for entry in self._structure
                if isinstance(entry, Option)]

    def options(self):
        return [option.key for option in self.option_blocks()]

    @property
    def updated(self):
        """Returns if the option was changed/updaed"""
        # if no lines were added, treat it as updated since we added it
        return self._updated or not self.lines

    @property
    def name(self):
        # The name of the section on a proxy is read-only.
        return self._name


class Option(Block):
    def __init__(self, key, value, container, delimiter='=',
                 space_around_delimiters=True):
        self._key = key
        self._values = [value]
        self._delimiter = delimiter
        self._value = None  # will be filled after join_multiline_value
        self._updated = False
        self._multiline_value_joined = False
        self._space_around_delimiters = space_around_delimiters
        super().__init__(container)

    def _join_multiline_value(self):
        if not self._multiline_value_joined:
            # do what `_join_multiline_value` in ConfigParser would do
            self._value = os.linesep.join(self._values).rstrip()
            self._multiline_value_joined = True

    def __str__(self):
        if not self.updated:
            return super().__str__()
        if self._value is None:
            return "{}{}".format(self._key, os.linesep)
        if self._space_around_delimiters:
            delim = " {} ".format(self._delimiter)
        else:
            delim = ""
        return "{}{}{}{}".format(self._key, delim, self._value, os.linesep)

    def __repr__(self):
        return '<Option: {} = {}>'.format(self.key, self.value)

    @property
    def updated(self):
        """Returns if the option was changed/updaed"""
        # if no lines were added, treat it as updated since we added it
        return self._updated or not self.lines

    @property
    def key(self):
        return self._key

    @property
    def value(self):
        self._join_multiline_value()
        return self._value

    @value.setter
    def value(self, value):
        self._updated = True
        self._multiline_value_joined = True
        self._value = value
        self._values = [value]

    def set_values(self, values, separator=os.linesep, indent=4*' '):
        self._updated = True
        self._multiline_value_joined = True
        self._values = values
        if separator == os.linesep:
            values.insert(0, '')
            separator = indent + separator
        self._value = separator.join(values) + os.linesep


class ConfigUpdater(MutableMapping):
    # Regular expressions for parsing section headers and options
    _SECT_TMPL = r"""
        \[                                 # [
        (?P<header>[^]]+)                  # very permissive!
        \]                                 # ]
        """
    _OPT_TMPL = r"""
        (?P<option>.*?)                    # very permissive!
        \s*(?P<vi>{delim})\s*              # any number of space/tab,
                                           # followed by any of the
                                           # allowed delimiters,
                                           # followed by any space/tab
        (?P<value>.*)$                     # everything up to eol
        """
    _OPT_NV_TMPL = r"""
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

    def __init__(self, dict_type=_default_dict,
                 allow_no_value=False, *, delimiters=('=', ':'),
                 comment_prefixes=('#', ';'), inline_comment_prefixes=None,
                 strict=True, space_around_delimiters=True):

        self._filename = None
        self._space_around_delimiters = space_around_delimiters

        self._dict = dict_type
        # keeping _sections to keep code aligned with ConfigParser but
        # _structure takes the actual role instead. Only use self._structure!
        self._sections = self._dict()
        self._structure = []
        self._delimiters = tuple(delimiters)
        if delimiters == ('=', ':'):
            self._optcre = self.OPTCRE_NV if allow_no_value else self.OPTCRE
        else:
            d = "|".join(re.escape(d) for d in delimiters)
            if allow_no_value:
                self._optcre = re.compile(self._OPT_NV_TMPL.format(delim=d),
                                          re.VERBOSE)
            else:
                self._optcre = re.compile(self._OPT_TMPL.format(delim=d),
                                          re.VERBOSE)
        self._comment_prefixes = tuple(comment_prefixes or ())
        self._inline_comment_prefixes = tuple(inline_comment_prefixes or ())
        self._strict = strict
        self._allow_no_value = allow_no_value
        # Options from ConfigParser that we need to set constantly
        self._empty_lines_in_values = False

    @property
    def _curr_block(self):
        if self._structure:
            return self._structure[-1]
        else:
            return None

    def _get_section_idx(self, name):
        idx = [i for i, entry in enumerate(self._structure)
               if isinstance(entry, Section) and entry.name == name]
        if idx:
            return idx[0]
        else:
            raise ValueError

    def read(self, filename, encoding=None):
        """Read and parse a filename.

        Files that cannot be opened are silently ignored; this is
        designed so that you can specify a list of potential
        configuration file locations (e.g. current directory, user's
        home directory, systemwide directory), and all existing
        configuration files in the list will be read.  A single
        filename may also be given.

        Return list of successfully read files.
        """
        try:
            with open(filename, encoding=encoding) as fp:
                self._read(fp, filename)
        except OSError:
            read_ok = []
        else:
            # os.Pathlike objects requires Python >=3.6
            # if isinstance(filename, os.PathLike):
            #    filename = os.fspath(filename)
            read_ok = [filename]
            self._filename = filename
        return read_ok

    def read_file(self, f, source=None):
        """Like read() but the argument must be a file-like object.

        The `f' argument must be iterable, returning one line at a time.
        Optional second argument is the `source' specifying the name of the
        file being read. If not given, it is taken from f.name. If `f' has no
        `name' attribute, `<???>' is used.
        """
        if source is None:
            try:
                source = f.name
            except AttributeError:
                source = '<???>'
        self._read(f, source)

    def read_string(self, string, source='<string>'):
        """Read configuration from a given string."""
        sfile = io.StringIO(string)
        self.read_file(sfile, source)

    def optionxform(self, optionstr):
        return optionstr.lower()

    def _update_curr_block(self, block_type):
        if not isinstance(self._curr_block, block_type):
            new_block = block_type(container=self._structure)
            self._structure.append(new_block)

    def _add_comment(self, line):
        if isinstance(self._curr_block, Section):
            self._curr_block._add_comment()
            self._curr_block._curr_entry._add_line(line)
        else:
            self._update_curr_block(Comment)
            self._curr_block._add_line(line)

    def _add_section(self, sectname, line):
        new_section = Section(sectname, container=self._structure)
        new_section._add_line(line)
        self._structure.append(new_section)

    def _add_option(self, key, vi, value, line):
        entry = Option(
            key, value,
            delimiter=vi,
            container=self._curr_block._structure,
            space_around_delimiters=self._space_around_delimiters)
        entry._add_line(line)
        self._curr_block._add_option(entry)

    def _add_space(self, line):
        if isinstance(self._curr_block, Section):
            self._curr_block._add_space()
            self._curr_block._curr_entry._add_line(line)
        else:
            self._update_curr_block(Space)
            self._curr_block._add_line(line)

    def _add_entry(self, line):
        self._update_curr_block(Option)
        self._curr_block._add_line(line)

    def _read(self, fp, fpname):
        """Parse a sectioned configuration file.

        Each section in a configuration file contains a header, indicated by
        a name in square brackets (`[]'), plus key/value options, indicated by
        `name' and `value' delimited with a specific substring (`=' or `:' by
        default).

        Values can span multiple lines, as long as they are indented deeper
        than the first line of the value. Depending on the parser's mode, blank
        lines may be treated as parts of multiline values or ignored.

        Configuration files may include comments, prefixed by specific
        characters (`#' and `;' by default). Comments may appear on their own
        in an otherwise empty line or may be entered in lines holding values or
        section names.

        Note: This method was borrowed from ConfigParser and we keep this
        mess here as close as possible to the original messod (pardon
        this german pun) for consistency reasons and later upgrades.
        """
        self._structure = []
        elements_added = set()
        cursect = None                        # None, or a dictionary
        sectname = None
        optname = None
        lineno = 0
        indent_level = 0
        e = None                              # None, or an exception
        for lineno, line in enumerate(fp, start=1):
            comment_start = sys.maxsize
            # strip inline comments
            inline_prefixes = {p: -1 for p in self._inline_comment_prefixes}
            while comment_start == sys.maxsize and inline_prefixes:
                next_prefixes = {}
                for prefix, index in inline_prefixes.items():
                    index = line.find(prefix, index+1)
                    if index == -1:
                        continue
                    next_prefixes[prefix] = index
                    if index == 0 or (index > 0 and line[index-1].isspace()):
                        comment_start = min(comment_start, index)
                inline_prefixes = next_prefixes
            # strip full line comments
            for prefix in self._comment_prefixes:
                if line.strip().startswith(prefix):
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
                    if (comment_start is None and
                        cursect is not None and
                        optname and
                        cursect[optname] is not None):
                        cursect[optname].append('') # newlines added at join
                        self._curr_block._curr_entry._add_line(line)  # HOOK
                else:
                    # empty line marks end of value
                    indent_level = sys.maxsize
                if comment_start is None:
                    self._add_space(line)
                continue
            # continuation line?
            first_nonspace = self.NONSPACECRE.search(line)
            cur_indent_level = first_nonspace.start() if first_nonspace else 0
            if (cursect is not None and optname and
                cur_indent_level > indent_level):
                cursect[optname].append(value)
                self._curr_block._curr_entry._add_line(line)  # HOOK
            # a section header or option header?
            else:
                indent_level = cur_indent_level
                # is it a section header?
                mo = self.SECTCRE.match(value)
                if mo:
                    sectname = mo.group('header')
                    if sectname in self._sections:
                        if self._strict and sectname in elements_added:
                            raise DuplicateSectionError(sectname, fpname,
                                                        lineno)
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
                        optname, vi, optval = mo.group('option', 'vi', 'value')
                        if not optname:
                            e = self._handle_error(e, fpname, lineno, line)
                        optname = self.optionxform(optname.rstrip())
                        if (self._strict and
                            (sectname, optname) in elements_added):
                            raise DuplicateOptionError(sectname, optname,
                                                       fpname, lineno)
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
                    else:
                        # a non-fatal parsing error occurred. set up the
                        # exception but keep going. the exception will be
                        # raised at the end of the file and will contain a
                        # list of all bogus lines
                        e = self._handle_error(e, fpname, lineno, line)
        # if any parsing errors occurred, raise an exception
        if e:
            raise e

    def _handle_error(self, exc, fpname, lineno, line):
        if not exc:
            exc = ParsingError(fpname)
        exc.append(lineno, repr(line))
        return exc

    def write(self, fp):
        """Write an .ini-format representation of the configuration state.
        """
        fp.write(str(self))

    def update_file(self):
        """Update the read-in configuration file.
        """
        if self._filename is None:
            raise NoConfigFileReadError()
        with open(self._filename, 'w') as fb:
            self.write(fb)

    def validate_format(self, **kwargs):
        """Call ConfigParser to validate config"""
        args = dict(
            dict_type=self._dict,
            allow_no_value=self._allow_no_value,
            inline_comment_prefixes=self._inline_comment_prefixes,
            strict=self._strict,
            empty_lines_in_values=self._empty_lines_in_values
        )
        args.update(kwargs)
        parser = ConfigParser(**args)
        updated_cfg = str(self)
        parser.read_string(updated_cfg)

    def sections_blocks(self):
        return [block for block in self._structure if isinstance(block, Section)]

    def sections(self):
        """Return a list of section names"""
        return [section.name for section in self.sections_blocks()]

    def __str__(self):
        return ''.join(str(block) for block in self._structure)

    def __getitem__(self, key):
        for section in self.sections_blocks():
            if section.name == key:
                return section
        else:
            raise KeyError(key)

    # ToDo: Implement me
    def __setitem__(self, key, value):
        # To conform with the mapping protocol, overwrites existing values in
        # the section.
        # section =
        pass

    def __delitem__(self, section):
        if not self.has_section(section):
            raise KeyError(section)
        self.remove_section(section)

    def __contains__(self, key):
        return self.has_section(key)

    def __len__(self):
        """Number of all blocks, not just sections"""
        return len(self._structure)

    def __iter__(self):
        """Iterate over all blocks, not just sections"""
        return self._structure.__iter__()

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._structure == other._structure
        else:
            return False

    def add_section(self, section_name):
        """Create a new section in the configuration.

        Raise DuplicateSectionError if a section by the specified name
        already exists. Raise ValueError if name is DEFAULT.
        """
        if section_name in self.sections():
            raise DuplicateSectionError(section_name)
        section = Section(section_name, container=self._structure)
        self._structure.append(section)

    def has_section(self, section):
        """Indicate whether the named section is present in the configuration.
        """
        return section in self.sections()

    def options(self, section):
        """Return a list of option names for the given section name."""
        if not self.has_section(section):
            raise NoSectionError(section) from None
        return self.__getitem__(section).options()

    def get(self, section, option):
        """Get an option value for a given section."""
        if not self.has_section(section):
            raise NoSectionError

        section = self.__getitem__(section)
        option = self.optionxform(option)
        try:
            value = section[option]
        except KeyError:
            raise NoOptionError(option, section)

        return value

    def items(self, section=_UNSET):
        """Return a list of (name, value) tuples for each option in a section.
        """
        if section is _UNSET:
            return [(sect.name, sect) for sect in self.sections_blocks()]

        section = self.__getitem__(section)
        return [(opt.key, opt) for opt in section.option_blocks()]

    def has_option(self, section, option):
        """Check for the existence of a given option in a given section.
        If the specified `section' is None or an empty string, DEFAULT is
        assumed. If the specified `section' does not exist, returns False."""
        if section not in self.sections():
            return False
        else:
            option = self.optionxform(option)
            return option in self[section]

    def set(self, section, option, value=None):
        """Set an option."""
        try:
            section = self.__getitem__(section)
        except KeyError:
            raise NoSectionError(section) from None
        option = self.optionxform(option)
        if option in section:
            section[option].value = value
        else:
            section[option] = value

    def remove_option(self, section, option):
        """Remove an option."""
        try:
            section = self.__getitem__(section)
        except KeyError:
            raise NoSectionError(section) from None
        option = self.optionxform(option)
        existed = option in section.options()
        if existed:
            del section[option]
        return existed

    def remove_section(self, name):
        """Remove a file section."""
        existed = self.has_section(name)
        if existed:
            idx = self._get_section_idx(name)
            del self._structure[idx]
        return existed
