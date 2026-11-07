import runpy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class StreamlitEntryPointTests(unittest.TestCase):
    def test_compatibility_entrypoint_calls_run_app_on_each_execution(self):
        run_app = Mock()
        app_module = types.ModuleType("app")
        app_module.run_app = run_app
        entrypoint = Path(__file__).resolve().parents[1] / "streamlit_app.py"

        with patch.dict(sys.modules, {"app":app_module}):
            runpy.run_path(str(entrypoint))
            runpy.run_path(str(entrypoint))

        self.assertEqual(run_app.call_count, 2)


if __name__ == "__main__":
    unittest.main()
