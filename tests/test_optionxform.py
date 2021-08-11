from textwrap import dedent

import pytest

from configupdater import ConfigUpdater


def test_stdlib_docs_compatibility():
    """Make sure optionxform works as documented in the stdlib docs (ConfigParser)"""
    config = """\
    [Section1]
    Key = Value

    [Section2]
    AnotherKey = Value
    """

    typical = ConfigUpdater()
    typical.read_string(dedent(config))
    assert list(typical["Section1"].keys()) == ["key"]
    assert list(typical["Section2"].keys()) == ["anotherkey"]

    custom = ConfigUpdater()
    custom.optionxform = lambda option: option
    custom.read_string(dedent(config))
    assert list(custom["Section1"].keys()) == ["Key"]
    assert list(custom["Section2"].keys()) == ["AnotherKey"]

    other = ConfigUpdater()
    other.optionxform = str
    other.read_string(dedent(config))
    assert list(other["Section1"].keys()) == ["Key"]
    assert list(other["Section2"].keys()) == ["AnotherKey"]


def test_custom():
    config = """\
    [section1]
    k_e_y = value
    """

    custom = ConfigUpdater()
    custom.optionxform = lambda option: option.replace("_", "")
    custom.read_string(dedent(config))
    assert list(custom["section1"].keys()) == ["key"]
    assert custom["section1"]["key"].value == "value"
    assert custom["section1"]["key"].raw_key == "k_e_y"


def test_section_contains():
    config = """\
    [section1]
    key = value
    """

    lowercase = ConfigUpdater()
    lowercase.read_string(dedent(config).lower())

    uppercase = ConfigUpdater()
    uppercase.optionxform = str
    uppercase.read_string(dedent(config).upper())

    assert "KEY" in uppercase["SECTION1"]
    assert "key" not in uppercase["SECTION1"]

    assert "key" in lowercase["section1"]
    assert "KEY" not in lowercase["section1"]


def test_section_setitem():
    cfg = ConfigUpdater()
    cfg.optionxform = str.upper
    cfg.read_string("[section1]\nOTHERKEY = 0")

    assert "KEY" not in cfg["section1"]
    cfg["section1"]["key"] = "value"
    assert "KEY" in cfg["section1"]
    assert cfg["section1"]["KEY"].value == "value"

    cfg["section1"]["key"] = "42"
    assert cfg["section1"]["KEY"].value == "42"
    assert cfg["section1"]["key"].value == "42"

    other = ConfigUpdater()
    other.optionxform = str.lower
    other.read_string("[section1]\nkEy = value")
    option = other["section1"]["key"].detach()

    with pytest.raises(ValueError):
        # otherkey exists in section1, but option is `key` instead of `otherkey`
        cfg["section1"]["otherkey"] = option
    with pytest.raises(ValueError):
        # anotherkey exists in section1 and option is `key` instead of `anotherkey`
        cfg["section1"]["anotherkey"] = option

    assert cfg["section1"]["key"].raw_key == "key"
    cfg["section1"]["key"] = option
    assert cfg["section1"]["key"].value == "value"
    assert cfg["section1"]["key"].key == "KEY"
    assert cfg["section1"]["key"].raw_key == "kEy"
