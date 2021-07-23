"""Options are the ultimate mean of configuration inside a configuration value.

They are always associated with a :attr:`~Option.key` (or the name of the configuration
parameter) and a :attr:`~Option.value`.

Options can also have multi-line values that are usually interpreted as a list of
values.

When editing configuration files with ConfigUpdater, a handy way of setting a multi-line
(or comma separated value) for an specific option is to use the
:meth:`~Option.set_values` method.
"""
import sys
from typing import TYPE_CHECKING, Optional, TypeVar, Union, cast

if sys.version_info[:2] >= (3, 9):  # pragma: no cover
    List = list
    Dict = dict
else:
    from typing import List  # pragma: no cover

if TYPE_CHECKING:
    from .section import Section

from .block import Block

Value = Union["Option", str]
T = TypeVar("T", bound="Option")


class Option(Block):
    """Option block holding a key/value pair.

    Attributes:
        key (str): name of the key
        value (str): stored value
        updated (bool): indicates name change or a new section
    """

    def __init__(
        self,
        key: str,
        value: Optional[str] = None,
        container: Optional["Section"] = None,
        delimiter: str = "=",
        space_around_delimiters: bool = True,
        line: Optional[str] = None,
    ):
        super().__init__(container=container)
        self._key = key
        self._values: List[Optional[str]] = [] if value is None else [value]
        self._value_is_none = value is None
        self._delimiter = delimiter
        self._value: Optional[str] = None  # will be filled after join_multiline_value
        self._updated = False
        self._multiline_value_joined = False
        self._space_around_delimiters = space_around_delimiters
        if line:
            super().add_line(line)
        if value is not None:
            self.value = value

    def add_value(self, value: Optional[str]):
        """PRIVATE: this function is not part of the public API of Option.
        It is only used internally by other classes of the package during parsing.
        """
        self._value_is_none = value is None
        self._values.append(value)

    def add_line(self, line: str):
        """PRIVATE: this function is not part of the public API of Option.
        It is only used internally by other classes of the package during parsing.
        """
        super().add_line(line)
        self.add_value(line.strip())

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
        return f"<Option: {self._key} = {self.value!r}>"

    def _instantiate_copy(self: T) -> T:
        """Will be called by :meth:`Block.__deepcopy__`"""
        self._join_multiline_value()
        return self.__class__(
            self._key,
            self._value,
            container=None,
            delimiter=self._delimiter,
            space_around_delimiters=self._space_around_delimiters,
        )

    @property
    def section(self) -> "Section":
        return cast("Section", self.container)

    @property
    def key(self) -> str:
        """Key string associated with the option.

        Please notice that the option key is normalized with
        :meth:`~configupdater.document.Document.optionxform`.

        When the option object is :obj:`detached <configupdater.block.Block.detach>`,
        this method will raise a :obj:`NotAttachedError`.
        """
        return self.section.document.optionxform(self._key)

    @key.setter
    def key(self, value: str):
        self._join_multiline_value()
        self._key = value
        self._updated = True

    @property
    def raw_key(self) -> str:
        """Equivalent to :obj:`key`, but before applying :meth:`optionxform`."""
        return self._key

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
