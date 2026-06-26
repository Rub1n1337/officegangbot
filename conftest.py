"""Pytest bootstrap: put the repo root on sys.path so tests can import the
top-level `cogs` and `core` packages regardless of where pytest is invoked."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
