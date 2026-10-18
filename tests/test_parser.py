import time
from configparser import ParsingError

import pytest

from configupdater import ConfigUpdater
from configupdater.parser import Parser


def test_syntax_options():
    parser = Parser(allow_no_value=True)
    assert parser.syntax_options["allow_no_value"] is True


def test_syntax_options_read_only():
    parser = Parser(allow_no_value=False)
    with pytest.raises(TypeError, match="does not support item assignment"):
        parser.syntax_options["allow_no_value"] = True
    assert parser.syntax_options["allow_no_value"] is False


def test_option_regex_does_not_backtrack():
    # A long line with many spaces but no delimiter took quadratic time to fail to
    # match, ~10s for this one (CPython gh-146333). Now it fails within milliseconds.
    content = "[section]\n" + "x" + " " * 50_000 + "y\n"
    start = time.perf_counter()
    with pytest.raises(ParsingError):
        ConfigUpdater().read_string(content)
    assert time.perf_counter() - start < 2


@pytest.mark.parametrize(
    ("delimiters", "line", "key", "value"),
    [
        (("=", ":"), "multi word key = value", "multi word key", "value"),
        (("=", ":"), "a b : c d", "a b", "c d"),
        (("=", ":"), "k = a = b", "k", "a = b"),
        (("=>", "::"), "x=y => z", "x=y", "z"),
        # whitespace delimiters split at the first one, as in Python 3.15
        ((" ",), "multi word value", "multi", "word value"),
        (("\t", " "), "a b\tc", "a", "b\tc"),
    ],
)
def test_option_regex_splits_like_configparser(delimiters, line, key, value):
    updater = ConfigUpdater(delimiters=delimiters)
    updater.read_string(f"[section]\n{line}\n")
    assert updater["section"].keys() == {key}
    assert updater["section"][key].value == value


def test_option_regex_multi_word_key_without_value():
    updater = ConfigUpdater(allow_no_value=True)
    updater.read_string("[section]\nmulti word key\n")
    assert updater["section"]["multi word key"].value is None
