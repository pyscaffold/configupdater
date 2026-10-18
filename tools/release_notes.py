#!/usr/bin/env python3
"""Print the notes for the GitHub release of a version from ``CHANGELOG.rst``.

The release workflow (``.github/workflows/publish-package.yml``) runs it with the
version of the pushed tag, e.g. ``python3 tools/release_notes.py 4.0``. It prints the
entries of the ``Version 4.0`` section, whose bullet lists read as Markdown as they
are. A pre-release such as ``4.0b1`` gets the section of ``4.0``, which may still be
marked as ``(unreleased)``. Without a matching section it exits with an error, so a
final release is not published while its section is still marked as unreleased.
"""

import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.rst"
HEADING = re.compile(r"^Version (?P<title>.+)\n=+\n", re.MULTILINE)
PRE_RELEASE = re.compile(r"(?P<release>\d+(?:\.\d+)*)(?:a|b|rc)\d+")


def release_notes(changelog: str, version: str) -> str:
    """Return the entries of the section for ``version`` in ``changelog``.

    Args:
        changelog: content of ``CHANGELOG.rst``
        version: version without the ``v`` of the tag, e.g. ``4.0`` or ``4.0b1``

    Raises:
        LookupError: if ``changelog`` has no section for ``version``
    """
    titles = [version]
    if pre_release := PRE_RELEASE.fullmatch(version):
        release = pre_release["release"]
        titles += [release, f"{release} (unreleased)"]

    headings = list(HEADING.finditer(changelog))
    ends = [heading.start() for heading in headings[1:]] + [len(changelog)]
    sections = {
        heading["title"]: changelog[heading.end() : end]
        for heading, end in zip(headings, ends, strict=True)
    }
    for title in titles:
        if title in sections:
            return sections[title].strip() + "\n"
    msg = f"{CHANGELOG.name} has no section 'Version {version}'"
    raise LookupError(msg)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(f"usage: {sys.argv[0]} VERSION")
    version = sys.argv[1]
    try:
        notes = release_notes(CHANGELOG.read_text(encoding="utf-8"), version)
    except LookupError as ex:
        sys.exit(f"error: {ex}")
    print(notes, end="")


if __name__ == "__main__":
    main()
