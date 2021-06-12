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
from typing import TYPE_CHECKING, Optional, Union, cast

if sys.version_info[:2] >= (3, 9):  # pragma: no cover
    List = list
    Dict = dict
else:
    from typing import List  # pragma: no cover

if TYPE_CHECKING:
    from .section import Section

from .block import Block, Comment, Space

SectionContent = Union["Option", "Comment", "Space"]
Value = Union["Option", str]


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
        container: "Section",
        delimiter: str = "=",
        space_around_delimiters: bool = True,
        line: Optional[str] = None,
    ):
        self._container: "Section" = container
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
        return f"<Option: {self._key} = {self.value!r}>"

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
