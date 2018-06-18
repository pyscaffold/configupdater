from configupdater import ConfigUpdater

from IPython import embed

from conftest import parser_to_str


def test_reading(setup_cfg_path, setup_cfg):
    parser = ConfigUpdater()
    parser.read(setup_cfg_path)
    result = parser_to_str(parser)
    embed()
    assert result == setup_cfg
