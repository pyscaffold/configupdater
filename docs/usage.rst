.. _usage:

=====
Usage
=====

.. The code examples below are run by ``tox -e doctests``. The hidden blocks set up
   a ``setup.cfg`` to read and print the results that the text shows.

.. testsetup::

    import os
    import tempfile

    _cwd = os.getcwd()
    _tmpdir = tempfile.TemporaryDirectory()
    os.chdir(_tmpdir.name)
    with open("setup.cfg", "w") as fp:
        fp.write("[metadata]\nname = my_project\nauthor = Ada Lovelace\n")

.. testcleanup::

    os.chdir(_cwd)
    _tmpdir.cleanup()

First install the package with:

.. code-block:: console

    pip install configupdater

or add it to a project managed with `uv <https://docs.astral.sh/uv/>`_:

.. code-block:: console

    uv add configupdater

Now we can simply do:

.. testcode::

    from configupdater import ConfigUpdater

    updater = ConfigUpdater()
    updater.read("setup.cfg")

which would read the file ``setup.cfg`` that is found in many projects.

To change the value of an existing key we can simply do:

.. testcode::

    updater["metadata"]["author"].value = "Alan Turing"

At any point we can print the current state of the configuration file with:

.. testcode::

    print(updater)

.. testoutput::
    :hide:
    :options: +NORMALIZE_WHITESPACE

    [metadata]
    name = my_project
    author = Alan Turing

To update the read-in file, with the encoding it was read with, just call
``updater.update_file()`` or ``updater.write(fp)`` with a file object ``fp`` to write the
changed configuration file to another destination.
Before actually writing, ConfigUpdater will automatically check that the updated
configuration file is still valid by parsing it with the help of ConfigParser.

Many of ConfigParser's methods still exists and it's best to look them up in the :doc:`API reference <api>`.
Let's look at some examples.

Adding and removing options
---------------------------

Let's say we have the following configuration in a string:

.. testcode::

    cfg = """
    [metadata]
    author = Ada Lovelace
    summary = The Analytical Engine
    """

We can add an *license* option, i.e. a key/value pair, in the same way we would do with ConfigParser:

.. testcode::

    updater = ConfigUpdater()
    updater.read_string(cfg)
    updater["metadata"]["license"] = "MIT"

A simple ``print(updater)`` will give show you that the new option was appended to the end:

.. testcode::
    :hide:

    print(str(updater).strip())

.. testoutput::

    [metadata]
    author = Ada Lovelace
    summary = The Analytical Engine
    license = MIT

Since the license is really important to us let's say we want to add it before the ``summary``
and even add a short comment before it:

.. testcode::

    updater = ConfigUpdater()
    updater.read_string(cfg)
    (
        updater["metadata"]["summary"]
        .add_before.comment("Ada would have loved MIT")
        .option("license", "MIT")
    )

which would result in:

.. testcode::
    :hide:

    print(str(updater).strip())

.. testoutput::

    [metadata]
    author = Ada Lovelace
    # Ada would have loved MIT
    license = MIT
    summary = The Analytical Engine

Using ``add_after`` would give the same result and looks like:

.. testcode::

    updater = ConfigUpdater()
    updater.read_string(cfg)
    (
        updater["metadata"]["author"]
        .add_after.comment("Ada would have loved MIT")
        .option("license", "MIT")
    )

.. testcode::
    :hide:

    print(str(updater).strip())

.. testoutput::
    :hide:

    [metadata]
    author = Ada Lovelace
    # Ada would have loved MIT
    license = MIT
    summary = The Analytical Engine

Let's say we want to rename ``summary`` to the more common ``description``:

.. testcode::

    updater = ConfigUpdater()
    updater.read_string(cfg)
    updater["metadata"]["summary"].key = "description"

.. testcode::
    :hide:

    print(str(updater).strip())

.. testoutput::
    :hide:

    [metadata]
    author = Ada Lovelace
    description = The Analytical Engine

If we wanted no summary at all, we could just do ``del updater["metadata"]["summary"]``.


Option keys and case sensitivity
--------------------------------

Like ConfigParser, ConfigUpdater passes option keys through
:meth:`~configupdater.ConfigUpdater.optionxform` before comparing them.
The default is :meth:`str.lower`, so ``updater["metadata"]["AUTHOR"]`` finds the
``author`` option, while the file keeps the original spelling, which is also
available as :attr:`~configupdater.Option.raw_key`.
To make keys case-sensitive, set ``optionxform`` before reading the file:

.. testcode::

    updater = ConfigUpdater()
    updater.optionxform = str
    updater.read_string(cfg)

.. testcode::
    :hide:

    assert "author" in updater["metadata"]
    assert "AUTHOR" not in updater["metadata"]

.. warning::
   As in ConfigParser, a custom ``optionxform`` must be idempotent, i.e.
   ``optionxform(optionxform(key)) == optionxform(key)``, because the keys that
   ConfigUpdater returns, e.g. when iterating over a section, are already
   transformed and are transformed again when you use them for a lookup.
   For example, with ``lambda key: "prefix_" + key``,
   ``[section[key] for key in section]`` raises a :class:`KeyError`: iterating over
   a section with a ``license`` option yields ``prefix_license``, which is then
   looked up as ``prefix_prefix_license``.


Adding and removing sections
----------------------------

Adding and remove sections just works like adding and removing options but on a higher level.
Sticking to our *Ada Lovelace* example, let's say we want to add a section ``options`` just
before ``metadata`` with a comment and two new lines to separate it from ``metadata``:

.. testcode::

    updater = ConfigUpdater()
    updater.read_string(cfg)
    (
        updater["metadata"]
        .add_before.comment("Some specific project options")
        .section("options")
        .space(2)
    )

As expected, this results in:

.. testcode::
    :hide:

    print(str(updater).strip())

.. testoutput::

    # Some specific project options
    [options]


    [metadata]
    author = Ada Lovelace
    summary = The Analytical Engine

We could now fill the new section with options like we learnt before. If we wanted to rename
an existing section we could do this with the help of the ``name`` attribute:

.. testcode::

    updater["metadata"].name = "MetaData"

.. testcode::
    :hide:

    assert updater.sections() == ["options", "MetaData"]

Sometimes it might be useful to inject a new section not in a programmatic way but more declarative.
Let's assume we have thus defined our new section in a multi-line string:

.. testcode::

    sphinx_sect_str = """
    [build_sphinx]
    source_dir = docs
    build_dir = docs/_build
    """

With the help of two ConfigUpdater objects we can easily inject this section into our example:

.. testcode::

    sphinx = ConfigUpdater()
    sphinx.read_string(sphinx_sect_str)
    sphinx_sect = sphinx["build_sphinx"]

    updater = ConfigUpdater()
    updater.read_string(cfg)

    (updater["metadata"].add_after.space().section(sphinx_sect.detach()))

The :meth:`~configupdater.block.Block.detach` method will remove the ``build_sphinx``
section from the first object and add it to the second object. This results in:

.. testcode::
    :hide:

    assert not sphinx.has_section("build_sphinx")
    print(str(updater).strip())

.. testoutput::

    [metadata]
    author = Ada Lovelace
    summary = The Analytical Engine

    [build_sphinx]
    source_dir = docs
    build_dir = docs/_build

Alternatively, if you want to preserve ``build_sphinx`` in both
:class:`~configupdater.ConfigUpdater` objects (i.e., prevent it from being
removed from the first while still adding a copy to the second), you call also
rely on stdlib's :func:`copy.deepcopy` function instead of
:meth:`~configupdater.block.Block.detach`:

.. testcode::

    from copy import deepcopy

    sphinx = ConfigUpdater()
    sphinx.read_string(sphinx_sect_str)
    sphinx_sect = sphinx["build_sphinx"]

    updater = ConfigUpdater()
    updater.read_string(cfg)

    (updater["metadata"].add_after.space().section(deepcopy(sphinx_sect)))

.. testcode::
    :hide:

    assert sphinx.has_section("build_sphinx")
    assert updater.has_section("build_sphinx")

This technique can be used for all objects inside ConfigUpdater: sections,
options, comments and blank spaces.

Shallow copies are discouraged in the context of ConfigUpdater because each
configuration block keeps a reference to its container to allow easy document
editing. When doing editions (such as adding or changing options and comments)
based on a shallow copy, the results can be unreliable and unexpected.

Keeping comments immediately before a section
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``add_before`` inserts directly before the section block. If you have added
comments immediately before that section using the builder, they remain before
the newly inserted block. To keep those comments next to the original section,
use :attr:`~configupdater.Section.add_before_skip_comments` instead:

.. testcode::

    updater = ConfigUpdater()
    updater.read_string("[first]\n")
    (
        updater["first"]
        .add_after.comment("Settings for the target section")
        .section("target")
    )
    (updater["target"].add_before_skip_comments.section("middle").space())

This results in:

.. testcode::
    :hide:

    print(str(updater).strip())

.. testoutput::

    [first]
    [middle]

    # Settings for the target section
    [target]

Only consecutive comment blocks at the document level are skipped. Blank
spaces stop the search, and comments inside a previous section are not moved.
This does not change how the parser associates comments with sections.

For more examples on how the API of ConfigUpdater works it's best to take a look into the
`unit tests`_ and read the references.


.. _`unit tests`: https://github.com/pyscaffold/configupdater/blob/main/tests/test_configupdater.py
