.. image:: https://api.cirrus-ci.com/github/pyscaffold/configupdater.svg?branch=main
    :alt: Built Status
    :target: https://cirrus-ci.com/github/pyscaffold/configupdater
.. image:: https://readthedocs.org/projects/pyscaffold/badge/?version=latest
    :alt: ReadTheDocs
    :target: https://configupdater.readthedocs.io/
.. image:: https://img.shields.io/coveralls/github/pyscaffold/configupdater/main.svg
    :alt: Coveralls
    :target: https://coveralls.io/r/pyscaffold/configupdater
.. image:: https://img.shields.io/pypi/v/configupdater.svg
    :alt: PyPI-Server
    :target: https://pypi.org/project/configupdater/
.. image:: https://img.shields.io/conda/vn/conda-forge/configupdater.svg
    :alt: Conda-Forge
    :target: https://anaconda.org/conda-forge/configupdater
.. image:: https://pepy.tech/badge/configupdater/month
    :alt: Monthly Downloads
    :target: https://pepy.tech/project/configupdater
.. image:: https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=ff69b4
    :alt: Sponsor me
    :target: https://github.com/sponsors/FlorianWilhelm

|

.. image:: https://configupdater.readthedocs.io/en/latest/_images/banner-640x323.png
    :height: 323px
    :width: 640px
    :scale: 60 %
    :alt: Config Updater
    :align: center

|

The sole purpose of `ConfigUpdater`_ is to easily update an INI config file
with no changes to the original file except the intended ones. This means
comments, the ordering of sections and key/value-pairs as wells as their
cases are kept as in the original file. Thus ConfigUpdater provides
complementary functionality to Python's `ConfigParser`_ which is primarily
meant for reading config files and writing *new* ones.

Features
========

The key differences to `ConfigParser`_ are:

* minimal invasive changes in the update configuration file,
* proper handling of comments,
* only a single config file can be updated at a time,
* the original case of sections and keys are kept,
* control over the position of a new section/key

Following features are **deliberately not** implemented:

* interpolation of values,
* propagation of parameters from the default section,
* conversions of values,
* passing key/value-pairs with ``default`` argument,
* non-strict mode allowing duplicate sections and keys.

Usage
=====

First install the package with either::

    pip install configupdater

or::

    conda install -c conda-forge configupdater

Now we can simply do::

    from configupdater import ConfigUpdater

    updater = ConfigUpdater()
    updater.read("setup.cfg")

which would read the file ``setup.cfg`` that is found in many projects.

To change the value of an existing key we can simply do::

    updater["metadata"]["author"].value = "Alan Turing"

At any point we can print the current state of the configuration file with::

    print(updater)

To update the read-in file just call ``updater.update_file()`` or ``updater.write(open('filename','w'))``
to write the changed configuration file to another destination. Before actually writing,
ConfigUpdater will automatically check that the updated configuration file is still valid by
parsing it with the help of ConfigParser.

Many of ConfigParser's methods still exists and it's best to look them up in the `module reference`_.
Let's look at some examples.

Adding and removing options
---------------------------

Let's say we have the following configuration in a string::

    cfg = """
    [metadata]
    author = Ada Lovelace
    summary = The Analytical Engine
    """

We can add an *license* option, i.e. a key/value pair, in the same way we would do with ConfigParser::

    updater = ConfigUpdater()
    updater.read_string(cfg)
    updater["metadata"]["license"] = "MIT"

A simple ``print(updater)`` will give show you that the new option was appended to the end::

    [metadata]
    author = Ada Lovelace
    summary = The Analytical Engine
    license = MIT

Since the license is really important to us let's say we want to add it before the ``summary``
and even add a short comment before it::

    updater = ConfigUpdater()
    updater.read_string(cfg)
    (updater["metadata"]["summary"].add_before
                                   .comment("Ada would have loved MIT")
                                   .option("license", "MIT"))

which would result in::

    [metadata]
    author = Ada Lovelace
    # Ada would have loved MIT
    license = MIT
    summary = Analytical Engine calculating the Bernoulli numbers

Using ``add_after`` would give the same result and looks like::

    updater = ConfigUpdater()
    updater.read_string(cfg)
    (updater["metadata"]["author"].add_after
                                  .comment("Ada would have loved MIT")
                                  .option("license", "MIT"))

Let's say we want to rename `summary` to the more common `description`::

    updater = ConfigUpdater()
    updater.read_string(cfg)
    updater["metadata"]["summary"].key = "description"

If we wanted no summary at all, we could just do ``del updater["metadata"]["summary"]``.


Adding and removing sections
----------------------------

Adding and remove sections just works like adding and removing options but on a higher level.
Sticking to our *Ada Lovelace* example, let's say we want to add a section ``options`` just
before ``metadata`` with a comment and two new lines to separate it from ``metadata``::

    updater = ConfigUpdater()
    updater.read_string(cfg)
    (updater["metadata"].add_before
                        .comment("Some specific project options")
                        .section("options")
                        .space(2))

As expected, this results in::

    # Some specific project options
    [options]

    [metadata]
    author = Ada Lovelace
    summary = The Analytical Engine

We could now fill the new section with options like we learnt before. If we wanted to rename
an existing section we could do this with the help of the ``name`` attribute::

    updater["metadata"].name = "MetaData"

Sometimes it might be useful to inject a new section not in a programmatic way but more declarative.
Let's assume we have thus defined our new section in a multi-line string::

    sphinx_sect_str = """
    [build_sphinx]
    source_dir = docs
    build_dir = docs/_build
    """

With the help of two ConfigUpdater objects we can easily inject this section into our example::

    sphinx = ConfigUpdater()
    sphinx.read_string(sphinx_sect_str)
    sphinx_sect = sphinx["build_sphinx"]

    updater = ConfigUpdater()
    updater.read_string(cfg)

    (updater["metadata"].add_after
                        .space()
                        .section(sphinx_sect.detach()))

The ``detach`` method will remove the ``build_sphinx`` section from the first object
and add it to the second object. This results in::

    [metadata]
    author = Ada Lovelace
    summary = The Analytical Engine

    [build_sphinx]
    source_dir = docs
    build_dir = docs/_build

Alternatively, if you want to preserve ``build_sphinx`` in both
``ConfigUpdater`` objects (i.e., prevent it from being removed from the first
while still adding a copy to the second), you call also rely on stdlib's
``copy.deepcopy`` function instead of ``detach``::

    from copy import deepcopy

    (updater["metadata"].add_after
                        .space()
                        .section(deepcopy(sphinx_sect)))

This technique can be used for all objects inside ConfigUpdater: sections,
options, comments and blank spaces.

Shallow copies are discouraged in the context of ConfigUpdater because each
configuration block keeps a reference to its container to allow easy document
editing. When doing editions (such as adding or changing options and comments)
based on a shallow copy, the results can be unreliable and unexpected.

For more examples on how the API of ConfigUpdater works it's best to take a look into the
`unit tests`_ and read the references.


Notes
=====

ConfigUpdater is mainly developed for `PyScaffold`_.

.. _ConfigParser: https://docs.python.org/3/library/configparser.html
.. _ConfigUpdater: https://configupdater.readthedocs.io/
.. _PyScaffold: https://pyscaffold.org/
.. _module reference: https://configupdater.readthedocs.io/en/latest/api/configupdater.html#configupdater.configupdater.ConfigUpdater
.. _unit tests: https://github.com/pyscaffold/configupdater/blob/main/tests/test_configupdater.py
