#!/usr/bin/env python
"""
Dummy conftest.py for configupdater.

If you don't know what this is for, just leave it empty.
Read more about conftest.py under:
https://pytest.org/latest/plugins.html
"""

import inspect
import os

import pytest


@pytest.fixture
def setup_cfg_path():
    filepath = inspect.getfile(inspect.currentframe())
    filedir = os.path.dirname(os.path.abspath(filepath))
    return os.path.join(filedir, "test_setup.cfg")


@pytest.fixture
def setup_cfg(setup_cfg_path):
    with open(setup_cfg_path) as fh:
        return fh.read()
