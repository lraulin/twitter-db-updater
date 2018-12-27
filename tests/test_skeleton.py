#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from twitter_db_updater.skeleton import fib

__author__ = "Lee Raulin"
__copyright__ = "Lee Raulin"
__license__ = "mit"


def test_fib():
    assert fib(1) == 1
    assert fib(2) == 1
    assert fib(7) == 13
    with pytest.raises(AssertionError):
        fib(-10)
