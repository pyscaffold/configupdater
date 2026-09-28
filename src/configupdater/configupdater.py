"""As the main entry point of the ConfigUpdater library, this module is responsible
for combining the data layer provided by the :mod:`configupdater.document` module
and the parsing capabilities of :mod:`configupdater.parser`.

To complete the API, this module adds file handling functions, so that you can read a
configuration file from the disk, change it to your liking and save the updated
content.
"""

import sys
from configparser import Error
from types import MappingProxyType as ReadOnlyMapping
from typing import TextIO, TypeVar

if sys.version_info[:2] >= (3, 9):  # pragma: no cover
    from collections.abc import Iterable, Mapping

    List = list
    Dict = dict
else:  # pragma: no cover
    from collections.abc import Iterable, Mapping

from typing_extensions import Self

from .block import (
    AlreadyAttachedError,
    AssignMultilineValueError,
    Comment,
    NotAttachedError,
    Space,
)
from .document import Document
from .option import NoneValueDisallowed, Option
from .parser import Parser, PathLike
from .section import Section

__all__ = [
    "AlreadyAttachedError",
    "AssignMultilineValueError",
    "Comment",
    "ConfigUpdater",
    "NoConfigFileReadError",
    "NoneValueDisallowed",
    "NotAttachedError",
    "Option",
    "Parser",
    "Section",
    "Space",
]

T = TypeVar("T", bound="ConfigUpdater")


class NoConfigFileReadError(Error):
    """Raised when no configuration file was read but update requested."""

    def __init__(self):
        super().__init__("No configuration file was yet read! Use .read(...) first.")


class ConfigUpdater(Document):
    """Tool to parse and modify existing ``cfg`` files.

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

    **ConfigUpdater** objects can be created by passing the same kind of arguments
    accepted by the :class:`Parser`. After a ConfigUpdater object is created, you can
    load some content into it by calling any of the ``read*`` methods
    (:meth:`read`, :meth:`read_file` and :meth:`read_string`).

    Once the content is loaded you can use the ConfigUpdater object more or less in the
    same way you would use a nested dictionary. Please have a look into
    :class:`Document` to understand the main differences.

    When you are done changing the configuration file, you can call :meth:`write` or
    :meth:`update_file` methods.
    """

    def __init__(
        self,
        allow_no_value=False,
        *,
        delimiters: tuple[str, ...] = ("=", ":"),
        comment_prefixes: tuple[str, ...] = ("#", ";"),
        inline_comment_prefixes: tuple[str, ...] | None = None,
        strict: bool = True,
        empty_lines_in_values: bool = True,
        space_around_delimiters: bool = True,
    ):
        self._parser_opts = {
            "allow_no_value": allow_no_value,
            "delimiters": delimiters,
            "comment_prefixes": comment_prefixes,
            "inline_comment_prefixes": inline_comment_prefixes,
            "strict": strict,
            "empty_lines_in_values": empty_lines_in_values,
            "space_around_delimiters": space_around_delimiters,
        }
        self._syntax_options = ReadOnlyMapping(self._parser_opts)
        self._filename: PathLike | None = None
        super().__init__()

    def _instantiate_copy(self) -> Self:
        """Will be called by ``Container.__deepcopy__``"""
        clone = self.__class__(**self._parser_opts)
        clone.optionxform = self.optionxform  # type: ignore[method-assign]
        clone._filename = self._filename
        return clone

    def _parser(self, **kwargs):
        opts = {"optionxform": self.optionxform, **self._parser_opts, **kwargs}
        return Parser(**opts)

    @property
    def syntax_options(self) -> Mapping:
        return self._syntax_options

    def read(self, filename: PathLike, encoding: str | None = None) -> Self:
        """Read and parse a filename.

        Args:
            filename (str): path to file
            encoding (str): encoding of file, default None
        """
        self.clear()
        self._filename = filename
        return self._parser().read(filename, encoding, self)

    def read_file(self, f: Iterable[str], source: str | None = None) -> Self:
        """Like read() but the argument must be a file-like object.

        The ``f`` argument must be iterable, returning one line at a time.
        Optional second argument is the ``source`` specifying the name of the
        file being read. If not given, it is taken from f.name. If ``f`` has no
        ``name`` attribute, ``<???>`` is used.

        Args:
            f: file like object
            source (str): reference name for file object, default None
        """
        self.clear()
        if hasattr(f, "name"):
            self._filename = f.name
        return self._parser().read_file(f, source, self)

    def read_string(self, string: str, source="<string>") -> Self:
        """Read configuration from a given string.

        Args:
            string (str): string containing a configuration
            source (str): reference name for file object, default '<string>'
        """
        self.clear()
        return self._parser().read_string(string, source, self)

    def write(self, fp: TextIO, validate: bool = True):
        # TODO: For Python>=3.8 instead of TextIO we can define a Writeable protocol
        """Write an .cfg/.ini-format representation of the configuration state.

        Args:
            fp (file-like object): open file handle
            validate (Boolean): validate format before writing
        """
        if validate:
            self.validate_format()
        fp.write(str(self))

    def update_file(self, validate: bool = True) -> Self:
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
        return self

    def validate_format(self, **kwargs):
        """Given the current state of the ``ConfigUpdater`` object (e.g. after
        modifications), validate its INI/CFG textual representation by parsing it with
        :class:`~configparser.ConfigParser`.

        The ConfigParser object is instead with the same arguments as the original
        ConfigUpdater object, but the ``kwargs`` can be used to overwrite them.

        See :meth:`~configupdater.document.Document.validate_format`.
        """
        return super().validate_format(**{**self._parser_opts, **kwargs})
