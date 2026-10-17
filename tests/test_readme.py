"""The examples in README.md must run and show the right configurations.

The examples in ``docs/usage.rst`` are checked by ``tox -e doctests``.
"""

import re
from pathlib import Path

README = Path(__file__).parent.parent / "README.md"
CODE_BLOCK = re.compile(r"^```(python|ini)\n(.*?)^```$", re.MULTILINE | re.DOTALL)


def test_readme_examples(tmp_path, monkeypatch):
    # The first example reads a ``setup.cfg`` and changes its author
    (tmp_path / "setup.cfg").write_text("[metadata]\nauthor = Ada Lovelace\n")
    monkeypatch.chdir(tmp_path)

    namespace = {}
    blocks = CODE_BLOCK.findall(README.read_text(encoding="utf-8"))
    assert blocks
    for language, code in blocks:
        if language == "python":
            exec(code, namespace)  # noqa: S102 (our own README)
        else:
            # An ``ini`` block shows ``updater`` after the preceding examples
            assert str(namespace["updater"]).strip() == code.strip()
