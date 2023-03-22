=========
Changelog
=========

Version 3.2
===========

- Option ``prepend_newline`` in ``set_values`` to optionally avoid new lines, issue #104

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
