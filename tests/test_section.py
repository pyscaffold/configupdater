from copy import deepcopy
from textwrap import dedent

import pytest

from configupdater.block import AlreadyAttachedError, NotAttachedError
from configupdater.parser import Parser


def test_add_before_skip_comments():
    doc = Parser().read_string("[first]\na = 1\n")
    doc["first"].add_after.space().comment("target comment").section("target")
    doc["target"]["b"] = "2"

    doc["target"].add_before_skip_comments.section("middle").space()
    doc["middle"]["c"] = "3"

    assert str(doc) == (
        "[first]\na = 1\n\n[middle]\nc = 3\n\n" "# target comment\n[target]\nb = 2\n"
    )
    assert doc.sections() == ["first", "middle", "target"]
    assert doc["middle"].container is doc


def test_add_before_skip_comments_multiple_comment_blocks():
    doc = Parser().read_string("[first]\n")
    doc["first"].add_after.comment("one").comment("two").section("target")
    comments = doc.structure[1:3]

    doc["target"].add_before_skip_comments.section("middle")

    assert str(doc) == "[first]\n[middle]\n# one\n# two\n[target]\n"
    assert doc.structure[2] is comments[0]
    assert doc.structure[3] is comments[1]


def test_add_before_skip_comments_stops_at_space():
    doc = Parser().read_string("[first]\n")
    (
        doc["first"]
        .add_after.comment("earlier")
        .space()
        .comment("target comment")
        .section("target")
    )

    doc["target"].add_before_skip_comments.section("middle")

    assert str(doc) == ("[first]\n# earlier\n\n[middle]\n# target comment\n[target]\n")


def test_add_before_skip_comments_leaves_previous_section_contents():
    doc = Parser().read_string("[first]\na = 1\n# first comment\n[target]\nb = 2\n")
    first = str(doc["first"])

    doc["target"].add_before_skip_comments.section("middle")

    assert str(doc) == "[first]\na = 1\n# first comment\n[middle]\n[target]\nb = 2\n"
    assert str(doc["first"]) == first


@pytest.mark.parametrize("prefix", ["", "# one\n# two\n"])
def test_add_before_skip_comments_at_document_start(prefix):
    doc = Parser().read_string(prefix + "[target]\n")

    doc["target"].add_before_skip_comments.section("first")

    assert str(doc) == "[first]\n" + prefix + "[target]\n"


def test_add_before_skip_comments_detached_section():
    section = Parser().read_string("[target]\n")["target"].detach()
    with pytest.raises(NotAttachedError):
        _ = section.add_before_skip_comments


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
