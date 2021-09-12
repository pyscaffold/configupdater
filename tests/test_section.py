from copy import deepcopy
from textwrap import dedent

import pytest

from configupdater.block import AlreadyAttachedError, NotAttachedError
from configupdater.parser import Parser


def test_set():
    example = """\
    [options.extras_require]
    testing =   # Add here test requirements (used by tox)
        sphinx  # required for system tests
        flake8  # required for system tests
    """
    doc = Parser().read_string(dedent(example))
    section = doc["options.extras_require"]

    section.set("all", "pyscaffold")
    assert section["all"].value == "pyscaffold"

    section.set("testing", ["pyscaffoldext-markdown", "rst-to-myst"])
    assert section["testing"].value == "\n    pyscaffoldext-markdown\n    rst-to-myst"


def test_deepcopy():
    example = """\
    [options.extras_require]
    testing =   # Add here test requirements (used by tox)
        sphinx  # required for system tests
        flake8  # required for system tests
    """
    doc = Parser().read_string(dedent(example))
    other = Parser().read_string("")
    section = doc["options.extras_require"]
    option = section["testing"]
    assert option.container is section

    clone = deepcopy(section)
    with pytest.raises(NotAttachedError):  # copies should always be created detached
        assert clone.container is None

    other.add_section(clone)  # needed to be able to modify section
    assert clone.container is other

    assert str(clone) == str(section)
    assert section.container is doc

    # Make sure no side effects are felt by the original when the copy is modified
    # and vice-versa
    clone["testing"] = ""
    assert str(clone) != str(section)
    assert str(doc) == dedent(example)
    clone["testing"].add_before.option("extra_option", "extra_value")
    assert "extra_option" in clone
    assert "extra_option" not in section
    assert clone["extra_option"].container is clone

    section["testing"].add_before.option("other_extra_option", "other_extra_value")
    assert "other_extra_option" in section
    assert "other_extra_option" not in clone
    assert section["other_extra_option"].container is section

    section.add_after.comment("# new comment")
    assert "# new comment" in str(doc)
    assert "# new comment" not in str(other)

    clone.add_before.comment("# other comment")
    assert "# other comment" in str(other)
    assert "# other comment" not in str(doc)


def test_clear_error_message():
    # Make sure the error messages specify the exact object
    example = """\
    [options.extras_require]
    testing =   # Add here test requirements (used by tox)
        sphinx  # required for system tests
        flake8  # required for system tests
    """
    doc = Parser().read_string(dedent(example))
    section = doc["options.extras_require"]
    clone = deepcopy(section)
    with pytest.raises(NotAttachedError) as ex:
        clone["testing"] = ""
    assert "<Section 'options.extras_require'>" in str(ex.value)

    with pytest.raises(AlreadyAttachedError) as ex:
        section["testing"] = next(clone.iter_options())
    assert "<Option 'testing'>" in str(ex.value)
