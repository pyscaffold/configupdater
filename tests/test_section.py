from configparser import ConfigParser
from copy import deepcopy
from textwrap import dedent

import pytest

from configupdater import ConfigUpdater
from configupdater.block import AlreadyAttachedError, NotAttachedError
from configupdater.parser import Parser


def test_add_before_skip_comments():
    doc = Parser().read_string("[first]\na = 1\n")
    doc["first"].add_after.space().comment("target comment").section("target")
    doc["target"]["b"] = "2"

    doc["target"].add_before_skip_comments.section("middle").space()
    doc["middle"]["c"] = "3"

    assert str(doc) == (
        "[first]\na = 1\n\n[middle]\nc = 3\n\n# target comment\n[target]\nb = 2\n"
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


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize(
    "body",
    [
        "",
        "key : value",
        "key : value{nl}",
        "# tail",
        "key = one{nl}  two",
        "key = v{nl}  ",
    ],
)
@pytest.mark.parametrize(
    "method", ["assignment", "set", "document_set", "update", "add_option"]
)
def test_append_option_no_trailing_newline(newline, body, method):
    original = "[s]" + (newline + body.format(nl=newline) if body else "")
    updater = ConfigUpdater().read_string(original)
    assert str(updater) == original
    expected = ConfigParser(interpolation=None)
    expected.read_string(original)
    expected.set("s", "new_key", "v")
    section = updater["s"]
    previous_blocks = [(block, str(block)) for block in section.structure]

    if method == "assignment":
        section["new_key"] = "v"
    elif method == "set":
        section.set("new_key", "v")
    elif method == "document_set":
        updater.set("s", "new_key", "v")
    elif method == "update":
        section.update({"new_key": "v"})
    else:
        assert section.add_option(section.create_option("new_key", "v")) is section

    result = str(updater)
    assert (
        result == original + ("" if original.endswith("\n") else "\n") + "new_key = v\n"
    )
    actual = ConfigParser(interpolation=None)
    actual.read_string(result)
    assert dict(actual["s"]) == dict(expected["s"])
    assert all(str(block) == raw for block, raw in previous_blocks)
    assert section["new_key"].container is section
    updater.validate_format()


@pytest.mark.parametrize("method", ["assignment", "add_option"])
def test_append_attached_option_leaves_target_unchanged(method):
    updater = ConfigUpdater().read_string("[s]\nkey : value")
    source = ConfigUpdater().read_string("[other]\nnew_key = v")
    option = source["other"]["new_key"]
    section = updater["s"]
    original = str(updater)
    blocks = tuple(section.structure)
    if method == "assignment":
        with pytest.raises(AlreadyAttachedError, match="already attached"):
            section["new_key"] = option
    else:
        with pytest.raises(AlreadyAttachedError, match="already attached"):
            section.add_option(option)
    assert str(updater) == original
    assert len(section.structure) == len(blocks)
    assert all(a is b for a, b in zip(section.structure, blocks, strict=True))
    assert option.container is source["other"]
    assert str(source) == "[other]\nnew_key = v"


@pytest.mark.parametrize("copy_option", [False, True])
def test_append_detached_option_without_trailing_newline(copy_option):
    updater = ConfigUpdater().read_string("[s]\nkey : value")
    source = ConfigUpdater().read_string("[other]\nnew_key = v")
    option = source["other"]["new_key"]
    option = deepcopy(option) if copy_option else option.detach()
    updater["s"]["new_key"] = option
    assert updater["s"]["new_key"] is option
    assert option.container is updater["s"]
    assert str(updater) == "[s]\nkey : value\nnew_key = v"
