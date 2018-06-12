#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Dummy conftest.py for configupdater.

    If you don't know what this is for, just leave it empty.
    Read more about conftest.py under:
    https://pytest.org/latest/plugins.html
"""
from __future__ import print_function, absolute_import, division

import os
import inspect
from io import StringIO

import pytest


@pytest.fixture
def setup_cfg_path():
    filepath = inspect.getfile(inspect.currentframe())
    filedir = os.path.dirname(os.path.abspath(filepath))
    return os.path.join(filedir, 'setup.cfg')


@pytest.fixture
def setup_cfg(setup_cfg_path):
    with open(setup_cfg_path) as fh:
        return fh.read()


def parser_to_str(parser):
    fh = StringIO()
    parser.write(fh)
    fh.seek(0)
    return fh.read()
