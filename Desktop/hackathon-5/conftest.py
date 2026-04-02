"""
Root conftest.py — configures pytest for the hackathon-5 project.

Sets asyncio_mode="auto" so all async test functions run without
needing @pytest.mark.asyncio on every test.
"""

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "asyncio: mark a test as async",
    )
