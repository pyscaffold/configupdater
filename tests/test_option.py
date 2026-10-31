from configparser import ConfigParser
from copy import deepcopy
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
    with pytest.warns(
        NoneValueDisallowed, match="<namespace = None>, the option is omitted"
    ):
        assert str(cfg["pyscaffold"]["namespace"]) == ""


def test_str_for_set_values():
    opt = Option("opt")
    opt.set_values("1234", separator=", ")
    assert str(opt) == "opt = 1, 2, 3, 4\n"


@pytest.mark.parametrize("separator", ["\n", ", "])
@pytest.mark.parametrize("prepend_newline", [True, False])
def test_as_list_and_append_after_setting_valueless_option(separator, prepend_newline):
    source = "# keep comment\n[build]\nplugins\nother : unchanged\n"
    cfg = ConfigUpdater(allow_no_value=True, delimiters=(":",)).read_string(source)
    option = cfg["build"]["plugins"]
    assert option.as_list() == []
    assert str(cfg) == source
    kwargs = {"separator": separator, "prepend_newline": prepend_newline}
    option.set_values(["alpha", "beta"], **kwargs)
    assert option.as_list(separator) == ["alpha", "beta"]
    for value in ["gamma", "delta"]:
        option.append(value, **kwargs)
    assert option.as_list(separator) == ["alpha", "beta", "gamma", "delta"]
    output = StringIO()
    cfg.write(output)
    assert output.getvalue().startswith("# keep comment\n[build]\nplugins :")
    assert output.getvalue().endswith("other : unchanged\n")
    parser = ConfigParser(allow_no_value=True, delimiters=(":",))
    parser.read_string(output.getvalue())
    expected = separator.join(["alpha", "beta", "gamma", "delta"])
    if separator == "\n" and prepend_newline:
        expected = "\n" + expected
    assert parser["build"]["plugins"] == expected


@pytest.mark.parametrize("initial", ["plugins", "plugins = alpha"])
def test_as_list_after_scalar_assignment(initial):
    cfg = ConfigUpdater(allow_no_value=True).read_string(f"[build]\n{initial}\n")
    option = cfg["build"]["plugins"]
    parser = ConfigParser(allow_no_value=True)
    parser.read_string(f"[build]\n{initial}\n")
    for value in [None, "", "beta", None, "gamma"]:
        option.value = value
        assert option.as_list() == ([] if value is None else [value])
        parser.set("build", "plugins", value)
        output = StringIO()
        cfg.write(output)
        reparsed = ConfigParser(allow_no_value=True)
        reparsed.read_string(output.getvalue())
        assert dict(reparsed["build"]) == dict(parser["build"])
    option.value = None
    option.append("delta")
    option.append("epsilon")
    assert option.as_list() == ["delta", "epsilon"]


@pytest.mark.parametrize("initial", [None, "alpha"])
def test_as_list_after_setting_empty_values(initial):
    option = Option("plugins", initial)
    option.set_values([])
    assert option.value == ""
    assert option.as_list() == [""]
    assert str(option) == "plugins = \n"


def test_append_to_new_valueless_option():
    option = Option("plugins")
    assert option.as_list() == []
    option.append("alpha")
    option.append("beta")
    assert option.as_list() == ["alpha", "beta"]


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


@pytest.mark.parametrize("spaces", [True, False])
def test_explicit_space_around_delimiters_takes_precedence(spaces):
    cfg = ConfigUpdater(space_around_delimiters=not spaces)
    cfg.read_string("[section]\nkey0 = 0\n")
    section = cfg["section"]
    section["key1"] = Option("key1", "1", space_around_delimiters=spaces)
    section["key1"].add_after.option("key2", "2", space_around_delimiters=spaces)
    section.add_option(
        section.create_option("key3", "3", space_around_delimiters=spaces)
    )
    delim = " = " if spaces else "="
    lines = [f"key{i}{delim}{i}\n" for i in (1, 2, 3)]
    assert str(cfg) == "[section]\nkey0 = 0\n" + "".join(lines)
    # The option keeps its setting when it is copied
    assert str(deepcopy(section["key1"])) == lines[0]
    parser = ConfigParser()
    parser.read_string(str(cfg))
    assert dict(parser["section"]) == {f"key{i}": str(i) for i in range(4)}


def test_space_around_delimiters_false_in_default_updater():
    cfg = ConfigUpdater().read_string("[section]\nkey0 = 0\n")
    section = cfg["section"]
    section["key1"] = Option("key1", "1", space_around_delimiters=False)
    section["key0"].add_after.option("key2", "2", space_around_delimiters=False)
    assert str(cfg) == "[section]\nkey0 = 0\nkey2=2\nkey1=1\n"


@pytest.mark.parametrize("spaces", [True, False])
def test_options_without_explicit_spaces_follow_the_document(spaces):
    cfg = ConfigUpdater(space_around_delimiters=spaces).read_string("[section]\n")
    section = cfg["section"]
    section["key1"] = Option("key1", "1")
    section["key1"].add_after.option("key2", "2")
    section["key3"] = "3"
    delim = " = " if spaces else "="
    assert str(cfg) == "[section]\n" + "".join(f"key{i}{delim}{i}\n" for i in (1, 2, 3))
    # A copy follows the document it is moved to and uses spaces when orphaned
    other = ConfigUpdater(space_around_delimiters=not spaces).read_string("[section]")
    for key in section:
        other["section"][key] = deepcopy(section[key])
    other_delim = "=" if spaces else " = "
    assert str(other) == "[section]\n" + "".join(
        f"key{i}{other_delim}{i}\n" for i in (1, 2, 3)
    )
    assert str(deepcopy(section["key1"])) == "key1 = 1\n"


def test_parsed_option_keeps_parser_spaces_when_copied():
    doc = Parser(space_around_delimiters=False).read_string("[section]\nkey=1\n")
    cfg = ConfigUpdater().read_string("[section]\n")
    cfg["section"]["key"] = deepcopy(doc["section"]["key"])
    cfg["section"]["key"].value = "2"
    assert str(cfg) == "[section]\nkey=2\n"
    assert str(doc) == "[section]\nkey=1\n"
