import os.path

from configupdater import ConfigUpdater


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
    assert [section for section in parser] == exp_sections
    assert parser.sections() == exp_sections
    assert len(parser) == len(exp_sections)


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


def test_get_option(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    options = parser.options('options.packages.find')
    exp_options = ['where', 'exclude']
    assert options == exp_options


def test_get_method(setup_cfg_path):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    value = parser.get('metadata', 'license').value
    assert value == 'mit'


test_cfg_in = """
[default]
key = 1
"""

test_cfg_out = """
[default]
key = 2
"""


def test_value_change():
    parser = ConfigUpdater()
    parser.read_string(test_cfg_in)
    assert parser['default']['key'].value == '1'
    parser['default']['key'].value = '2'
    assert str(parser) == test_cfg_out


def test_del_option():
    parser = ConfigUpdater()
    parser.read_string(test_cfg_in)
    del parser['default']['key']
    assert str(parser) == "\n[default]\n"
