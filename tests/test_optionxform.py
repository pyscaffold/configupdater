from textwrap import dedent

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


def test_contains():
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


def test_add_option():
    cfg = ConfigUpdater()
    cfg.optionxform = str.upper
    cfg.read_string("[section1]")

    assert "OTHERKEY" not in cfg["section1"]
    cfg["section1"]["otherkey"] = "othervalue"
    assert "OTHERKEY" in cfg["section1"]
    assert cfg["section1"]["OTHERKEY"].value == "othervalue"

    cfg["section1"]["otherkey"] = "42"
    assert cfg["section1"]["OTHERKEY"].value == "42"
    assert cfg["section1"]["otherkey"].value == "42"
