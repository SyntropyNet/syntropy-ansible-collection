from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.syntropynet.syntropy.plugins.modules import (
    syntropy_api_key as module,
)


def test_imports():
    assert module.HAS_SDK
