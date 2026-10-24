"""As the main entry point of the ConfigUpdater library, this module is responsible
for combining the data layer provided by the :mod:`configupdater.document` module
and the parsing capabilities of :mod:`configupdater.parser`.

To complete the API, this module adds file handling functions, so that you can read a
configuration file from the disk, change it to your liking and save the updated
content.
"""

from __future__ import annotations

import io
from collections.abc import Iterable, Mapping
from configparser import Error
from types import MappingProxyType as ReadOnlyMapping
from typing import Any, Self, TextIO

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


class NoConfigFileReadError(Error):
    """Raised when no configuration file was read but update requested."""

    def __init__(self) -> None:
        super().__init__("No configuration file was yet read! Use .read(...) first.")


class ConfigUpdater(Document):
    """Tool to parse and modify existing ``cfg`` files.

    ConfigUpdater follows the API of ConfigParser with some differences:

      * only a single config file can be updated at a time,
      * the original case of sections and keys is kept,
      * control over the position of a new section/key.

    The following features are **deliberately not** implemented:

      * interpolation of values,
      * propagation of parameters from the default section,
      * conversion of values,
      * passing key/value pairs with the ``defaults`` argument,
      * non-strict mode allowing duplicate sections and keys.

    **ConfigUpdater** objects can be created by passing the same kind of arguments
    accepted by the :class:`Parser`. After a ConfigUpdater object is created, you can
    load some content into it by calling any of the ``read*`` methods
    (:meth:`read`, :meth:`read_file` and :meth:`read_string`).

    Once the content is loaded you can use the ConfigUpdater object more or less in the
    same way you would use a nested dictionary. Please have a look at
    :class:`Document` to understand the main differences.

    When you are done changing the configuration file, you can call the :meth:`write` or
    :meth:`update_file` method.
    """

    def __init__(
        self,
        allow_no_value: bool = False,
        *,
        delimiters: tuple[str, ...] = ("=", ":"),
        comment_prefixes: tuple[str, ...] = ("#", ";"),
        inline_comment_prefixes: tuple[str, ...] | None = None,
        strict: bool = True,
        empty_lines_in_values: bool = True,
        space_around_delimiters: bool = True,
    ) -> None:
        self._parser_opts: dict[str, Any] = {
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
        self._encoding: str | None = None
        super().__init__()

    def _instantiate_copy(self) -> Self:
        """Will be called by ``Container.__deepcopy__``"""
        clone = self.__class__(**self._parser_opts)
        clone.optionxform = self.optionxform  # type: ignore[method-assign]
        clone._filename = self._filename
        clone._encoding = self._encoding
        return clone

    def _parser(self, **kwargs: Any) -> Parser:
        opts = {"optionxform": self.optionxform, **self._parser_opts, **kwargs}
        return Parser(**opts)

    @property
    def syntax_options(self) -> Mapping[str, Any]:
        return self._syntax_options

    def read(self, filename: PathLike, encoding: str | None = None) -> Self:
        """Read and parse a filename.

        ``filename`` and ``encoding`` are remembered, so that :meth:`update_file`
        writes the file back with the encoding it was read with.

        Args:
            filename (str): path to file
            encoding (str): encoding of file, default None, i.e. the locale encoding
                (UTF-8 in UTF-8 mode) like in :func:`open`
        """
        encoding = io.text_encoding(encoding)
        self.clear()
        self._filename = filename
        self._encoding = encoding
        return self._parser().read(filename, encoding=encoding, into=self)

    def read_file(self, f: Iterable[str], source: str | None = None) -> Self:
        """Like read() but the argument must be a file-like object.

        The ``f`` argument must be iterable, returning one line at a time.
        Optional second argument is the ``source`` specifying the name of the
        file being read. If not given, it is taken from f.name. If ``f`` has no
        ``name`` attribute, ``<???>`` is used.

        If ``f`` has a ``name`` attribute, like a file opened with :func:`open`,
        :meth:`update_file` writes to this file using ``f.encoding`` (the default
        encoding if ``f`` has none). Otherwise, the file and encoding of a previous
        ``read*`` call are kept for :meth:`update_file`.

        Args:
            f: file-like object
            source (str): reference name for file object, default None
        """
        self.clear()
        if hasattr(f, "name"):
            self._filename = f.name
            self._encoding = getattr(f, "encoding", None)
        return self._parser().read_file(f, source, self)

    def read_string(self, string: str, source: str = "<string>") -> Self:
        """Read configuration from a given string.

        The file and encoding of a previous ``read*`` call are kept for
        :meth:`update_file`.

        Args:
            string (str): string containing a configuration
            source (str): reference name for file object, default '<string>'
        """
        self.clear()
        return self._parser().read_string(string, source, self)

    def write(self, fp: TextIO, validate: bool = True) -> None:
        # TODO: For Python>=3.8 instead of TextIO we can define a Writeable protocol
        """Write a .cfg/.ini-format representation of the configuration state.

        Args:
            fp (file-like object): open file handle
            validate (bool): validate format before writing
        """
        if validate:
            self.validate_format()
        fp.write(str(self))

    def update_file(self, validate: bool = True) -> Self:
        """Update the read-in configuration file.

        The file is written with the encoding it was read with, see :meth:`read` and
        :meth:`read_file`.

        Args:
            validate (bool): validate format before writing
        """
        if self._filename is None:
            raise NoConfigFileReadError()
        if validate:  # validate BEFORE opening the file!
            self.validate_format()
        encoding = io.text_encoding(self._encoding)
        with open(self._filename, "w", encoding=encoding) as fb:
            self.write(fb, validate=False)
        return self

    def validate_format(self, **kwargs: Any) -> bool:
        """Given the current state of the ``ConfigUpdater`` object (e.g. after
        modifications), validate its INI/CFG textual representation by parsing it with
        :class:`~configparser.ConfigParser`.

        The ConfigParser object is instantiated with the same arguments as the original
        ConfigUpdater object, but ``kwargs`` can be used to override them.

        See :meth:`~configupdater.document.Document.validate_format`.
        """
        return super().validate_format(**{**self._parser_opts, **kwargs})
