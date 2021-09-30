"""Core of the fluent API used by **ConfigUpdater** to make editing configuration files
easier.
"""
from configparser import DuplicateOptionError, DuplicateSectionError
from typing import TYPE_CHECKING, Optional, TypeVar, Union

if TYPE_CHECKING:
    from .block import Block
    from .container import Container
    from .section import Section

T = TypeVar("T", bound="BlockBuilder")


class BlockBuilder:
    """Builder that injects blocks at a given index position."""

    def __init__(self, container: "Container", idx: int):
        self._container = container
        self._idx = idx

    def _insert(self: T, block: "Block") -> T:
        self._container.structure.insert(self._idx, block)
        self._idx += 1
        return self

    def comment(self: T, text: str, comment_prefix="#") -> T:
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
            text = "{} {}".format(comment_prefix, text)
        if not text.endswith("\n"):
            text = "{}{}".format(text, "\n")
        return self._insert(comment.add_line(text))

    def section(self: T, section: Union[str, "Section"]) -> T:
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
            msg = "Parameter must be a string or Section type!"
            raise ValueError(msg, {"container": section})

        if container.has_section(section.name):
            raise DuplicateSectionError(section.name)

        section.attach(container)
        return self._insert(section)

    def space(self: T, newlines: int = 1) -> T:
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

    def option(self: T, key, value: Optional[str] = None, **kwargs) -> T:
        """Creates a new option inside a section

        Args:
            key (str): key of the option
            value (str or None): value of the option
            **kwargs: are passed to the constructor of :class:`Option`

        Returns:
            self for chaining
        """
        from .section import Section

        if not isinstance(self._container, Section):
            msg = "Options can only be added inside a section!"
            raise ValueError(msg, {"container": self._container})
        section = self._container
        option = section.create_option(key, value)
        if option.key in section.options():
            raise DuplicateOptionError(section.name, option.key)
        option.value = value
        return self._insert(option)
