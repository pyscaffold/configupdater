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
- Releases happen by pushing a `v*` tag, which triggers
  `.github/workflows/publish-package.yml`: it builds the package and uploads it to
  PyPI via trusted publishing (no API token) in the `pypi` environment. Never upload
  to PyPI yourself, and never create or push tags without being asked.
- CI runs on GitHub Actions (`.github/workflows/ci.yml`): build and inspect the
  sdist/wheel, run the tests against the wheel on Linux, macOS and Windows for every
  Python version in the classifiers, and typecheck on the oldest one. Coverage goes
  to Coveralls. The `All required checks pass` job is the single status check for
  branch protection. Actions are pinned to commit SHAs, which Dependabot updates.
  Lint runs on pre-commit.ci, which pushes autofix and autoupdate commits to PRs.

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
- **Mirror ConfigParser.** Behavior matches the stdlib `configparser.ConfigParser`
  as closely as possible. Deviate only where format preservation requires it (e.g.
  `Option` objects instead of strings, keeping the spelling of parsed keys) or for
  the deliberately unsupported features below, and document every deviation in the
  docstring and, if it is user-visible, in the changelog. When in doubt, check what
  ConfigParser does and add a test that compares against it.
- **Round-trip fidelity.** An unmodified document serializes byte-identically to its
  input (`str(updater) == original`). `Block.__str__` returns the original lines
  unless the block is `updated`; only updated blocks are re-rendered.
- **Single parent.** A block is attached to exactly one container. `attach()` raises
  `AlreadyAttachedError`; to move a block use `detach()` or `copy.deepcopy`.
  `container_idx` locates blocks by identity (`is`), because blocks compare equal
  by their string content.
- **Option keys** are normalized through `Document.optionxform` (default `str.lower`);
  `Option.raw_key` keeps the original spelling, also for options created with
  `s[key] = v`, `set` or the builder. Section names are case-sensitive. Each public
  `Section` method that takes a key (`s[key]` get/set/del, `in`/`has_option`, `get`,
  `set`) applies `optionxform` exactly once and then uses private helpers
  (`_find_option`, `_get_option_idx`) that expect a transformed key. `Document`
  methods pass the caller's key on unchanged. As in ConfigParser, whose docs require
  it, `optionxform` must be idempotent: iteration yields transformed keys that are
  transformed again on lookup (e.g. `[s[k] for k in s]`).
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

The minimum is Python 3.11 (since 4.0), so 3.11 features such as `typing.Self` and
`X | Y` unions are fine. The minimum is set in several places that must stay in sync:
`python_requires` and the classifiers in `setup.cfg`, ruff's `target-version` in
`pyproject.toml`, `pyupgrade --py311-plus` in `.pre-commit-config.yaml` and the
`py{…}-diff` envs in `tox.ini`. The CI test matrix is derived from the classifiers. Otherwise pre-commit.ci autofixes can
introduce syntax newer than the minimum, which is how commit `99c0a76` broke imports
on Python < 3.11 before the minimum was raised.

## Conventions

- Formatting/linting: ruff + ruff-format (Black style, line length 88) with ruff's
  default rule set plus the ignores in `pyproject.toml`. `.isort.cfg` and the flake8
  settings in `setup.cfg` are legacy; no hook runs isort or flake8.
- Docstrings use Google style (`Args:`, `Returns:`, `Raises:`) with Sphinx roles;
  `docs/api.rst` autodocs the package.
- Tests are plain pytest functions in `tests/`. Inline configs use `dedent(...)`;
  `tests/test_setup.cfg` (via the `setup_cfg_path` / `setup_cfg` fixtures in
  `conftest.py`) is the round-trip fixture. Compare against stdlib `ConfigParser`
  where behavior should match. Every bugfix needs a regression test; name it after
  the GitHub issue when there is one (e.g. `test_update_file_issue_68`).
- User-visible changes get an entry in `CHANGELOG.rst` under the next version,
  referencing the issue (`issue #N`), or the PR (`PR #N`) if there is no issue.
- `README.md` is the PyPI long description; `docs/usage.rst` is a separate, longer
  usage guide.
- Untracked local artifacts (`docs/html/`, `site/`, `*.bak`, `build/`, `.tox/`) are
  not part of the project. Ignore them and don't commit them.
