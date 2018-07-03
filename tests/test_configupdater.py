import os.path

from configupdater import ConfigUpdater, NoConfigFileReadError, ParsingError
from configupdater.configupdater import Section, Option, DuplicateSectionError

import pytest


def test_reade_write_no_changes(setup_cfg_path, setup_cfg):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    assert str(parser) == setup_cfg


def test_update_no_changes(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    old_mtime = os.path.getmtime(setup_cfg_path)
    parser.update_file()
    new_mtime = os.path.getmtime(setup_cfg_path)
    assert old_mtime != new_mtime


def test_update_no_cfg():
    parser = ConfigUpdater()
    with pytest.raises(NoConfigFileReadError):
        parser.update_file()


def test_str(setup_cfg_path, setup_cfg):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    output = str(parser)
    assert output == setup_cfg


def test_has_section(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    assert parser.has_section('metadata')
    assert not parser.has_section('nonexistent_section')


def test_contains_section(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    assert 'metadata' in parser


def test_sections(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    exp_sections = ['metadata', 'options', 'options.packages.find',
                    'options.extras_require', 'test', 'tool:pytest',
                    'aliases', 'bdist_wheel', 'build_sphinx',
                    'devpi:upload', 'flake8', 'pyscaffold']
    assert parser.sections() == exp_sections


def test_len_section(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    # we test ne number of blocks, not sections
    assert len(parser) == 14


def test_iter_section(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    # we test ne number of blocks, not sections
    assert len([block for block in parser]) == 14


def test_get_section(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    section = parser['metadata']
    assert section._structure


def test_has_option(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    assert parser.has_option('metadata', 'author')
    assert not parser.has_option('metadata', 'coauthor')
    assert not parser.has_option('nonexistent_section', 'key')


def test_contains_options(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    section = parser['metadata']
    assert 'author' in section
    assert 'wrong_option' not in section


def test_len_option(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    section = parser['metadata']
    # we test ne number of entries, not options
    assert len(section) == 12


def test_iter_option(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    section = parser['metadata']
    # we test ne number of entries, not options
    assert len([entry for entry in section]) == 12


def test_get_option(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    options = parser.options('options.packages.find')
    exp_options = ['where', 'exclude']
    assert options == exp_options


def test_items(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    sect_names, sects = zip(*parser.items())
    exp_sect_namess= [
        'metadata', 'options', 'options.packages.find',
        'options.extras_require', 'test', 'tool:pytest',
        'aliases', 'bdist_wheel', 'build_sphinx',
        'devpi:upload', 'flake8', 'pyscaffold']
    assert list(sect_names) == exp_sect_namess
    assert all([isinstance(s, Section) for s in sects])

    opt_names, opts = zip(*parser.items('devpi:upload'))
    exp_opt_names = ['no-vcs', 'formats']
    assert list(opt_names) == exp_opt_names
    assert all([isinstance(o, Option) for o in opts])


def test_get_method(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    value = parser.get('metadata', 'license').value
    assert value == 'mit'


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


def test_value_change():
    parser = ConfigUpdater()
    parser.read_string(test1_cfg_in)
    assert parser['default']['key'].value == '1'
    parser['default']['key'].value = '2'
    assert str(parser) == test1_cfg_out
    # try another way
    section = parser['default']
    section['key'] = '1'
    assert str(parser) == test1_cfg_in


def test_remove_option():
    parser = ConfigUpdater()
    parser.read_string(test1_cfg_in)
    parser.remove_option('default', 'key')
    assert str(parser) == test1_cfg_out_removed
    parser.remove_option('default', 'non_existent_key')
    parser.read_string(test1_cfg_in)
    del parser['default']['key']
    assert str(parser) == test1_cfg_out_removed


def test_set_option():
    parser = ConfigUpdater()
    parser.read_string(test1_cfg_in)
    parser.set('default', 'key', '1')
    assert parser['default']['key'].value == '1'
    parser.set('default', 'key', 2)
    assert parser['default']['key'].value == 2
    assert str(parser) == test1_cfg_out
    parser.set('default', 'key')
    assert parser['default']['key'].value is None
    assert str(parser) == test1_cfg_out_none
    parser.read_string(test1_cfg_in)
    parser.set('default', 'other_key', 3)
    assert str(parser) == test1_cfg_out_added


def test_del_option():
    parser = ConfigUpdater()
    parser.read_string(test1_cfg_in)
    del parser['default']['key']
    assert str(parser) == "\n[default]\n"


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


def test_remove_section():
    parser = ConfigUpdater()
    parser.read_string(test2_cfg_in)
    del parser['section2']
    assert str(parser) == test2_cfg_out


test_wrong_cfg = """
[strange section]
a
"""


def test_handle_error():
    parser = ConfigUpdater(allow_no_value=False)
    with pytest.raises(ParsingError):
        parser.read_string(test_wrong_cfg)


def test_validate_format(setup_cfg_path):
    parser = ConfigUpdater(allow_no_value=False)
    parser.read(setup_cfg_path)
    parser.validate_format()
    parser.set('metadata', 'author')
    with pytest.raises(ParsingError):
        parser.validate_format()


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
    parser = ConfigUpdater()
    parser.read_string(test3_cfg_in)
    parser['section'].add_before.comment('comment of section')
    parser['section'].add_after.comment('# comment after section\n')
    assert str(parser) == test3_cfg_out


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
    parser = ConfigUpdater()
    parser.read_string(test4_cfg_in)
    with pytest.raises(ValueError):
        parser['section'].add_before.option('key0', 0)
    parser['section']['key1'].add_before.option('key0', 0)
    parser['section']['key1'].add_after.option('key2')
    assert str(parser) == test4_cfg_out


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
    parser = ConfigUpdater()
    parser.read_string(test5_cfg_in)
    parser['section1'].add_before.space(2)
    parser['section1']['key1'].add_after.space(1)
    assert str(parser) == test5_cfg_out


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


def test_add_before_after_section():
    parser = ConfigUpdater()
    parser.read_string(test6_cfg_in)
    with pytest.raises(ValueError):
        parser['section2']['key1'].add_before.section('section1')
    parser['section2'].add_before.section('section1')
    parser['section1']['key1'] = 42
    parser['section2'].add_after.section('section3').space(1)
    assert str(parser) == test6_cfg_out


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
    parser = ConfigUpdater()
    parser.read_string(test7_cfg_in)
    with pytest.raises(DuplicateSectionError):
        parser.add_section('section1')
    parser.add_section('section2')
    parser['section2']['key1'] = 1
    assert str(parser) == test7_cfg_out
