from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]

if "custom_components" not in sys.modules:
    custom_components = ModuleType("custom_components")
    custom_components.__path__ = [str(ROOT / "custom_components")]
    sys.modules["custom_components"] = custom_components

if "custom_components.appliance_patterns" not in sys.modules:
    appliance_pkg = ModuleType("custom_components.appliance_patterns")
    appliance_pkg.__path__ = [str(ROOT / "custom_components" / "appliance_patterns")]
    sys.modules["custom_components.appliance_patterns"] = appliance_pkg
