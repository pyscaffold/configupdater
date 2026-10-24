.. image:: gfx/banner-640x323.png
   :height: 323px
   :width: 640px
   :scale: 60 %
   :alt: ConfigUpdater
   :align: center

|

The sole purpose of `ConfigUpdater`_ is to easily update an INI config file
with no changes to the original file except the intended ones. This means
comments, the ordering of sections and key/value pairs as well as their
case are kept as in the original file. Thus ConfigUpdater provides
complementary functionality to Python's `ConfigParser`_, which is primarily
meant for reading config files and writing *new* ones.
Read more on how to use `ConfigUpdater`_ in the :ref:`usage page <usage>`.

Features
========

The key differences to `ConfigParser`_ are:

* minimally invasive changes in the updated configuration file,
* proper handling of comments,
* only a single config file can be updated at a time,
* the original case of sections and keys is kept,
* control over the position of a new section/key.

The following features are **deliberately not** implemented:

* interpolation of values,
* propagation of parameters from the default section,
* conversion of values,
* passing key/value pairs with the ``defaults`` argument,
* non-strict mode allowing duplicate sections and keys.

.. note::

   ConfigUpdater started out as a helper for `PyScaffold`_, which still uses
   it to update the ``setup.cfg`` of existing projects. Since then it has
   become a useful tool in its own right for everyone who needs to change
   configuration files programmatically without losing the comments and
   formatting that humans put into them.

.. _ConfigParser: https://docs.python.org/3/library/configparser.html
.. _ConfigUpdater: https://configupdater.readthedocs.io/
.. _PyScaffold: https://pyscaffold.org/



Contents
========

.. toctree::
   :maxdepth: 2

   Usage & Examples <usage>
   Contributions & Help <contributing>
   License <license>
   Authors <authors>
   Changelog <changelog>
   API Reference <api>


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
