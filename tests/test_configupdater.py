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
    parser.update()
    new_mtime = os.path.getmtime(setup_cfg_path)
    assert old_mtime != new_mtime


def test_str(setup_cfg_path, setup_cfg):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    output = str(parser)
    assert output == setup_cfg


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

