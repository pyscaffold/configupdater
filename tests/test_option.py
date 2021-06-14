from textwrap import dedent

from configupdater import ConfigUpdater


def test_option_add_line():
    # The `add_line` seems to be part of the public API for Option, and since Option
    # does not have a `add_comment` method, instead of creating a builder, users could
    # just think about using `add_line` for that.

    # If the option was created during the parsing phase, this seem to work fine
    # However we have to also guarantee that happens when the option is created
    # afterwards, for example in a __setitem__ context.

    example = """\
    [section]
    option1 = something
    """

    # When the option comes from parsing, everything should work fine
    updater = ConfigUpdater()
    updater.read_string(dedent(example))
    option1 = updater["section"]["option1"]
    option1.add_line("      # comment about option1\n")
    assert "option1 =" in str(option1)
    assert "something" in str(option1)
    assert "comment about option1" in str(option1)

    # If the option comes from __setitem__, things can be more complicated
    updater["section"]["option2"] = "value"
    option2 = updater["section"]["option2"]
    option2.add_line("      # comment about option2\n")
    print("option2:", repr(str(option2)))  # helps with debugging
    assert "option2 =" in str(option2)
    assert "value" in str(option2)
    assert "comment about option2" in str(option2)
