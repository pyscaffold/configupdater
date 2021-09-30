import pytest

from configupdater.parser import Parser


def test_syntax_options():
    parser = Parser(allow_no_value=True)
    assert parser.syntax_options["allow_no_value"] is True


def test_syntax_options_read_only():
    parser = Parser(allow_no_value=False)
    with pytest.raises(Exception) as exc_info:
        parser.syntax_options["allow_no_value"] = True
    assert "assignment" in str(exc_info.value)
    assert parser.syntax_options["allow_no_value"] is False
