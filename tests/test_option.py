from copy import deepcopy
from configparser import ConfigParser
from io import StringIO
from textwrap import dedent

import pytest

from configupdater.block import NotAttachedError
from configupdater.configupdater import ConfigUpdater
from configupdater.option import NoneValueDisallowed, Option
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


def test_str_for_none_value():
    assert str(Option("namespace")) == "namespace\n"  # orphan option

    cfg = ConfigUpdater(allow_no_value=True).read_string("[pyscaffold]")
    cfg.set("pyscaffold", "namespace")
    assert str(cfg["pyscaffold"]["namespace"]) == "namespace\n"

    cfg = ConfigUpdater(allow_no_value=False).read_string("[pyscaffold]")
    cfg.set("pyscaffold", "namespace")
    with pytest.warns(NoneValueDisallowed):
        assert str(cfg["pyscaffold"]["namespace"]) == ""


def test_str_for_set_values():
    opt = Option("opt")
    opt.set_values("1234", separator=", ")
    assert str(opt) == "opt = 1, 2, 3, 4\n"


@pytest.mark.parametrize("delimiters", [("=", ":"), (":", "="), ("=>", ":"), ":="])
@pytest.mark.parametrize("spaces", [True, False])
def test_assign_value_to_parsed_no_value_option(delimiters, spaces):
    source = "# keep comment\n[options]\nColor\n\nOther : unchanged\n"
    cfg = ConfigUpdater(
        allow_no_value=True,
        delimiters=delimiters,
        space_around_delimiters=spaces,
    ).read_string(source)
    assert str(cfg) == source
    delimiter = f" {delimiters[0]} " if spaces else delimiters[0]
    for value in [None, "", "yes", None, "no"]:
        cfg["options"]["Color"] = value
        line = "Color\n" if value is None else f"Color{delimiter}{value}\n"
        output = StringIO()
        cfg.write(output)
        assert output.getvalue() == source.replace("Color\n", line)
        parser = ConfigParser(allow_no_value=True, delimiters=delimiters)
        parser.read_string(output.getvalue())
        assert dict(parser["options"]) == {"color": value, "other": "unchanged"}


@pytest.mark.parametrize("prepend_newline", [True, False])
def test_set_multiline_values_on_parsed_no_value_option(prepend_newline):
    cfg = ConfigUpdater(allow_no_value=True, delimiters=(":",)).read_string(
        "[options]\nColor\n"
    )
    cfg["options"]["Color"].set_values(["red", "blue"], prepend_newline=prepend_newline)
    expected = (
        "Color :\n    red\n    blue\n"
        if prepend_newline
        else "Color : red\n        blue\n"
    )
    assert str(cfg) == "[options]\n" + expected
    parser = ConfigParser(delimiters=(":",))
    parser.read_string(str(cfg))
    assert parser["options"]["color"] == (
        "\nred\nblue" if prepend_newline else "red\nblue"
    )


def test_no_value_option_keeps_parser_delimiter_when_copied():
    doc = Parser(allow_no_value=True, delimiters=(":",)).read_string(
        "[options]\nColor\n"
    )
    clone = deepcopy(doc["options"]["Color"])
    clone.value = "yes"
    assert str(clone) == "Color : yes\n"
    assert str(doc) == "[options]\nColor\n"


def test_existing_option_keeps_its_delimiter_after_assignment():
    cfg = ConfigUpdater(delimiters=("=", ":")).read_string("[options]\nColor : red\n")
    cfg["options"]["Color"] = "blue"
    assert str(cfg) == "[options]\nColor : blue\n"
