"""Core of the fluent API used by **ConfigUpdater** to make editing configuration files
easier.
"""

from __future__ import annotations

from configparser import DuplicateOptionError, DuplicateSectionError
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from .block import Block
    from .container import Container
    from .section import Section


class BlockBuilder:
    """Builder that injects blocks at a given index position."""

    def __init__(self, container: Container[Any], idx: int) -> None:
        self._container = container
        self._idx = idx

    def _insert(self, block: Block) -> Self:
        self._container.structure.insert(self._idx, block)
        self._idx += 1
        return self

    def comment(self, text: str, comment_prefix: str = "#") -> Self:
        """Creates a comment block

        Args:
            text (str): content of comment without #
            comment_prefix (str): character indicating start of comment

        Returns:
            self for chaining
        """
        from .block import Comment

        comment = Comment(self._container)
        if not text.startswith(comment_prefix):
            text = f"{comment_prefix} {text}"
        if not text.endswith("\n"):
            text = "{}{}".format(text, "\n")
        return self._insert(comment.add_line(text))

    def section(self, section: str | Section) -> Self:
        """Creates a section block

        Args:
            section (str or :class:`Section`): name of section or object

        Returns:
            self for chaining
        """
        from .document import Document
        from .section import Section

        container = self._container
        if not isinstance(container, Document):
            raise ValueError("Sections can only be added at section level!")

        if isinstance(section, str):
            # create a new section
            section = Section(section)
        elif not isinstance(section, Section):
            # Runtime check for callers that ignore the type hints
            raise ValueError(
                "Parameter must be a string or Section type!", {"container": section}
            )

        if container.has_section(section.name):
            raise DuplicateSectionError(section.name)

        section.attach(container)
        return self._insert(section)

    def space(self, newlines: int = 1) -> Self:
        """Creates a vertical space of newlines

        Args:
            newlines (int): number of empty lines

        Returns:
            self for chaining
        """
        from .block import Space

        space = Space(container=self._container)
        for _ in range(newlines):
            space.add_line("\n")
        return self._insert(space)

    def option(
        self,
        key: str,
        value: str | None = None,
        *,
        delimiter: str | None = None,
        space_around_delimiters: bool | None = None,
    ) -> Self:
        """Creates a new option inside a section

        Args:
            key (str): key of the option
            value (str or None): value of the option
            delimiter (str or None): delimiter between key and value, by default
                the first of the ``delimiters`` given to
                :class:`~configupdater.ConfigUpdater`
            space_around_delimiters (bool or None): surround the delimiter with
                spaces, by default as given to :class:`~configupdater.ConfigUpdater`.

        Returns:
            self for chaining
        """
        from .section import Section

        if not isinstance(self._container, Section):
            msg = "Options can only be added inside a section!"
            raise ValueError(msg, {"container": self._container})
        section = self._container
        option = section.create_option(
            key,
            value,
            delimiter=delimiter,
            space_around_delimiters=space_around_delimiters,
        )
        if option.key in section.options():
            raise DuplicateOptionError(section.name, option.key)
        option.value = value
        return self._insert(option)
