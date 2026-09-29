"""Check a glTF file against the Honu glTF Asset Profile."""

from .rules import Finding, check_file

__all__ = ["Finding", "check_file"]
