import configupdater
from configupdater.configupdater import ConfigParser

from IPython import embed

from conftest import parser_to_str


def test_reading(setup_cfg_path, setup_cfg):
    parser = ConfigParser()
    parser.read(setup_cfg_path)
    result = parser_to_str(parser)
    assert result == setup_cfg
