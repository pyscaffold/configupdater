from textwrap import dedent

from configupdater import ConfigUpdater


def test_transfering_blocks_between_elements():
    # Let's say a user have a big new section that it wants to insert in an existing
    # document. Instead of programmatically creating this new section using the builder
    # API, they might be tempted to parse this new section from template files.

    existing = """\
    [section0]
    option0 = 0
    """

    template1 = """\
    [section1]
    option1 = 1
    """

    template2 = """\
    [section2]
    option2 = 2
    # comment
    """

    target = ConfigUpdater()
    target.read_string(dedent(existing))

    source1 = ConfigUpdater()
    source1.read_string(dedent(template1))

    source2 = ConfigUpdater()
    source2.read_string(dedent(template2))

    target["section1"] = source1["section1"].remove()
    assert "section1" in target

    target["section1"].add_after.section(source2["section2"].remove())
    # Help with debugging
    print(f"@@@ target:\n{target}")
    print(f"@@@ source1:\n{source1}")
    print(f"@@@ source2:\n{source2}")
    assert "section2" not in source1
    assert "section2" in target
