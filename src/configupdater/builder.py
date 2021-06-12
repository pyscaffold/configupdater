from configparser import DuplicateOptionError, DuplicateSectionError
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from .container import Container

T = TypeVar("T", bound="BlockBuilder")


class BlockBuilder:
    """Builder that injects blocks at a given index position."""

    def __init__(self, container: "Container", idx: int):
        self._container = container
        self._idx = idx

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
        comment.add_line(text)
        self._container.structure.insert(self._idx, comment)
        self._idx += 1
        return self

    def section(self: T, section) -> T:
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
            section = Section(section, container=container)
        elif not isinstance(section, Section):
            raise ValueError("Parameter must be a string or Section type!")

        if container.has_section(section.name):
            raise DuplicateSectionError(section.name)

        self._container.structure.insert(self._idx, section)
        self._idx += 1
        return self

    def space(self: T, newlines=1) -> T:
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
        self._container.structure.insert(self._idx, space)
        self._idx += 1
        return self

    def option(self: T, key, value=None, **kwargs) -> T:
        """Creates a new option inside a section

        Args:
            key (str): key of the option
            value (str or None): value of the option
            **kwargs: are passed to the constructor of :class:`Option`

        Returns:
            self for chaining
        """
        from .option import Option
        from .section import Section

        if not isinstance(self._container, Section):
            raise ValueError("Options can only be added inside a section!")
        option = Option(key, value, container=self._container, **kwargs)
        if option.key in self._container.options():
            raise DuplicateOptionError(self._container.name, option.key)
        option.value = value
        self._container.structure.insert(self._idx, option)
        self._idx += 1
        return self
