from copy import deepcopy
from textwrap import dedent

import pytest

from configupdater.block import NotAttachedError
from configupdater.parser import Parser


def test_deepcopy():
    example = """\
    [options.extras_require]
    testing =   # Add here test requirements (used by tox)
        sphinx  # required for system tests
        flake8  # required for system tests
    """
    doc = Parser().read_string(dedent(example))
    section = doc["options.extras_require"]
    option = section["testing"]
    assert option.container is section

    clone = deepcopy(option)

    assert str(clone) == str(option)
    assert option.container is section
    with pytest.raises(NotAttachedError):
        assert clone.container is None  # copies should always be created detached

    # Make sure no side effects are felt by the original when the copy is modified
    clone.value = ""
    assert str(clone) != str(option)
    assert str(doc) == dedent(example)
