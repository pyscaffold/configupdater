import argparse
import sys
from configparser import ConfigParser, SectionProxy
from difflib import HtmlDiff
from inspect import getsourcelines, getsourcefile, getmembers
from typing import Collection, Optional, Type

from bs4 import BeautifulSoup

from configupdater import ConfigUpdater, Parser, Section
from configupdater.document import Document

COMPARISONS = [
    (Parser, ConfigParser),
    (ConfigUpdater, ConfigParser),
    (Document, ConfigParser),
    (Section, SectionProxy),
]


def meta_info(obj):
    path = getsourcefile(obj)
    src, start = getsourcelines(obj)
    return src, path, start


def diff_member(
    name: str,
    orig_cls: Type,
    changed_cls: Type,
    context: bool,
    numlines: int,
) -> Optional[str]:
    orig = getattr(orig_cls, name, None)
    changed = getattr(changed_cls, name, None)

    if orig is None or changed is None:
        return None

    if not (callable(orig) and callable(changed)):
        # Not a method
        return None

    try:
        orig_src, orig_file, orig_line = meta_info(orig)
        changed_src, changed_file, changed_line = meta_info(changed)
    except TypeError:
        # buitins will fail if inspected
        return None

    diff_table = HtmlDiff(tabsize=4, charjunk=lambda _: False).make_table(
        orig_src,
        changed_src,
        fromdesc=f"{orig_file}:{orig_line}",
        todesc=f"{changed_file}:{changed_line}",
        context=context,
        numlines=numlines,
    )

    mod_name = changed_cls.__module__
    qual_name = changed_cls.__qualname__

    return f"""
    <section id="{name}">
        <header>
            <h2><pre>{mod_name}:{qual_name}.{name}<pre></h2>
        </header>

        {diff_table}
    </section>
    """


def diff(
    orig_cls: Type,
    changed_cls: Type,
    context: bool,
    numlines: int,
) -> str:
    diff_fragments = (
        diff_member(name, orig_cls, changed_cls, context, numlines)
        for name, _ in getmembers(changed_cls)
        if name != "__init__" and name in changed_cls.__dict__
    )
    return "\n".join(d for d in diff_fragments if d)


def diff_all(context: bool, numlines: int) -> str:
    content_str = (
        "\n".join(
            diff(orig, target, context, numlines) for (target, orig) in COMPARISONS
        )
        .encode("utf-8", "xmlcharrefreplace")
        .decode("utf-8")
    )

    content = BeautifulSoup(f"<main>{content_str}<main>", "html.parser").main
    page = BeautifulSoup(HtmlDiff(tabsize=4).make_file("", ""), "html.parser")
    page.find("table").replace_with(content)
    return page.prettify()


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument(
        "--no-context",
        action="store_false",
        dest="context",
        default=True,
        help="Produce a full diff",
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
        f.write(diff_all(opts.context, opts.numlines))


__name__ == "__main__" and main()
