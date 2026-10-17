=========
Changelog
=========

Version 4.0 (unreleased)
========================

- Drop support for Python < 3.11, the minimum supported version is now Python 3.11
- Simplify type hints using Python 3.11 features (``typing.Self``, ``X | Y`` unions)
  and remove compatibility code for older Python versions
- Added ``add_before_skip_comments`` to ``Section`` for inserting blocks before the
  comments that directly precede a section, issue #117
- Fix ``add_section`` gluing the new section header to the last line when the file
  does not end with a newline, issue #126
- Fix ``None`` being written as delimiter when assigning a value to an option that was
  parsed without a value (``allow_no_value``), issue #141
- Fix navigating, detaching or inserting at the wrong position when a container holds
  several equal comment or blank-line blocks, issue #140
- ``del section[key]`` (and thus ``section.pop(key)``) now applies ``optionxform``
  like ``section[key]`` does, PR #148
- Document that a custom ``optionxform`` must be idempotent
- **Breaking:** ``key in section``, ``section.has_option(key)`` and
  ``section.get(key)`` now apply ``optionxform`` to ``key``, like ``section[key]``
  and ConfigParser do. With the default ``str.lower``, ``"KEY" in section`` is now
  ``True`` and ``section.get("KEY")`` returns the option instead of ``None``
- **Breaking:** ``Section.set`` and ``ConfigUpdater.set`` keep the given spelling
  when they create a new option, like ``section[key] = value`` does. For example,
  ``updater.set("metadata", "Name", "x")`` now writes ``Name = x`` instead of
  ``name = x``
- ``ConfigUpdater.set``, ``get``, ``has_option`` and ``remove_option`` apply
  ``optionxform`` only once instead of transforming already transformed keys again

Version 3.2
===========

- Option ``prepend_newline`` in ``set_values`` to optionally avoid new lines, issue #104
- Fix square brackets not parsed in section names, issue #122

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
- Allowing sections/options to be copied from one document to the other, issue #47
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

- Added fallback option to ConfigUpdater.get reflecting ConfigParser

Version 1.1.2
=============

- Fix wrongly modifying input in Option.set_value #11

Version 1.1.1
=============

- Fix iterating over the items() view of a section breaks #8

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
- Also run unittests with Windows

Version 1.0
===========

- Fix: Use \n instead of os.linesep where appropriate

Version 0.3.2
=============

- Added Github and documentation link into the project's metadata

Version 0.3.1
=============

- Require Python >= 3.4 with ``python_requires``

Version 0.3
===========

- Added a ``insert_at`` function at section level
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
