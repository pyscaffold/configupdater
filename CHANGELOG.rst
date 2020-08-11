=========
Changelog
=========

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
