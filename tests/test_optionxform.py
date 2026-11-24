from configparser import ConfigParser, DuplicateOptionError
from io import StringIO
from textwrap import dedent

import pytest

from configupdater import ConfigUpdater, NoOptionError


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


def test_validate_format_uses_optionxform():
    config = "[section]\nKey = first\nkey = second\n"
    updater = ConfigUpdater()
    updater.optionxform = str
    updater.read_string(config)
    parser = ConfigParser()
    parser.optionxform = str
    parser.read_string(config)

    assert updater.validate_format() is True
    assert updater.to_dict() == {"section": dict(parser["section"])}
    assert str(updater) == config


def test_write_uses_optionxform():
    config = "[section]\nKey = first\nkey = second\n"
    updater = ConfigUpdater()
    updater.optionxform = str
    updater.read_string(config)
    output = StringIO()

    updater.write(output)

    assert output.getvalue() == config
    parser = ConfigParser()
    parser.optionxform = str
    parser.read_string(output.getvalue())
    assert dict(parser["section"]) == {"Key": "first", "key": "second"}


def test_update_file_uses_optionxform(tmp_path):
    path = tmp_path / "settings.ini"
    path.write_text("[section]\nKey = first\nkey = second\n", encoding="utf-8")
    updater = ConfigUpdater()
    updater.optionxform = str
    updater.read(path, encoding="utf-8")
    updater["section"]["Key"].value = "updated"

    assert updater.update_file() is updater

    assert path.read_text(encoding="utf-8") == (
        "[section]\nKey = updated\nkey = second\n"
    )
    parser = ConfigParser()
    parser.optionxform = str
    parser.read(path, encoding="utf-8")
    assert dict(parser["section"]) == {"Key": "updated", "key": "second"}


@pytest.mark.parametrize(
    ("optionxform", "other_key"),
    [(str.lower, "KEY"), (lambda key: key.replace("_", ""), "k_e_y")],
    ids=["default", "custom"],
)
def test_validate_format_rejects_normalized_duplicates(optionxform, other_key):
    config = f"[section]\nkey = first\n{other_key} = second\n"
    updater = ConfigUpdater()
    updater.optionxform = str
    updater.read_string(config)
    updater.optionxform = optionxform
    parser = ConfigParser()
    parser.optionxform = optionxform

    with pytest.raises(DuplicateOptionError, match="option 'key'"):
        parser.read_string(config)
    with pytest.raises(DuplicateOptionError, match="option 'key'"):
        updater.validate_format()

    assert updater.validate_format(strict=False) is True
    assert str(updater) == config


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

    # Like `section[key]`, `in` applies optionxform (here the default str.lower)
    assert "key" in lowercase["section1"]
    assert "KEY" in lowercase["section1"]
    assert lowercase["section1"].has_option("KEY")
    assert "missing" not in lowercase["section1"]


@pytest.mark.parametrize("key", ["key", "KEY", "kEy", "missing"])
def test_section_lookup_matches_configparser(key):
    config = "[section]\nKey = value\n"
    updater = ConfigUpdater()
    updater.read_string(config)
    parser = ConfigParser()
    parser.read_string(config)
    section, proxy = updater["section"], parser["section"]

    assert (key in section) == (key in proxy)
    assert section.has_option(key) == parser.has_option("section", key)
    assert updater.has_option("section", key) == parser.has_option("section", key)

    option = section.get(key)
    assert (None if option is None else option.value) == proxy.get(key)


def test_section_get_uses_optionxform():
    config = ConfigUpdater()
    config.read_string("[section]\nKey = value\n")
    section = config["section"]

    assert section.get("KEY") is section["key"]
    assert section.get("MISSING") is None
    assert section.get("MISSING", "default") == "default"
    assert config.get("section", "KEY") is section["key"]


def test_section_pop_uses_optionxform():
    config = ConfigUpdater()
    config.read_string("[section]\nKey = value\nother = 1\n")
    parser = ConfigParser()
    parser.read_string("[section]\nKey = value\nother = 1\n")

    option = config["section"].pop("KEY")
    assert option.raw_key == "Key"
    assert option.value == parser["section"].pop("KEY") == "value"
    assert str(config) == "[section]\nother = 1\n"
    assert config["section"].pop("KEY", None) is None
    with pytest.raises(KeyError):
        config["section"].pop("KEY")


def test_section_set_keeps_raw_key():
    config = ConfigUpdater()
    config.read_string("[section]\nExisting = 0\n")
    section = config["section"]

    section.set("NewKey", "1")
    section["OtherKey"] = "2"
    config.set("section", "DocKey", "3")
    section.set("MultiKey", ["a", "b"])
    assert [o.raw_key for o in section.iter_options()] == [
        "Existing",
        "NewKey",
        "OtherKey",
        "DocKey",
        "MultiKey",
    ]
    assert section.options() == ["existing", "newkey", "otherkey", "dockey", "multikey"]

    # Setting an existing option keeps its original spelling
    section.set("EXISTING", "4")
    config.set("section", "newkey", "5")
    assert str(config) == dedent(
        """\
        [section]
        Existing = 4
        NewKey = 5
        OtherKey = 2
        DocKey = 3
        MultiKey =
            a
            b
        """
    )


def prefix_optionxform(key):
    """Not idempotent, so it reveals keys that are transformed twice."""
    return "x_" + key


def test_section_methods_apply_optionxform_once():
    config = ConfigUpdater()
    config.optionxform = prefix_optionxform
    config.read_string("[section]\nkey = value\n")
    section = config["section"]

    assert section.options() == ["x_key"]
    assert "key" in section
    assert section.has_option("key")
    assert section.get("key") is section["key"]

    section.set("key", "new")
    assert section["key"].value == "new"
    section["key"] = "newer"
    assert section["key"].value == "newer"
    section.set("other", "1")
    assert section["other"].raw_key == "other"
    assert str(config) == "[section]\nkey = newer\nother = 1\n"

    assert section.pop("key").value == "newer"
    assert "key" not in section
    assert str(config) == "[section]\nother = 1\n"


def test_document_methods_apply_optionxform_once():
    config = "[section]\nlicense = MIT\n"
    updater = ConfigUpdater()
    updater.optionxform = prefix_optionxform
    updater.read_string(config)
    parser = ConfigParser()
    parser.optionxform = prefix_optionxform
    parser.read_string(config)

    assert updater.has_option("section", "license")
    assert parser.has_option("section", "license")
    assert updater.get("section", "license").value == "MIT"
    assert parser.get("section", "license") == "MIT"

    updater.set("section", "license", "GPL")
    parser.set("section", "license", "GPL")
    updater.set("section", "author", "me")
    parser.set("section", "author", "me")
    assert updater.get("section", "license").value == "GPL"
    assert parser.get("section", "license") == "GPL"
    assert updater["section"].options() == parser.options("section")
    assert str(updater) == "[section]\nlicense = GPL\nauthor = me\n"

    assert updater.remove_option("section", "license") is True
    assert parser.remove_option("section", "license") is True
    assert updater.remove_option("section", "license") is False
    assert parser.remove_option("section", "license") is False
    assert str(updater) == "[section]\nauthor = me\n"

    with pytest.raises(NoOptionError) as updater_error:
        updater.get("section", "license")
    with pytest.raises(NoOptionError) as parser_error:
        parser.get("section", "license")
    assert updater_error.value.option == parser_error.value.option == "x_license"


def test_section_delitem_uses_optionxform():
    config = ConfigUpdater()
    config.read_string("[section]\nKey = Value\n")

    section = config["section"]
    del section["KEY"]

    assert section.option_blocks() == []
    assert str(config) == "[section]\n"
    with pytest.raises(KeyError):
        del section["MISSING"]


def test_section_delitem_uses_custom_optionxform():
    config = ConfigUpdater()
    config.optionxform = lambda option: option.replace("_", "").lower()
    config.read_string("[section]\nK_E_Y = Value\n")

    del config["section"]["K_E_Y"]

    assert config["section"].option_blocks() == []


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

    with pytest.raises(ValueError, match="does not equal option key"):
        # otherkey exists in section1, but option is `key` instead of `otherkey`
        cfg["section1"]["otherkey"] = option
    with pytest.raises(ValueError, match="does not equal option key"):
        # anotherkey exists in section1 and option is `key` instead of `anotherkey`
        cfg["section1"]["anotherkey"] = option

    assert cfg["section1"]["key"].raw_key == "key"
    cfg["section1"]["key"] = option
    assert cfg["section1"]["key"].value == "value"
    assert cfg["section1"]["key"].key == "KEY"
    assert cfg["section1"]["key"].raw_key == "kEy"
