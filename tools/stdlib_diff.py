"""Simple command line utility to help finding the differences between
ConfigUpdater and ConfigParser.

The output of this script is similar to the output produced by
`git format-patch`. This means that programs like `delta` or `bat`
can be used to add some format highlighting to the output. Examples:

    %(prog)s | delta --side-by-side
    %(prog)s | bat -l diff

Alternatively https://github.com/megatops/PatchViewer can also be used.

[delta]: https://github.com/dandavison/delta
[bat]: https://github.com/sharkdp/bat
[PathViewer]:  https://github.com/megatops/PatchViewer
"""
from __future__ import annotations

import argparse
import os.path
import sys
from configparser import ConfigParser, SectionProxy
from dataclasses import dataclass
from difflib import SequenceMatcher
from inspect import getmembers, getsourcefile, getsourcelines
from typing import Iterator, Optional, Sequence, Type

try:
    import configupdater  # noqa
except ImportError:
    repo = os.path.dirname(os.path.dirname(__file__))
    sys.path.append(os.path.join(repo, "src"))

from configupdater import ConfigUpdater, Parser, Section
from configupdater.document import Document

COMPARISONS = [
    (Parser, ConfigParser),
    (ConfigUpdater, ConfigParser),
    (Document, ConfigParser),
    (Section, SectionProxy),
]


def diff_all(numlines: int) -> str:
    patches = (diff_class(orig, target, numlines) for (target, orig) in COMPARISONS)
    return "\n\n".join(patches)


def diff_class(orig_cls: Type, changed_cls: Type, numlines: int) -> str:
    diff_fragments = (
        diff_member(name, orig_cls, changed_cls, numlines)
        for name, _ in getmembers(changed_cls)
        if name != "__init__" and name in changed_cls.__dict__
    )
    return "\n".join(d for d in diff_fragments if d)


def diff_member(
    name: str, orig_cls: Type, changed_cls: Type, numlines: int
) -> Optional[str]:
    orig = getattr(orig_cls, name, None)
    changed = getattr(changed_cls, name, None)

    if orig is None or changed is None:
        return None

    if not (callable(orig) and callable(changed)):
        # Not a method
        return None

    orig_code = CodeInfo.inspect(orig)
    changed_code = CodeInfo.inspect(changed)
    title = (
        f"{orig_cls.__module__}:{orig_cls.__qualname__}.{name} | "
        f"{changed_cls.__module__}:{changed_cls.__qualname__}.{name}"
    )

    return "".join(format_patch(orig_code, changed_code, numlines, title))


@dataclass
class CodeInfo:
    lines: Sequence[str]
    file: str
    starting_line: int

    @classmethod
    def inspect(cls, obj) -> "CodeInfo":
        path = "<builtin>"
        try:
            path = getsourcefile(obj) or "<extension>"
            src, start = getsourcelines(obj)
        except TypeError:
            src = [f"# {path} ::: {obj}\n"]
            start = 0
        return cls(src, path, start)


def format_patch(
    source: CodeInfo, target: CodeInfo, numlines: int = 3, title: str = ""
) -> Iterator[str]:
    """Variation of :obj:`difflib.unified_diff` that considers line offsets."""
    started = False
    matcher = SequenceMatcher(None, source.lines, target.lines)
    for group in matcher.get_grouped_opcodes(numlines):
        if not started:
            started = True
            yield f"--- {relativise_path(source.file)}\n"
            yield f"+++ {relativise_path(target.file)}\n"

        first, last = group[0], group[-1]
        source_range = line_range(first[1], last[2], source.starting_line)
        target_range = line_range(first[3], last[4], target.starting_line)
        yield f"@@ -{source_range} +{target_range} @@ {title}".strip() + "\n"

        for tag, i1, i2, j1, j2 in group:
            if tag == "equal":
                for line in source.lines[i1:i2]:
                    yield " " + line
                continue
            if tag in {"replace", "delete"}:
                for line in source.lines[i1:i2]:
                    yield "-" + line
            if tag in {"replace", "insert"}:
                for line in target.lines[j1:j2]:
                    yield "+" + line


def line_range(start, stop, offset):
    length = stop - start
    return f"{offset + start},{length}"  # Lines are counted from 1


def relativise_path(path: str) -> str:
    relative = os.path.relpath(path)
    return relative if len(path) > len(relative) else path


def main():
    cli = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    cli.add_argument(
        "-l",
        "--lines",
        type=int,
        default=3,
        metavar="N",
        dest="numlines",
        help="Set number of context lines (default %(default)s)",
    )
    cli.add_argument("-o", "--output", type=argparse.FileType("w"), default=sys.stdout)
    opts = cli.parse_args()
    with opts.output as f:
        f.write(diff_all(opts.numlines))


if __name__ == "__main__":
    main()
