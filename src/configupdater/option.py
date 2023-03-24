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
import warnings
from typing import TYPE_CHECKING, Any, Optional, TypeVar, Union, cast

if sys.version_info[:2] >= (3, 9):  # pragma: no cover
    from collections.abc import Iterable

    List = list
    Dict = dict
else:  # pragma: no cover
    from typing import Iterable, List

if TYPE_CHECKING:
    from .section import Section
    from .document import Document

from .block import AssignMultilineValueError, Block

Value = Union["Option", str]
T = TypeVar("T", bound="Option")


def is_multi_line(value: Any) -> bool:
    """Checks if a given value has multiple lines"""
    if isinstance(value, str):
        return "\n" in value
    else:
        return False


class NoneValueDisallowed(SyntaxWarning):
    """Cannot represent <{option} = None>, it will be converted to <{option} = ''>.
    Please use ``allow_no_value=True`` with ``ConfigUpdater``.
    """

    @classmethod
    def warn(cls, option):
        warnings.warn(cls.__doc__.format(option=option), cls, stacklevel=2)


class Option(Block):
    """Option block holding a key/value pair."""

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
            self._set_value(value)

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

    def _get_delim(self, determine_suffix=True) -> str:
        document = self._document()
        opts = getattr(document, "syntax_options", None) or {}
        value = self._value
        space = self._space_around_delimiters or opts.get("space_around_delimiters")
        if determine_suffix and str(value).startswith("\n"):
            suffix = ""  # no space is needed if we use multi-line arguments
        else:
            suffix = " "
        delim = f" {self._delimiter}{suffix}" if space else self._delimiter
        return delim

    def value_start_idx(self) -> int:
        """Index where the value of the option starts, good for indentation"""
        delim = self._get_delim(determine_suffix=False)
        return len(f"{self._key}{delim}")

    def __str__(self) -> str:
        if not self.updated:
            return super().__str__()

        document = self._document()
        opts = getattr(document, "syntax_options", None) or {}
        value = self._value

        if value is None:
            if document is None or opts.get("allow_no_value"):
                return f"{self._key}\n"
            NoneValueDisallowed.warn(self._key)
            return ""

        delim = self._get_delim()
        return f"{self._key}{delim}{value}\n"

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

    def _document(self) -> Optional["Document"]:
        if self._container is None:
            return None
        return self._container._container  # type: ignore

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
        """Value associated with the given option."""
        self._join_multiline_value()
        return self._value

    @value.setter
    def value(self, value: str):
        if is_multi_line(value):
            raise AssignMultilineValueError(self)
        self._set_value(value)

    def _set_value(self, value: str):
        self._updated = True
        self._multiline_value_joined = True
        self._value = value
        self._values = [value]

    def as_list(self, separator="\n") -> List[str]:
        """Returns the (multi-line/element) value as a list

        Empty list if value is None, single-element list for a one-element
        value and an element for each line in a multi-element value.

        Args:
            separator (str): separator for values, default: line separator
        """
        if self._value_is_none:
            return []
        else:
            return [v.strip() for v in cast(str, self.value).strip().split(separator)]

    def append(self, value: str, **kwargs) -> "Option":
        """Append a value to a mult-line value

        Args:
            value (str): value
            kwargs: keyword arguments for `set_values`
        """
        sep = kwargs.get("separator", None)
        if sep is None:
            new_values = self.as_list()
        else:
            new_values = self.as_list(separator=sep)

        new_values.append(value)
        self.set_values(new_values, **kwargs)
        return self

    def set_values(
        self,
        values: Iterable[str],
        separator="\n",
        indent: Optional[str] = None,
        prepend_newline=True,
    ):
        """Sets the value to a given list of options, e.g. multi-line values

        Args:
            values (iterable): sequence of values
            separator (str): separator for values, default: line separator
            indent (optional str): indentation in case of line separator.
                If prepend_newline is `True` 4 whitespaces by default, otherwise
                determine automatically if `None`.
            prepend_newline (bool): start with a new line or not, resp.
        """
        values = list(values).copy()
        self._updated = True
        self._multiline_value_joined = True
        self._values = cast(List[Optional[str]], values)

        if indent is None:
            if prepend_newline:
                indent = 4 * " "
            else:
                indent = self.value_start_idx() * " "

        # The most common case of multiline values being preceded by a new line
        if prepend_newline and "\n" in separator:
            values = [""] + values
            separator = separator + indent
        elif "\n" in separator:
            separator = separator + indent

        self._value = separator.join(values)
