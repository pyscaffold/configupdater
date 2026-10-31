=========
Changelog
=========

Version 4.0.2 (unreleased)
==========================

- Make ``Option.as_list()`` use the current value after assignments to or from
  ``None``, so ``append()`` no longer discards values added to a valueless option
  and converting an option to ``None`` no longer raises an ``AttributeError``, PR #179
- Detach every child block when clearing a document or section, so removed
  sections and options can be attached elsewhere without stale parent links
  (follow-up to PR #43), PR #180

Version 4.0.1
=============

- Insert a newline before a newly added option when the file does not end
  with one, so appending an option to the last section no longer glues the
  option onto the last line and silently corrupts the previous value
  (related to the new-section fix in PR #142 for issue #126), PR #178
- Fix spelling, grammar and factual errors in the documentation and docstrings,
  e.g. the inverted description of ``empty_lines_in_values`` and the name of the
  unsupported ``defaults`` argument of ConfigParser, PR #175

Version 4.0
===========

- **Breaking:** Drop support for Python < 3.11; the minimum supported version is now
  Python 3.11, PR #150
- Add support for Python 3.15, PR #160
- Simplify type hints using Python 3.11 features (``typing.Self``, ``X | Y`` unions)
  and remove compatibility code for older Python versions, PR #150
- Add ``add_before_skip_comments`` to ``Section`` for inserting blocks before the
  comments that directly precede a section, issue #117
- Fix ``add_section`` gluing the new section header to the last line when the file
  does not end with a newline, issue #126
- Fix ``None`` being written as delimiter when assigning a value to an option that was
  parsed without a value (``allow_no_value``), issue #141
- Port the option regexes of Python 3.15's ``configparser`` (CPython gh-146333). The
  old ones backtracked quadratically, so a long line with many spaces could stall
  the parser for minutes, PR #161
- Fix navigating, detaching or inserting at the wrong position when a container holds
  several equal comment or blank-line blocks, issue #140
- ``del section[key]`` (and thus ``section.pop(key)``) now applies ``optionxform``
  like ``section[key]`` does, PR #148
- Document that a custom ``optionxform`` must be idempotent, PR #152
- Build with hatchling and hatch-vcs, with all metadata in ``pyproject.toml``. The
  wheel is now tagged ``py3-none-any`` (instead of ``py2.py3-none-any``), and the
  license is declared as a PEP 639 expression. The ``testing`` extra is removed;
  development dependencies are dependency groups, installed e.g. with ``uv sync``, PR #156
- Complete the type annotations of the public API, now checked with mypy in strict
  mode, and fix the ``NoneValueDisallowed`` warning under ``python -OO``, PR #158
- Fix ``NotAttachedError``, ``AlreadyAttachedError`` and ``AssignMultilineValueError``
  failing with an ``AttributeError`` under ``python -OO``, PR #163
- Correct the ``NoneValueDisallowed`` message. It claimed that an option without a
  value is written with an empty value, but the option has been omitted since version 3.0.1,
  PR #163
- ``add_before.option`` and ``add_after.option`` pass ``delimiter`` and
  ``space_around_delimiters`` on to the new option instead of silently ignoring all
  keyword arguments. Other keyword arguments now raise a ``TypeError``, PR #163
- **Breaking:** An explicit ``space_around_delimiters`` of an ``Option`` (also given
  to ``add_before.option``, ``add_after.option`` or ``Section.create_option``) now
  takes precedence over the syntax options of the ``ConfigUpdater``, so ``False``
  writes ``key=value`` even with the default ``space_around_delimiters=True``.
  ``Option`` defaults to ``space_around_delimiters=None``, i.e. it follows the
  ``ConfigUpdater`` it belongs to: ``Option("key", "value")`` now writes
  ``key=value`` into a ``ConfigUpdater(space_around_delimiters=False)`` instead of
  ``key = value``. Options created with ``section[key] = value`` or ``set`` keep
  following the ``ConfigUpdater`` they are copied to, PR #166
- **Breaking:** ``key in section``, ``section.has_option(key)`` and
  ``section.get(key)`` now apply ``optionxform`` to ``key``, like ``section[key]``
  and ConfigParser do. With the default ``str.lower``, ``"KEY" in section`` is now
  ``True`` and ``section.get("KEY")`` returns the option instead of ``None``, PR #153
- **Breaking:** ``Section.set`` and ``ConfigUpdater.set`` keep the given spelling
  when they create a new option, like ``section[key] = value`` does. For example,
  ``updater.set("metadata", "Name", "x")`` now writes ``Name = x`` instead of
  ``name = x``, PR #153
- ``ConfigUpdater.set``, ``get``, ``has_option`` and ``remove_option`` apply
  ``optionxform`` only once instead of transforming already transformed keys again,
  PR #153
- Fix wrong code examples in the usage guide and the README, which are now tested,
  PR #164
- Fix ``update_file`` writing the file with the platform's default encoding instead
  of the encoding it was read with. ``read`` and ``read_file`` remember the encoding
  (``read_file`` takes it from ``f.encoding``), PR #165
- ``ConfigUpdater.read`` and ``Parser.read`` call ``io.text_encoding`` like
  ConfigParser, so with ``-X warn_default_encoding`` the ``EncodingWarning`` points
  to the caller (PEP 597), PR #165

Version 3.2
===========

- Option ``prepend_newline`` in ``set_values`` to optionally avoid new lines, issue #104
- Fix square brackets in section names not being parsed, issue #122

Version 3.1.1
=============

- Preserve indentation of section when there are comments, issue #92

Version 3.1
===========

- Prevent modifying multi-line values directly with ``value``, issue #87
- Added ``append`` method to ``Option`` for editing multi-line values
- Added ``as_list`` method to ``Option`` to handle multi-line values more easily

Version 3.0.1
=============

- Fix error when parsing unindented comments in multi-line values, issue #73
- Fix invalid string produced when ``allow_no_value = False``, issue #68

Version 3.0
===========

- Added type hinting, issue #16
- Fix parsing error of indented comment lines, issue #25
- Allow handling of raw section comment, issue #25
- More unit testing of optionxform, issue #55
- Allow sections/options to be copied from one document to the other, issue #47
- New logo, issue #29
- Whole API was rechecked by @abravalheri and changed for consistency, issue #19


Version 2.0
===========

- Changes in parser, i.e. comments in multi-line option values are kept
- Issue #14 is fixed
- Parameter ``empty_lines_in_values`` is now activated by default and can be changed
- Renamed ``sections_blocks`` to ``section_blocks`` for consistency
- Renamed ``last_item`` to ``last_block`` for consistency
- Added ``first_block``
- Reworked some internal parts of the inheritance hierarchy
- Added ``remove`` to remove the current block
- Added ``next_block`` and ``previous_block`` for easier navigation in section

Version 1.1.3
=============

- Added ``fallback`` argument to ``ConfigUpdater.get``, mirroring ConfigParser

Version 1.1.2
=============

- Fix wrongly modifying input in ``Option.set_value``, issue #11

Version 1.1.1
=============

- Fix iterating over the ``items()`` view of a section, issue #8

Version 1.1
===========

- Validate format on write by default (can be deactivated)
- Fixed issue #7 with mixed-case options
- Fixed issue #7 with add_before/add_after problem
- Fixed issue #7 with wrong duplicate mixed-case entries
- Fixed issue #7 with duplicate options after add_after/before

Version 1.0.1
=============

- More sane error message if ``read_file`` is misused
- Also run unit tests on Windows

Version 1.0
===========

- Fix: Use ``\n`` instead of ``os.linesep`` where appropriate

Version 0.3.2
=============

- Added GitHub and documentation links to the project's metadata

Version 0.3.1
=============

- Require Python >= 3.4 with ``python_requires``

Version 0.3
===========

- Added an ``insert_at`` method at section level
- Some internal code simplifications

Version 0.2
===========

- Added a ``to_dict()`` function

Version 0.1.1
=============

- Allow for flexible comment character in ``comment(...)``

Version 0.1
===========

- First release
