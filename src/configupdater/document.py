"""This module focus in the top level data layer API of ConfigUpdater, i.e.
how to access and modify the sections of the configurations.

Differently from :mod:`configparser`, the different aspects of the ConfigUpdater API are
split between several modules.
"""
import sys
from configparser import (
    ConfigParser,
    DuplicateSectionError,
    NoOptionError,
    NoSectionError,
)
from enum import Enum
from typing import Optional, Tuple, TypeVar, Union, overload

if sys.version_info[:2] >= (3, 9):  # pragma: no cover
    from collections.abc import Iterable, Iterator, MutableMapping

    List = list
    Dict = dict
else:  # pragma: no cover
    from typing import Dict, Iterable, Iterator, List, MutableMapping

from .block import Comment, Space
from .container import Container
from .option import Option
from .section import Section

# Used in parser getters to indicate the default behaviour when a specific
# option is not found it to raise an exception. Created to enable 'None' as
# a valid fallback value.
_UniqueValues = Enum("UniqueValues", "_UNSET")
_UNSET = _UniqueValues._UNSET

T = TypeVar("T")
D = TypeVar("D", bound="Document")

ConfigContent = Union["Section", "Comment", "Space"]
Value = Union["Option", str]


class Document(Container[ConfigContent], MutableMapping[str, Section]):
    """Access to the data manipulation API from **ConfigUpdater**.

    A ``Document`` object tries to implement a familiar *dict-like* interface,
    via :class:`MutableMapping`. However, it also tries to be as compatible as possible
    with the stdlib's :class:`~configparser.ConfigParser`. This means that there are a
    few methods that will work differently from what users familiar with *dict-like*
    interfaces would expect. The most notable example is :meth:`get`.

    A important difference between ConfigUpdater's ``Document`` model and
    :class:`~configparser.ConfigParser` is the behaviour of the :class:`Section`
    objects.
    If we represent the type of a *dict-like* (or :class:`MutableMapping`) object by
    ``M[K, V]``, where ``K`` is the type of its keys and ``V`` is the type of the
    associated values, ConfigUpdater's sections would be equivalent to
    ``M[str, Option]``, while ConfigParser's would be ``M[str, str]``.

    This means that when you try to access a key inside a section in ConfigUpdater, you
    are going to receive a :class:`Option` object, not its value.
    To access the value of the option you need to call :class:`Option.value`.
    """

    def _get_section_idx(self, name: str) -> int:
        return next(
            i
            for i, entry in enumerate(self._structure)
            if isinstance(entry, Section) and entry.name == name
        )

    def optionxform(self, optionstr) -> str:
        """Converts an option key for unification

        By default it uses :meth:`str.lower`, which means that ConfigUpdater will
        compare options in a case insensitive way.

        This implementation mimics ConfigParser API, and can be configured as described
        in :meth:`configparser.ConfigParser.optionxform`.

        Args:
             optionstr (str): key name

        Returns:
            str: unified option name
        """
        return optionstr.lower()

    def validate_format(self, **kwargs):
        """Call ConfigParser to validate config

        Args:
            kwargs: are passed to :class:`configparser.ConfigParser`

        Raises:
            configparser.ParsingError: if syntax errors are found

        Returns:
            ``True`` when no error is found
        """
        kwargs.pop("space_around_delimiters", None)
        parser = ConfigParser(**kwargs)
        parser.read_string(str(self))
        return True

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

    def __iter__(self) -> Iterator[str]:
        return (b.name for b in self.iter_blocks() if isinstance(b, Section))

    def __str__(self) -> str:
        return "".join(str(block) for block in self._structure)

    def __getitem__(self, key) -> Section:
        for section in self.section_blocks():
            if section.name == key:
                return section

        raise KeyError(f"No section `{key}` found", {"key": key})

    def __setitem__(self, key: str, value: Section):
        if not isinstance(value, Section):
            raise ValueError("Value must be of type Section!")
        if isinstance(key, str) and key in self:
            idx = self._get_section_idx(key)
            self.__getitem__(key).detach()
            value.attach(self)
            self._structure.insert(idx, value)
        else:
            if value.name != key:
                raise ValueError(
                    f"Set key `{key}` does not equal option key `{value.name}`"
                )
            self.add_section(value)

    def __delitem__(self, key: str):
        if not self.remove_section(key):
            raise KeyError(f"No section `{key}` found", {"key": key})

    # MutableMapping[str, Section] for some reason accepts key: object
    # it actually doesn't matter for the implementation, so we omit the typing
    def __contains__(self, key) -> bool:
        """Returns whether the given section exists.

        Args:
            key (str): name of section

        Returns:
            bool: wether the section exists
        """
        return next((True for s in self.iter_sections() if s.name == key), False)

    has_section = __contains__

    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__):
            return self._structure == other._structure
        else:
            return False

    def clear(self):
        for block in self._structure:
            block.detach()
        self._structure.clear()

    def add_section(self, section: Union[str, Section]):
        """Create a new section in the configuration.

        Raise DuplicateSectionError if a section by the specified name
        already exists. Raise ValueError if name is DEFAULT.

        Args:
            section (str or :class:`Section`): name or Section type
        """
        if isinstance(section, str):
            # create a new section
            section_obj = Section(section)
        elif isinstance(section, Section):
            section_obj = section
        else:
            raise ValueError("Parameter must be a string or Section type!")

        if self.has_section(section_obj.name):
            raise DuplicateSectionError(section_obj.name)

        section_obj.attach(self)
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

    # The following is a pragmatic violation of Liskov substitution principle:
    # As dicts, Mappings should have get(self, key: str, default: T) -> T
    # but ConfigParser overwrites it and uses the function to offer a different
    # functionality
    @overload  # type: ignore[override]
    def get(self, section: str, option: str) -> Option:
        ...

    @overload
    def get(self, section: str, option: str, fallback: T) -> Union[Option, T]:  # noqa
        ...

    def get(self, section, option, fallback=_UNSET):  # noqa
        """Gets an option object for a given section or a fallback value.

        Warning:
            Please notice this method works differently from what is expected of
            :meth:`MutableMapping.get` (or :meth:`dict.get`).
            Similarly to :meth:`configparser.ConfigParser.get`, will take least 2
            arguments, and the second argument does not correspond to a default value.

            This happens because this function is not designed to return a
            :obj:`Section` of the :obj:`ConfigUpdater` document, but instead a nested
            :obj:`Option`.

            See :meth:`get_section`, if instead, you want to retrieve a :obj:`Section`.

        Args:
            section (str): section name
            option (str): option name
            fallback (T): if the key is not found and fallback is provided, the
              ``fallback`` value will be returned. ``None`` is a valid fallback value.

        .. attention::
            When ``option`` is not present, the ``fallback`` value itself is
            returned. If you want instead to obtain a new ``Option`` object
            with a default value associated with it, you can try the following::

                configupdater.get("section", "option", fallback=Option("name", value))

            ... which roughly corresponds to::

                configupdater["section"].get("option", Option("name", value))


        Raises:
            :class:`NoSectionError`: if ``section`` cannot be found
            :class:`NoOptionError`: if the option cannot be found and no ``fallback``
                was given

        Returns:
            :class:`Option` object holding key/value pair when it exists.  Otherwise,
            the value passed via the ``fallback`` argument itself (type ``T``).
        """
        section_obj = self.get_section(section, _UNSET)
        if section_obj is _UNSET:
            raise NoSectionError(section) from None

        option = self.optionxform(option)
        value = section_obj.get(option, fallback)
        # ^  we checked section_obj against _UNSET, so we are sure about its type

        if value is _UNSET:
            raise NoOptionError(option, section)

        return value

    @overload
    def get_section(self, name: str) -> Optional[Section]:
        ...

    @overload
    def get_section(self, name: str, default: T) -> Union[Section, T]:
        ...

    def get_section(self, name, default=None):
        """This method works similarly to :meth:`dict.get`, and allows you
        to retrieve an entire section by its name, or provide a ``default`` value in
        case it cannot be found.
        """
        return next((s for s in self.iter_sections() if s.name == name), default)

    # The following is a pragmatic violation of Liskov substitution principle
    # For some reason MutableMapping.items return a Set-like object
    # but we want to preserve ordering
    @overload  # type: ignore[override]
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
        return key in self.get_section(section, {})

    def set(
        self: D,
        section: str,
        option: str,
        value: Union[None, str, Iterable[str]] = None,
    ) -> D:
        """Set an option.

        Args:
            section: section name
            option: option name
            value: value, default None
        """
        try:
            section_obj = self.__getitem__(section)
        except KeyError:
            raise NoSectionError(section) from None
        option = self.optionxform(option)
        section_obj.set(option, value)
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
        try:
            idx = self._get_section_idx(name)
            del self._structure[idx]
            return True
        except StopIteration:
            return False

    def to_dict(self) -> Dict[str, Dict[str, Optional[str]]]:
        """Transform to dictionary

        Returns:
            dict: dictionary with same content
        """
        return {sect.name: sect.to_dict() for sect in self.iter_sections()}
