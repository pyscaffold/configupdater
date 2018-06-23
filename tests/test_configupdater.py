import os.path
from collections import Counter

from configupdater import ConfigUpdater
from configupdater.configupdater import LineKeeper

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


def test_line_keeper():
    counter = Counter()

    def hook():
        counter['count'] += 1

    keeper = LineKeeper(hook=hook)
    assert bool(keeper) is False
    assert len(keeper) == 0
    keeper.clear()
    assert counter['count'] == 0
    keeper.append('A')
    assert keeper[0] == 'A'
    assert counter['count'] == 1
    keeper.extend(['B', 'C'])
    assert counter['count'] == 2
    keeper[0] = 42
    assert counter['count'] == 3
    keeper.clear()
    assert counter['count'] == 4
    keeper.insert(0, 'A')
    assert keeper[0] == 'A'
    assert counter['count'] == 5
    assert keeper.index('A') == 0
    assert counter['count'] == 5
