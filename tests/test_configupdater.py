import os.path

from configupdater import ConfigUpdater

from conftest import parser_to_str


def test_reade_write_no_changes(setup_cfg_path, setup_cfg):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    result = parser_to_str(parser)
    assert result == setup_cfg


def test_update_no_changes(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    old_mtime = os.path.getmtime(setup_cfg_path)
    parser.update_file()
    new_mtime = os.path.getmtime(setup_cfg_path)
    assert old_mtime != new_mtime


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


def test_sections(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    exp_sections = ['metadata', 'options', 'options.packages.find',
                    'options.extras_require', 'test', 'tool:pytest',
                    'aliases', 'bdist_wheel', 'build_sphinx',
                    'devpi:upload', 'flake8', 'pyscaffold']
    assert parser.sections() == exp_sections


def test_get_section(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    section = parser['metadata']
    assert section.entries


def test_has_option(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    assert parser.has_option('metadata', 'author')
    assert not parser.has_option('metadata', 'coauthor')
    assert not parser.has_option('nonexistent_section', 'key')





test_cfg_in = """
[default]
key = 1
"""

test_cfg_out = """
[default]
key = 2
"""


# def test_value_change():
#     parser = ConfigUpdater()
#     parser.read_string(test_cfg_in)
#     parser

