.. image:: https://travis-ci.org/pyscaffold/configupdater.svg?branch=master
    :target: https://travis-ci.org/pyscaffold/configupdater
.. image:: https://coveralls.io/repos/pyscaffold/configupdater/badge.png
    :target: https://coveralls.io/r/pyscaffold/configupdater

=============
ConfigUpdater
=============

WORK IN PROGRESS!

The sole purpose of ``ConfigUpdater`` is to easily update an INI config file
with no changes to the original file except the intended ones. This means
comments, the ordering of sections and key/value-pairs as wells as their
case are kept as in the original file. Thus ``ConfigUpdater`` provides
complementary functionality to Python's `ConfigParser`_ which is primarily
meant for reading config files and writing new ones.

Differences
===========

The key differences to ``ConfigParser`` are:

* inline comments are treated as part of a key's value,
* the original case of sections and keys are kept,
* control over the position of a new section/key

Following features are **deliberately not** implemented:

* interpolation of values,
* propagation of parameters from the default section,
* conversions of values,
* non-strict mode allowing duplicate sections and keys,


Note
====

``ConfigUpdater`` is mainly developed for http://pyscaffold.org/.

.. _ConfigParser: https://docs.python.org/3/library/configparser.html
