"""
Data models and constants for registry operations.
"""

from typing import Literal

# Registry value types accepted by Set-ItemProperty -Type.
ALLOWED_REGISTRY_TYPES = frozenset(
    {
        "String",
        "ExpandString",
        "Binary",
        "DWord",
        "MultiString",
        "QWord",
    }
)

RegistryType = Literal[
    "String",
    "ExpandString",
    "Binary",
    "DWord",
    "MultiString",
    "QWord",
]
