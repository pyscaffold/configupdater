.. image:: gfx/banner-640x323.png
   :height: 323px
   :width: 640px
   :scale: 60 %
   :alt: ConfigUpdater
   :align: center

|

The sole purpose of `ConfigUpdater`_ is to easily update an INI config file
with no changes to the original file except the intended ones. This means
comments, the ordering of sections and key/value-pairs as wells as their
cases are kept as in the original file. Thus ConfigUpdater provides
complementary functionality to Python's `ConfigParser`_ which is primarily
meant for reading config files and writing *new* ones.
Read more on how to use `ConfigUpdater`_ in the :ref:`usage page <usage>`.

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

.. note::

   ConfigUpdater is mainly developed for `PyScaffold`_.

.. _ConfigParser: https://docs.python.org/3/library/configparser.html
.. _ConfigUpdater: https://configupdater.readthedocs.io/
.. _PyScaffold: https://pyscaffold.org/
.. _module reference: https://configupdater.readthedocs.io/en/latest/api/configupdater.html#configupdater.configupdater.ConfigUpdater
.. _unit tests: https://github.com/pyscaffold/configupdater/blob/main/tests/test_configupdater.py



Contents
========

.. toctree::
   :maxdepth: 2

   Usage & Examples <usage>
   Contributions & Help <contributing>
   License <license>
   Authors <authors>
   Changelog <changelog>
   Module Reference <api/modules>


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
