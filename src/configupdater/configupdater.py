import io
import os
import sys
from configparser import Error
from typing import Optional, TextIO, Tuple, Union, cast

if sys.version_info[:2] >= (3, 9):
    from collections.abc import Iterable, MutableMapping

    List = list
    Dict = dict
else:
    from typing import Iterable, MutableMapping


class NoConfigFileReadError(Error):
    """Raised when no configuration file was read but update requested."""

    def __init__(self):
        super().__init__("No configuration file was yet read! Use .read(...) first.")


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
        pass

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
