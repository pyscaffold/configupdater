# CLAUDE.md

Guidance for AI coding agents working in this repository.

## Project

**ConfigUpdater** is a pure-Python library (no runtime dependencies) for
*format-preserving* editing of INI/`.cfg` files. Its API mirrors the stdlib's
`configparser.ConfigParser`, but comments, blank lines, key casing and ordering
are kept, so a file can be read, modified and written back with minimal diffs.
It belongs to the PyScaffold organization (PyScaffold uses it to edit `setup.cfg`).

The project was generated with PyScaffold 4.6: do not edit the `[pyscaffold]`
section of `setup.cfg` or the `requires` in `pyproject.toml`.
Packaging metadata lives in `setup.cfg`; the version comes from git tags via
`setuptools_scm`.

## Commands

All tasks are defined in `tox.ini`. tox is not installed globally here, so run it
through uv, using a Python ≥ 3.11 (see "Python version support" below):

```bash
uvx --python 3.12 --with tox-uv tox -e default            # tests (pytest -k "not system")
uvx --python 3.12 --with tox-uv tox -e default -- tests/test_option.py::test_name
uvx --python 3.12 --with tox-uv tox -e typecheck          # mypy src tools
uvx --python 3.12 --with tox-uv tox -e lint               # pre-commit run --all-files
uvx --python 3.12 --with tox-uv tox -e docs               # sphinx html → docs/_build/html
uvx --python 3.12 --with tox-uv tox -e doctests
uvx --python 3.12 --with tox-uv tox -e clean,build        # sdist + wheel in dist/
uvx --python 3.12 --with tox-uv tox -e py312-diff         # diff vs. stdlib ConfigParser (tools/stdlib_diff.py)
```

Notes:
- pytest options come from `[tool:pytest]` in `setup.cfg` (coverage is always on,
  `--verbose`). `pytest-randomly` shuffles test order; add `-p no:randomly` when
  debugging order-dependent failures. `pytest-xdist` is available (`-n auto`).
- `tox -e lint` **rewrites files** (ruff `--fix`, ruff-format, pyupgrade, codespell
  `-w`, end-of-file/trailing-whitespace fixers). Run it deliberately and review the diff.
- `tox -e publish` uploads to (Test)PyPI. Never run it; releases happen by pushing a
  `v*` tag, which triggers `.github/workflows/publish-package.yml`. Never create or
  push tags without being asked.
- CI runs on Cirrus (`.cirrus.yml`): build + lint + typecheck on Linux 3.11, tests on
  Linux 3.8/3.10/3.12, conda, macOS, FreeBSD and Windows. pre-commit.ci pushes
  autofix and autoupdate commits to PRs.

## Architecture

Source is in `src/configupdater/` (src layout). The document is a tree of *blocks*:

| Module | Contents |
|---|---|
| `block.py` | `Block` base class (raw `_lines` + back-reference to its container), `Comment`, `Space`, and the `NotAttachedError` / `AlreadyAttachedError` / `AssignMultilineValueError` exceptions |
| `container.py` | `Container[T]`: ordered `_structure` list of child blocks, deepcopy support |
| `option.py` | `Option(Block)`: key/value pair incl. multi-line values (`as_list`, `append`, `set_values`) |
| `section.py` | `Section(Block, Container, MutableMapping[str, Option])` |
| `document.py` | `Document(Container, MutableMapping[str, Section])`: ConfigParser-like API (`get`, `items`, `has_option`, `set`, `remove_option`, `to_dict`, `validate_format`, …) |
| `configupdater.py` | `ConfigUpdater(Document)`: adds file I/O (`read`, `read_file`, `read_string`, `write`, `update_file`) and stores parser options in `syntax_options` |
| `parser.py` | `Parser`: builds the block tree. Adapted from CPython's `configparser` (its license is appended to `LICENSE.txt`); raises the stdlib `configparser` exceptions |
| `builder.py` | `BlockBuilder`: fluent insertion API behind `block.add_before`, `block.add_after`, `section.insert_at(idx)` |

Key invariants. Changes must preserve them:
- **Round-trip fidelity.** An unmodified document serializes byte-identically to its
  input (`str(updater) == original`). `Block.__str__` returns the original lines
  unless the block is `updated`; only updated blocks are re-rendered.
- **Single parent.** A block is attached to exactly one container. `attach()` raises
  `AlreadyAttachedError`; to move a block use `detach()` or `copy.deepcopy`.
  `container_idx` locates blocks by identity (`is`), because blocks compare equal
  by their string content.
- **Option keys** are normalized through `Document.optionxform` (default `str.lower`);
  `Option.raw_key` keeps the original spelling. Section names are case-sensitive.
  `optionxform` must be idempotent, because keys are often transformed twice (e.g.
  `Document.set` → `Section.set`). In `Section`, `s[key]` get/set/del apply it, but
  `key in s` and `s.get(key)` expect an already transformed key (asserted in
  `tests/test_optionxform.py`).
- `updater["sect"]["key"]` returns an `Option`, not a string. Use `.value`.
- Deliberately **not** supported: interpolation, `DEFAULT` section propagation,
  value type conversion, non-strict mode (duplicate sections/options).
- `write()` and `update_file()` call `validate_format()` first, which re-parses
  `str(self)` with the stdlib `ConfigParser`.

Public API: `configupdater/__init__.py` re-exports the `__all__` of `configupdater.py`
and `parser.py`; new public names must be added there. The package ships `py.typed`,
so type annotations are part of the API and `mypy src tools` must pass.

`tools/stdlib_diff.py` prints how ConfigUpdater's methods diverge from their
ConfigParser counterparts. It is useful when porting upstream parser fixes.

## Python version support

Declared support is Python 3.8+ (classifiers, CI matrix, `pyupgrade --py38-plus`;
`python_requires` in `setup.cfg` still says `>=3.6`).

**Known issue (since commit `99c0a76`, Oct 2026):** a pre-commit.ci autofix with
ruff 0.17 rewrote the sources to use `typing.Self` and runtime-evaluated `X | None`
annotations, so the package currently fails to import on Python < 3.11. Ruff has no
`target-version` configured, so autofixes can introduce syntax newer than the
supported minimum again. When touching typing code, keep it importable on the
minimum supported version (e.g. `from __future__ import annotations`,
`typing_extensions`, or a pinned ruff `target-version`). Legacy
`if sys.version_info[:2] >= (3, 9): List = list` shims remain in several modules;
don't add new ones.

## Conventions

- Formatting/linting: ruff + ruff-format (Black style, line length 88), isort
  profile black with `configupdater` as first-party. Flake8 settings in `setup.cfg`
  are legacy.
- Docstrings use Google style (`Args:`, `Returns:`, `Raises:`) with Sphinx roles;
  `docs/api.rst` autodocs the package.
- Tests are plain pytest functions in `tests/`. Inline configs use `dedent(...)`;
  `tests/test_setup.cfg` (via the `setup_cfg_path` / `setup_cfg` fixtures in
  `conftest.py`) is the round-trip fixture. Compare against stdlib `ConfigParser`
  where behavior should match. Every bugfix needs a regression test; name it after
  the GitHub issue when there is one (e.g. `test_update_file_issue_68`).
- User-visible changes get an entry in `CHANGELOG.rst` under the next version,
  referencing the issue (`issue #N`).
- `README.md` is the PyPI long description. `README.rst` is a stale leftover.
- Untracked local artifacts (`docs/html/`, `site/`, `*.bak`, `build/`, `.tox/`) are
  not part of the project. Ignore them and don't commit them.
