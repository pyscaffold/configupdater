import configparser
import copy
import os.path
from configparser import ConfigParser
from io import StringIO
from textwrap import dedent

import pytest

from configupdater import (
    AlreadyAttachedError,
    AssignMultilineValueError,
    Comment,
    ConfigUpdater,
    DuplicateOptionError,
    DuplicateSectionError,
    MissingSectionHeaderError,
    NoConfigFileReadError,
    NoneValueDisallowed,
    NoOptionError,
    NoSectionError,
    NotAttachedError,
    Option,
    ParsingError,
    Section,
    Space,
)


def test_read_write_no_changes(setup_cfg_path, setup_cfg):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    assert str(updater) == setup_cfg


def test_read_file_like(setup_cfg_path):
    updater = ConfigUpdater()
    with open(setup_cfg_path) as fp:
        updater.read_file(fp)
    fp = StringIO()
    updater.read_file(fp)


def test_update_no_changes(setup_cfg_path):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    old_mtime = os.path.getmtime(setup_cfg_path)
    updater.update_file()
    new_mtime = os.path.getmtime(setup_cfg_path)
    assert old_mtime != new_mtime


def test_updater_to_dict(setup_cfg_path):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    parser = ConfigParser()
    parser.read(setup_cfg_path)
    parser_dict = {sect: dict(parser[sect]) for sect in parser.sections()}
    assert updater.to_dict() == parser_dict


def test_update_no_cfg():
    updater = ConfigUpdater()
    with pytest.raises(NoConfigFileReadError):
        updater.update_file()


def test_update_file_issue_68(tmp_path):
    # allow_no_value = False
    file = tmp_path / "file.cfg"
    file.write_text("[section]")
    cfg = ConfigUpdater(allow_no_value=False).read_file(open(file))
    cfg.set("section", "option")
    with pytest.warns(NoneValueDisallowed):
        # A warning is issued, but the method will not fail
        cfg.update_file()
    assert file.read_text().strip() == "[section]"

    # allow_no_value = True
    file.write_text("[section]")
    cfg = ConfigUpdater(allow_no_value=True).read_file(open(file))
    cfg.set("section", "option")
    cfg.update_file()
    assert file.read_text().strip() == "[section]\noption"


def test_str(setup_cfg_path, setup_cfg):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    output = str(updater)
    assert output == setup_cfg


def test_has_section(setup_cfg_path):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    assert updater.has_section("metadata")
    assert not updater.has_section("nonexistent_section")


def test_contains_section(setup_cfg_path):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    assert "metadata" in updater


def test_sections(setup_cfg_path):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    exp_sections = [
        "metadata",
        "options",
        "options.packages.find",
        "options.extras_require",
        "test",
        "tool:pytest",
        "aliases",
        "bdist_wheel",
        "build_sphinx",
        "devpi:upload",
        "flake8",
        "pyscaffold",
    ]
    assert updater.sections() == exp_sections


def test_len_updater(setup_cfg_path):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    # we test the number of blocks, not sections
    assert len(updater) == 14


def test_iter_section(setup_cfg_path):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    # iter_blocks will give us everything, iter_sections just the section objects and
    # __iter__ should work as iter_blocks
    assert len([block for block in updater.iter_blocks()]) == 14
    assert len([block for block in updater.iter_sections()]) == 12
    assert len([entry for entry in updater]) == 12


def test_iter_items_section(setup_cfg_path):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)

    result = list(k for k, v in updater["metadata"].items())
    assert result == [
        "name",
        "description",
        "author",
        "author-email",
        "license",
        "url",
        "long-description",
        "platforms",
        "classifiers",
    ]


def test_get_section(setup_cfg_path):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    section = updater["metadata"]
    assert section._structure
    with pytest.raises(KeyError):
        updater["non_existent_section"]

    # `get_section` is equivalent to dict.get
    assert updater.get_section("non_existent_section") is None
    default = {}
    assert updater.get_section("non_existent_section", default) is default


def test_section_to_dict(setup_cfg_path):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    parser = ConfigParser()
    parser.read(setup_cfg_path)
    updater_dict = updater["metadata"].to_dict()
    parser_dict = dict(parser["metadata"])
    assert updater_dict == parser_dict


def test_has_option(setup_cfg_path):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    assert updater.has_option("metadata", "author")
    assert not updater.has_option("metadata", "coauthor")
    assert not updater.has_option("nonexistent_section", "key")


def test_contains_options(setup_cfg_path):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    section = updater["metadata"]
    assert "author" in section
    assert "wrong_option" not in section


def test_len_section(setup_cfg_path):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    section = updater["metadata"]
    # we test the number of blocks in section
    assert len(section) == 12


def test_len_option(setup_cfg_path):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    option = updater["metadata"]["classifiers"]
    assert len(option.lines) == 3


def test_iter_option(setup_cfg_path):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    section = updater["metadata"]
    # iter_blocks will give us everything, iter_options just the option objects and
    # __iter__ should work as iter_blocks
    assert len([entry for entry in section.iter_blocks()]) == 12
    assert len([entry for entry in section.iter_options()]) == 9
    assert len([entry for entry in section]) == 9


def test_get_options(setup_cfg_path):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    options = updater.options("options.packages.find")
    exp_options = ["where", "exclude"]
    assert options == exp_options
    with pytest.raises(NoSectionError):
        updater.options("non_existent_section")

    # Section objects also have a "get" method similar to dict
    section = updater["metadata"]
    assert section.get("name").value == "configupdater"
    assert section.get("non_existent_option") is None
    assert section.get("non_existent_option", []) == []


def test_items(setup_cfg_path):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    sect_names, sects = zip(*updater.items())
    exp_sect_namess = [
        "metadata",
        "options",
        "options.packages.find",
        "options.extras_require",
        "test",
        "tool:pytest",
        "aliases",
        "bdist_wheel",
        "build_sphinx",
        "devpi:upload",
        "flake8",
        "pyscaffold",
    ]
    assert list(sect_names) == exp_sect_namess
    assert all([isinstance(s, Section) for s in sects])

    opt_names, opts = zip(*updater.items("devpi:upload"))
    exp_opt_names = ["no-vcs", "formats"]
    assert list(opt_names) == exp_opt_names
    assert all([isinstance(o, Option) for o in opts])


def test_get_method(setup_cfg_path):
    updater = ConfigUpdater()
    updater.read(setup_cfg_path)
    value = updater.get("metadata", "license").value
    assert value == "mit"
    with pytest.raises(NoSectionError):
        updater.get("non_existent_section", "license")
    with pytest.raises(NoOptionError):
        updater.get("metadata", "wrong_key")
    assert updater.get("metadata", "wrong_key", fallback=None) is None


test1_cfg_in = """
[default]
key = 1
"""

test1_cfg_out = """
[default]
key = 2
"""

test1_cfg_out_added = """
[default]
key = 1
other_key = 3
"""

test1_cfg_out_none = """
[default]
key
"""

test1_cfg_out_removed = """
[default]
"""

test1_cfg_out_values = """
[default]
key =
    param1
    param2
"""


def test_get_option():
    updater = ConfigUpdater()
    updater.read_string(test1_cfg_in)
    updater.read_string(test1_cfg_in)
    option = updater["default"]["key"]
    assert option.value == "1"
    with pytest.raises(KeyError):
        updater["default"]["wrong_key"]


def test_value_change():
    updater = ConfigUpdater()
    updater.read_string(test1_cfg_in)
    assert updater["default"]["key"].value == "1"
    updater["default"]["key"].value = "2"
    assert str(updater) == test1_cfg_out
    # try another way
    section = updater["default"]
    section["key"] = "1"
    assert str(updater) == test1_cfg_in


def test_remove_option():
    updater = ConfigUpdater()
    updater.read_string(test1_cfg_in)
    updater.remove_option("default", "key")
    assert str(updater) == test1_cfg_out_removed
    updater.remove_option("default", "non_existent_key")
    updater.read_string(test1_cfg_in)
    del updater["default"]["key"]
    assert str(updater) == test1_cfg_out_removed
    with pytest.raises(NoSectionError):
        updater.remove_option("wrong_section", "key")


def test_set_option():
    updater = ConfigUpdater(allow_no_value=True)
    updater.read_string(test1_cfg_in)
    updater.set("default", "key", "1")
    assert updater["default"]["key"].value == "1"
    updater.set("default", "key", 2)
    assert updater["default"]["key"].value == 2
    assert str(updater) == test1_cfg_out
    updater.set("default", "key")
    assert updater["default"]["key"].value is None
    assert str(updater) == test1_cfg_out_none
    updater.read_string(test1_cfg_in)
    updater.set("default", "other_key", 3)
    assert str(updater) == test1_cfg_out_added
    updater.read_string(test1_cfg_in)
    values = ["param1", "param2"]
    updater["default"]["key"].set_values(values)
    assert str(updater) == test1_cfg_out_values
    assert values == ["param1", "param2"]  # non destructive operation
    with pytest.raises(NoSectionError):
        updater.set("wrong_section", "key", "1")
    new_option = copy.deepcopy(updater["default"]["key"])
    updater["default"]["key"] = new_option
    assert updater["default"]["key"] is new_option
    new_option = copy.deepcopy(updater["default"]["key"])
    new_option.key = "wrong_key"
    with pytest.raises(ValueError):
        updater["default"]["key"] = new_option


def test_section_set_option():
    updater = ConfigUpdater(allow_no_value=True)
    updater.read_string(test1_cfg_in)
    default_sec = updater["default"]
    default_sec.set("key", "1")
    assert default_sec["key"].value == "1"
    default_sec.set("key", 2)
    assert default_sec["key"].value == 2
    assert str(default_sec) == test1_cfg_out[1:]
    default_sec.set("key")
    assert default_sec["key"].value is None
    assert str(default_sec) == test1_cfg_out_none[1:]
    updater.read_string(test1_cfg_in)
    default_sec = updater["default"]
    default_sec.set("other_key", 3)
    assert str(default_sec) == test1_cfg_out_added[1:]
    updater.read_string(test1_cfg_in)
    default_sec = updater["default"]
    values = ["param1", "param2"]
    default_sec["key"].set_values(values)
    assert str(default_sec) == test1_cfg_out_values[1:]
    assert values == ["param1", "param2"]  # non destructive operation


def test_del_option():
    updater = ConfigUpdater()
    updater.read_string(test1_cfg_in)
    del updater["default"]["key"]
    assert str(updater) == "\n[default]\n"
    with pytest.raises(KeyError):
        del updater["default"]["key"]


test2_cfg_in = """
[section1]
key = 1

[section2]
key = 2
"""

test2_cfg_out = """
[section1]
key = 1

"""


def test_del_section():
    updater = ConfigUpdater()
    updater.read_string(test2_cfg_in)
    del updater["section2"]
    assert str(updater) == test2_cfg_out
    with pytest.raises(KeyError):
        del updater["section2"]


test_wrong_cfg = """
[strange section]
a
"""


def test_handle_error():
    updater = ConfigUpdater(allow_no_value=False)
    with pytest.raises(ParsingError):
        updater.read_string(test_wrong_cfg)


def test_validate_format(setup_cfg_path):
    updater = ConfigUpdater(allow_no_value=True)
    updater.read(setup_cfg_path)
    updater.validate_format(allow_no_value=False)
    updater.set("metadata", "author")
    with pytest.raises(ParsingError):
        updater.validate_format(allow_no_value=False)


def test_validate_format_propagates_kwargs(setup_cfg_path):
    updater = ConfigUpdater(allow_no_value=True)
    updater.read(setup_cfg_path)
    updater.set("pyscaffold", "namespace")
    assert updater["pyscaffold"]["namespace"].value is None
    assert str(updater["pyscaffold"]["namespace"]) == "namespace\n"  # no `=` sign
    assert updater.validate_format() is True


test3_cfg_in = """
[section]
key = 1
"""

test3_cfg_out = """
# comment of section
[section]
key = 1
# comment after section
"""


def test_add_before_after_comment():
    updater = ConfigUpdater()
    updater.read_string(test3_cfg_in)
    updater["section"].add_before.comment("comment of section")
    updater["section"].add_after.comment("# comment after section\n")
    assert str(updater) == test3_cfg_out


test4_cfg_in = """
[section]
key1 = 1
"""

test4_cfg_out = """
[section]
key0 = 0
key1 = 1
key2
"""


def test_add_before_after_option():
    updater = ConfigUpdater(allow_no_value=True)
    updater.read_string(test4_cfg_in)
    with pytest.raises(ValueError):
        updater["section"].add_before.option("key0", 0)
    updater["section"]["key1"].add_before.option("key0", 0)
    updater["section"]["key1"].add_after.option("key2")
    assert str(updater) == test4_cfg_out


test5_cfg_in = """
[section0]
key0 = 0
[section1]
key1 = 1
key2 = 2
"""


test5_cfg_out = """
[section0]
key0 = 0


[section1]
key1 = 1

key2 = 2
"""


def test_add_before_after_space():
    updater = ConfigUpdater()
    updater.read_string(test5_cfg_in)
    updater["section1"].add_before.space(2)
    updater["section1"]["key1"].add_after.space(1)
    assert str(updater) == test5_cfg_out


test6_cfg_in = """
[section0]
key0 = 0
[section2]
key1 = 1
key2 = 2
"""


test6_cfg_out = """
[section0]
key0 = 0
[section1]
key1 = 42
[section2]
key1 = 1
key2 = 2

[section3]
"""


test6_cfg_out_new_sect = """
[section0]
key0 = 0
[section2]
key1 = 1
key2 = 2
[new_section]
key0 = 0
"""


def test_add_before_after_section():
    updater = ConfigUpdater()
    updater.read_string(test6_cfg_in)
    with pytest.raises(ValueError):
        updater["section2"]["key1"].add_before.section("section1")
    updater["section2"].add_before.section("section1")
    updater["section1"]["key1"] = 42
    updater["section2"].add_after.space(1).section("section3")
    assert str(updater) == test6_cfg_out
    with pytest.raises(ValueError):
        updater["section2"].add_before.section(updater["section2"]["key1"])
    updater.read_string(test6_cfg_in)
    sect_updater = ConfigUpdater()
    sect_updater.read_string(test6_cfg_in)
    section = sect_updater["section0"]
    section.name = "new_section"
    updater["section2"].add_after.section(section.detach())
    assert str(updater) == test6_cfg_out_new_sect
    with pytest.raises(DuplicateSectionError):
        updater["section2"].add_after.section(section)


test7_cfg_in = """
[section0]
key0 = 0

[section1]
key1 = 42
"""


test7_cfg_out = """
[section0]
key0 = 0

[section1]
key1 = 42
[section2]
key1 = 1
"""


def test_add_section():
    updater = ConfigUpdater()
    updater.read_string(test7_cfg_in)
    with pytest.raises(DuplicateSectionError):
        updater.add_section("section1")
    updater.add_section("section2")
    updater["section2"]["key1"] = 1
    assert str(updater) == test7_cfg_out
    with pytest.raises(ValueError):
        updater.add_section(updater["section2"]["key1"])


test6_cfg_out_overwritten = """
[section0]
key0 = 42
[section2]
key1 = 1
key2 = 2
"""


def test_set_item_section():
    updater = ConfigUpdater()
    sect_updater = ConfigUpdater()
    updater.read_string(test6_cfg_in)
    with pytest.raises(ValueError):
        updater["section"] = "newsection"
    sect_updater.read_string(test6_cfg_in)
    section = sect_updater["section0"]
    with pytest.raises(ValueError):
        updater["new_section"] = section
    section.name = "new_section"
    updater["new_section"] = section.detach()
    assert str(updater) == test6_cfg_out_new_sect
    # test overwriting an existing section
    updater.read_string(test6_cfg_in)
    sect_updater.read_string(test6_cfg_in)
    exist_section = sect_updater["section0"]
    exist_section["key0"] = 42
    updater["section0"] = exist_section.detach()
    assert str(updater) == test6_cfg_out_overwritten


def test_no_space_around_delim():
    updater = ConfigUpdater(space_around_delimiters=False)
    updater.read_string(test7_cfg_in)
    updater["section0"]["key0"] = 0
    del updater["section1"]
    assert str(updater) == "\n[section0]\nkey0=0\n\n"


def test_constructor(setup_cfg_path):
    updater = ConfigUpdater(delimiters=(":", "="))
    updater.read(setup_cfg_path)
    updater = ConfigUpdater(delimiters=(":", "="), allow_no_value=True)
    updater.read(setup_cfg_path)


test8_inline_prefixes = """
[section] # just a section
key = value  # just a value
"""


def test_inline_comments():
    updater = ConfigUpdater(inline_comment_prefixes="#")
    updater.read_string(test8_inline_prefixes)
    assert updater.has_section("section")
    assert updater["section"]["key"].value == "value"


test9_dup_section = """
[section]
key = value

[section]
key = value
"""


def test_duplicate_section_error():
    updater = ConfigUpdater()
    with pytest.raises(DuplicateSectionError):
        updater.read_string(test9_dup_section)


def test_missing_section_error():
    updater = ConfigUpdater()
    with pytest.raises(MissingSectionHeaderError):
        updater.read_string("key = value")


test10_dup_option = """
[section]
key = value
key = value
"""


def test_duplicate_option_error():
    updater = ConfigUpdater()
    with pytest.raises(DuplicateOptionError):
        updater.read_string(test10_dup_option)


test11_no_values = """
[section]
key
"""


def test_no_value():
    updater = ConfigUpdater(allow_no_value=True)
    updater.read_string(test11_no_values)
    assert updater["section"]["key"].value is None


def test_eq(setup_cfg_path):
    updater1 = ConfigUpdater()
    updater1.read(setup_cfg_path)
    updater2 = ConfigUpdater()
    updater2.read(setup_cfg_path)
    assert updater1 == updater2
    updater1.remove_section("metadata")
    assert updater1 != updater2
    assert updater1 != updater2["metadata"]
    assert updater2["metadata"] != updater2["metadata"]["author"]
    assert not updater1.remove_section("metadata")


test12_cfg_in = """
[section]
opiton = 42
"""


test12_cfg_out = """
[section]
option = 42
"""


def test_rename_option_key():
    updater = ConfigUpdater()
    updater.read_string(test12_cfg_in)
    updater["section"]["opiton"].key = "option"


test13_cfg_in = """
[section]
CAPITAL = 1
"""


def test_set_optionxform():
    updater = ConfigUpdater()
    updater.read_string(test13_cfg_in)
    assert updater["section"]["capital"].value == "1"
    assert callable(updater.optionxform)
    updater.optionxform = lambda x: x
    updater.read_string(test13_cfg_in)
    assert updater["section"]["CAPITAL"].value == "1"


test14_cfg_in = """
[section]
option2 = 2
option4 = 4
"""

test14_cfg_out = """
[section]
option0 = 0
option1 = 1
option2 = 2
option3 = 3
option4 = 4
"""


def test_insert_at():
    updater = ConfigUpdater()
    updater.read_string(test14_cfg_in)
    updater["section"].insert_at(0).option("option0", 0).option("option1", 1)
    updater["section"].insert_at(3).option("option3", 3)
    assert str(updater) == test14_cfg_out


def test_read_file_with_string():
    updater = ConfigUpdater()
    with pytest.raises(RuntimeError):
        updater.read_file("path/to/file.cfg")


test15_cfg_in = """
[section]
OptionA = 2
"""


def test_read_mixed_case_options():
    updater = ConfigUpdater()
    updater.read_string(test15_cfg_in)
    assert updater.has_option("section", "OptionA")
    assert updater.has_option("section", "optiona")
    assert updater["section"]["OptionA"].value == "2"
    assert updater["section"]["optiona"].value == "2"


test16_cfg_in = """
[section]
OptionA = 2
"""


test16_cfg_out = """
[section]
OptionA = 4
OptionB = 6
"""


def test_update_mixed_case_options():
    updater = ConfigUpdater()
    updater.read_string(test16_cfg_in)
    updater["section"]["optiona"].value = "4"
    updater["section"]["OptionB"] = "6"
    assert str(updater) == test16_cfg_out


test17_cfg_in = """
[section]
key1 = 1
"""


test17_cfg_out = """
[section]
key0 = 0
key1 = 1
key2 = 2
key3 = 3
"""


def test_add_before_then_add_after_option():
    updater = ConfigUpdater()
    updater.read_string(test17_cfg_in)
    updater["section"]["key1"].add_before.option("key0", "0")
    updater["section"]["key1"].add_after.option("key2", "2")
    updater["section"]["key2"].add_after.option("key3", "3")
    assert str(updater) == test17_cfg_out


test18_cfg_in = """
[section]
Key0 = 0
"""

test18_cfg_out = """
[section]
Key0 = 2
"""


def test_assure_no_duplicate_options():
    updater = ConfigUpdater()
    updater.read_string(test18_cfg_in)
    updater["section"]["KEY0"].value = "1"
    updater["section"]["keY0"] = "2"
    assert str(updater) == test18_cfg_out


test19_cfg_in = """
[section]
Key0 = 0
"""


def test_no_duplicate_blocks_with_blockbuilder():
    updater = ConfigUpdater()
    updater.read_string(test19_cfg_in)
    with pytest.raises(DuplicateOptionError):
        updater["section"]["Key0"].add_after.option("key0", "1")
    with pytest.raises(DuplicateSectionError):
        updater["section"].add_after.section("section")
    assert str(updater) == test19_cfg_in


# Taken from issue #14
test20_cfg_in = """
[flake8]
exclude =
  # Trash and cache:
  .git
  __pycache__
  .venv
  .eggs
  *.egg
  temp
  # Bad code that I write to test things:
  ex.py
new = value

per-file-ignores =
  # Disable imports in `__init__.py`:
  lambdas/__init__.py: WPS226, WPS413
  lambdas/contrib/mypy/lambdas_plugin.py: WPS437
  # There are multiple assert's in tests:
  tests/*.py: S101, WPS226, WPS432, WPS436, WPS450
  # We need to write tests to our private class:
  tests/test_math_expression/*.py: S101, WPS432, WPS450"""


def test_comments_in_multiline_options():
    updater = ConfigUpdater()
    updater.read_string(test20_cfg_in)
    per_file_ignores = updater["flake8"]["per-file-ignores"].value
    exp_val = (
        "\n# Disable imports in `__init__.py`:\nlambdas/__init__.py: WPS226, WPS413\n"
        "lambdas/contrib/mypy/lambdas_plugin.py: WPS437\n# There are multiple assert's"
        " in tests:\ntests/*.py: S101, WPS226, WPS432, WPS436, WPS450\n# We need to"
        " write tests to our private class:\ntests/test_math_expression/*.py: S101,"
        " WPS432, WPS450"
    )
    updater.validate_format()
    assert per_file_ignores == exp_val
    assert test20_cfg_in == str(updater)


test21_cfg_in = """
[main1]
key1 =
    a
    b

    c
    d
[main2]
key1 =
    a
    b

    c
    d

[main3]

[main4]
key1 =
    a
    b


    c
    d
key2 =
    # comment
    a
    b
    # comment


    c
    d
[main5]
key1 =
    a
    b

    c
    d

key2 = abcd
[main6]
"""


def test_empty_lines_in_values_support():
    updater = ConfigUpdater()
    updater.read_string(test21_cfg_in)
    parser = ConfigParser()
    parser.read_string(test21_cfg_in)
    assert updater["main1"]["key1"].value == parser["main1"]["key1"]
    assert updater["main2"]["key1"].value == parser["main2"]["key1"]
    assert updater["main4"]["key1"].value == parser["main4"]["key2"]

    # Make sure values are not being stored in "whitespace nodes"
    value = (x.strip() for x in updater["main1"]["key1"].value.splitlines())
    assert [v for v in value if v] == ["a", "b", "c", "d"]

    assert test21_cfg_in == str(updater)
    with pytest.raises(ParsingError):
        updater = ConfigUpdater(empty_lines_in_values=False)
        updater.read_string(test21_cfg_in)


test22_cfg_in = """
[section]
key1 = 1
# comment
key2 = 2

"""

test22_cfg_out = """
[section]
key1 = 1
key2 = 2
"""


def test_navigation_and_remove():
    updater = ConfigUpdater()
    updater.read_string(test22_cfg_in)
    section = updater["section"]
    key1 = section["key1"]
    assert key1 is updater["section"].first_block
    assert key1.previous_block is None
    assert isinstance(key1.next_block, Comment)
    key2 = key1.next_block.next_block
    assert key2.value == section["key2"].value
    assert isinstance(key2.next_block, Space)
    assert key2.next_block is section.last_block
    assert section.last_block.next_block is None
    key1.next_block.detach()
    key2.next_block.detach()
    assert str(updater) == test22_cfg_out


test23_cfg_in = """
[section1]
    # indented comment
a = 42
"""


def test_indented_comment():
    updater = ConfigUpdater()
    updater.read_string(test23_cfg_in)
    section = updater["section1"]
    assert isinstance(section.first_block, Comment)
    assert str(updater) == test23_cfg_in


test24_cfg_in = """
[sec1]
key1 = val1
key2 = val2

[sec2]
key1 = val1
key2 = val2
"""


def test_iter_consistency_with_configparser():
    parser = ConfigParser()
    parser.read_string(test24_cfg_in)
    updater = ConfigUpdater()
    updater.read_string(test24_cfg_in)
    # [1:] to drop 'DEFAULT' section
    assert list(parser)[1:] == list(updater)
    assert list(parser["sec1"]) == list(updater["sec1"])


def test_add_detached_section_option_objects():
    updater = ConfigUpdater()
    updater.read_string(test24_cfg_in)
    sec1 = updater["sec1"]
    sec2 = updater["sec2"]
    assert sec2.container is updater
    sec2.detach()
    assert not updater.has_section("sec2")
    assert not sec2.has_container()
    with pytest.raises(NotAttachedError):
        sec2.container

    new_sec2 = Section("new-sec2")
    new_opt = Option(key="new-key", value="new-value")
    new_sec2.add_option(new_opt)
    with pytest.raises(AlreadyAttachedError):
        sec1.add_option(new_opt)
    updater.add_section(new_sec2)
    assert updater.has_section("new-sec2")
    assert updater["new-sec2"]["new-key"].value == "new-value"

    new_sec3 = Section("new-sec3")
    new_opt2 = Option(key="new-key", value="new-value")
    updater["new-sec3"] = new_sec3
    new_sec3["new-key"] = new_opt2


def test_transferring_blocks_between_elements():
    # Let's say a user have a big new section that it wants to insert in an existing
    # document. Instead of programmatically creating this new section using the builder
    # API, they might be tempted to parse this new section from template files.

    existing = """\
    [section0]
    option0 = 0
    """

    template1 = """\
    [section1]
    option1 = 1
    """

    template2 = """\
    [section2]
    option2 = 2
    # comment
    """

    target = ConfigUpdater()
    target.read_string(dedent(existing))

    source1 = ConfigUpdater()
    source1.read_string(dedent(template1))

    source2 = ConfigUpdater()
    source2.read_string(dedent(template2))

    target["section1"] = source1["section1"].detach()
    assert "section1" in target

    target["section1"].add_after.section(source2["section2"].detach())
    assert "section2" not in source1
    assert "section2" in target


def test_transfering_sections_and_manipulating_options():
    # This test case is similar to `test_transfering_sections_between_elements`,
    # but now we use the builder API in the options inside the transferred section.
    # We need to make sure that when a section is copied to a different tree,
    # the references inside the options are updated, so we don't end up adding blocks in
    # the original object.

    existing = """\
    [section0]
    option0 = 0
    """

    template1 = """\
    [section1]
    option1 = 1
    """

    target = ConfigUpdater()
    target.read_string(dedent(existing))

    source1 = ConfigUpdater()
    source1.read_string(dedent(template1))

    target["section1"] = source1["section1"].detach()
    assert "section1" in target

    target["section1"]["option1"].add_after.option("option2", "value")

    assert "option2" not in str(source1)
    assert "option2" in str(target)


def test_transfering_sections_and_manipulating_options_with_deepcopy():
    existing = """\
    [section0]
    option0 = 0
    """

    template1 = """\
    [section1]
    option1 = 1
    """

    template2 = """\
    [section2]
    option2 = 2
    # comment
    """

    target = ConfigUpdater()
    target.read_string(dedent(existing))

    source1 = ConfigUpdater()
    source1.read_string(dedent(template1))

    source2 = ConfigUpdater()
    source2.read_string(dedent(template2))

    target["section1"] = copy.deepcopy(source1["section1"])
    assert "section1" in target
    assert "section1" in source1

    target["section1"].add_after.section(copy.deepcopy(source2["section2"]))
    target["section2"]["option2"] = "value"
    assert "option2 = value" in str(target)
    assert "option2" not in str(source1)
    assert "value" not in str(source2)


def test_deepcopy():
    example = """\
    [options]
    testing =   # Add here test requirements (used by tox)
        sphinx  # required for system tests
        flake8  # required for system tests
    """
    updater = ConfigUpdater().read_string(dedent(example))
    clone = copy.deepcopy(updater)
    assert clone["options"].container is clone
    assert clone["options"]["testing"].container is not updater["options"]
    clone["options"]["testing"].detach()
    assert "testing" not in str(clone)
    assert "testing" in str(updater)
    clone.add_section("other")
    assert "other" in clone
    assert "other" not in updater
    assert str(updater) == dedent(example)


def test_section_comment():
    section = """\
    [section0] # section comment
    key = value
    """

    updater = ConfigUpdater()
    updater.read_string(dedent(section))

    updater["section0"].name = "section1"

    expected = """\
    [section1] # section comment
    key = value
    """
    assert str(updater) == dedent(expected)
    assert updater["section1"].raw_comment == " # section comment"

    updater["section1"].raw_comment = " # new comment"
    expected = """\
    [section1] # new comment
    key = value
    """
    assert str(updater) == dedent(expected)


def test_setitem_detached_option():
    existing = """\
    [section0]
    option0 = 0
    option1 = # No value
    """

    template1 = """\
    [section1]
    option1 = 1
    """

    target = ConfigUpdater()
    target.read_string(dedent(existing))

    source1 = ConfigUpdater()
    source1.read_string(dedent(template1))

    option1 = source1["section1"]["option1"].detach()
    target["section0"]["option1"] = option1
    assert target["section0"]["option1"].value == "1"


def test_comments_in_multiline_values():
    indented_case = """\
    [header]
    install_requires =
        importlib-metadata; python_version<"3.8"
        #Adding some comments here that are perfectly valid.
        some-other-dependency
    """
    unindented_case = """\
    [header]
    install_requires =
        importlib-metadata; python_version<"3.8"
    #Adding some comments here that are perfectly valid.
        some-other-dependency
    """
    error_case_if_no_value = """\
    [header]
    install_requires =
        importlib-metadata; python_version<"3.8"
    #Adding some comments here that are perfectly valid.
    some-other-dependency
    """
    parser = ConfigParser(allow_no_value=False)
    updater = ConfigUpdater(allow_no_value=False)

    parser.read_string(dedent(indented_case))
    updater.read_string(dedent(indented_case))
    assert str(updater) == dedent(indented_case)

    parser.read_string(dedent(unindented_case))
    updater.read_string(dedent(unindented_case))
    assert str(updater) == dedent(unindented_case)

    with pytest.raises(configparser.ParsingError):
        parser.read_string(dedent(error_case_if_no_value))
    with pytest.raises(ParsingError):
        updater.read_string(dedent(error_case_if_no_value))

    parser = ConfigParser(allow_no_value=True)
    updater = ConfigUpdater(allow_no_value=True)

    parser.read_string(dedent(indented_case))
    updater.read_string(dedent(indented_case))
    assert str(updater) == dedent(indented_case)

    parser.read_string(dedent(unindented_case))
    updater.read_string(dedent(unindented_case))
    assert str(updater) == dedent(unindented_case)

    parser.read_string(dedent(error_case_if_no_value))
    updater.read_string(dedent(error_case_if_no_value))
    assert str(updater) == dedent(error_case_if_no_value)


def test_modify_multiline_value():
    ml_value = """\
    [metadata]
    classifiers =
        Development Status :: 3 - Alpha
        #Development Status :: 4 - Beta
        #Development Status :: 5 - Production/Stable
        Programming Language :: Python :: 3 :: Only
        Programming Language :: Python :: 3
        Programming Language :: Python :: Implementation :: CPython
        Programming Language :: Python :: Implementation :: PyPy
        License :: OSI Approved :: MIT License
    """
    ml_value = dedent(ml_value)
    updater = ConfigUpdater()
    updater.read_string(ml_value)

    with pytest.raises(AssignMultilineValueError):
        updater["metadata"]["classifiers"].value += "License :: OSI Approved :: BSD"

    new_classifiers = updater["metadata"]["classifiers"].value.strip().split("\n")
    new_classifiers += ["Topic :: Utilities"]
    updater["metadata"]["classifiers"].set_values(new_classifiers)
    ml_value += "    Topic :: Utilities\n"
    assert str(updater) == ml_value

    updater["metadata"]["classifiers"].value = "new_value"
    updater["metadata"]["classifiers"].value += "_and_more"
    expected = """\
    [metadata]
    classifiers = new_value_and_more
    """
    assert str(updater) == dedent(expected)


def test_append_to_multi_line_value():
    cfg = """\
    [metadata]
    classifiers =
        Development Status :: 3 - Alpha
        #Development Status :: 4 - Beta
        #Development Status :: 5 - Production/Stable
        Programming Language :: Python :: 3 :: Only
        Programming Language :: Python :: 3
        Programming Language :: Python :: Implementation :: CPython
        Programming Language :: Python :: Implementation :: PyPy
        License :: OSI Approved :: MIT License
    """
    cfg = dedent(cfg)
    updater = ConfigUpdater()
    updater.read_string(cfg)
    updater["metadata"]["classifiers"].append("Topic :: Utilities")
    cfg += "    Topic :: Utilities\n"
    assert str(updater) == cfg


def test_append_to_comma_separated_value():
    cfg = """\
    [metadata]
    classifiers = terminal, developers
    """
    cfg = dedent(cfg)
    updater = ConfigUpdater()
    updater.read_string(cfg)
    option = updater["metadata"]["classifiers"]
    option.append("gui", separator=", ")

    cfg_out = """\
    [metadata]
    classifiers = terminal, developers, gui
    """
    cfg_out = dedent(cfg_out)
    assert str(updater) == cfg_out


def test_append_to_no_multi_line_value():
    cfg_in = """\
    [main]
    key = value1
    """
    cfg_out = """\
    [main]
    key =
        value1
        new_value
    """
    cfg_in, cfg_out = dedent(cfg_in), dedent(cfg_out)
    updater = ConfigUpdater()
    updater.read_string(cfg_in)
    updater["main"]["key"].append("new_value")

    target = ConfigUpdater()
    target.read_string(cfg_out)
    assert str(updater) == str(target)

    updater["main"]["key"].append("new_value2")
    cfg_out += "    new_value2\n"
    assert str(updater) == cfg_out


def test_as_list_multi_line():
    cfg = """\
    [metadata]
    no_value
    single_value = 1
    classifiers =
        Development Status :: 3 - Alpha
        #Development Status :: 4 - Beta
    """
    cfg = dedent(cfg)
    updater = ConfigUpdater(allow_no_value=True)
    updater.read_string(cfg)

    meta = updater["metadata"]
    assert meta["no_value"].as_list() == []
    assert meta["single_value"].as_list() == ["1"]
    assert meta["classifiers"].as_list() == [
        "Development Status :: 3 - Alpha",
        "#Development Status :: 4 - Beta",
    ]


def test_as_list_comma_separated():
    cfg = """\
    [metadata]
    classifiers = terminal, developers
    """
    cfg = dedent(cfg)
    updater = ConfigUpdater()
    updater.read_string(cfg)
    option = updater["metadata"]["classifiers"]
    assert option.as_list(",") == ["terminal", "developers"]


def test_indented_section():
    cfg = """\
    [section0]

        [section1]
            key = value
    """

    updater = ConfigUpdater()
    updater.read_string(dedent(cfg))

    assert str(updater) == dedent(cfg)


def test_section_without_end_of_line():
    cfg = """\
    [section]"""

    updater = ConfigUpdater()
    updater.read_string(dedent(cfg))

    assert str(updater) == dedent(cfg)


def test_set_values_for_existing_multiline_value():
    cfg_newline = """\
    [section]
    options =
        option1
        option2_typo
    """
    exp_cfg_newline = """\
    [section]
    options =
        option1
        option2
    """
    cfg_no_newline = """\
    [section]
    options = option1
              option2_typo
    """
    exp_cfg_no_newline = """\
    [section]
    options = option1
              option2
    """
    cfg_newline_comment = """\
    [section]
    options = # comment
        option1 # comment
        option2_typo
    """
    exp_cfg_newline_comment = """\
    [section]
    options =
        # comment
        option1 # comment
        option2
    """
    cfg_no_newline_comment = """\
    [section]
    options = option1 # comment
              option2_typo
    """
    exp_cfg_no_newline_comment = """\
    [section]
    options = option1 # comment
              option2
    """

    def test_no_change_but_option2_fixed(cfg, exp_cfg, prepend_newline):
        updater = ConfigUpdater()
        updater.read_string(dedent(cfg))
        options = updater["section"]["options"].as_list()
        options[-1] = "option2"  # fix typo
        updater["section"]["options"].set_values(
            options, prepend_newline=prepend_newline
        )

        assert str(updater) == dedent(exp_cfg)

    test_no_change_but_option2_fixed(cfg_newline, exp_cfg_newline, True)
    test_no_change_but_option2_fixed(cfg_no_newline, exp_cfg_no_newline, False)
    test_no_change_but_option2_fixed(cfg_newline_comment, exp_cfg_newline_comment, True)
    test_no_change_but_option2_fixed(
        cfg_no_newline_comment, exp_cfg_no_newline_comment, False
    )
    test_no_change_but_option2_fixed(cfg_newline, exp_cfg_no_newline, False)
    test_no_change_but_option2_fixed(cfg_no_newline, exp_cfg_newline, True)

    cfg_single_value_at_first = """\
    [section]
    options = option1
    """
    exp_cfg_single_value_at_first = """\
    [section]
    options =
        option1
        option2
    """
    updater = ConfigUpdater()
    updater.read_string(dedent(cfg_single_value_at_first))
    updater["section"]["options"].append("option2")
    assert str(updater) == dedent(exp_cfg_single_value_at_first)

    exp_cfg_no_newline_indent2 = """\
    [section]
    options = option1
      option2
    """
    updater = ConfigUpdater()
    updater.read_string(dedent(cfg_no_newline))
    options = updater["section"]["options"].as_list()
    options[-1] = "option2"  # fix typo
    updater["section"]["options"].set_values(
        options, prepend_newline=False, indent=2 * " "
    )
    assert str(updater) == dedent(exp_cfg_no_newline_indent2)
