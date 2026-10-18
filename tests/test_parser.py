import pytest

from configupdater.parser import Parser


def test_syntax_options():
    parser = Parser(allow_no_value=True)
    assert parser.syntax_options["allow_no_value"] is True


def test_syntax_options_read_only():
    parser = Parser(allow_no_value=False)
    with pytest.raises(TypeError, match="does not support item assignment"):
        parser.syntax_options["allow_no_value"] = True
    assert parser.syntax_options["allow_no_value"] is False
