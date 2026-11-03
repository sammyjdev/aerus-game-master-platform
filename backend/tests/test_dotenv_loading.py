"""Verify dotenv isolation without reading a real local environment file."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("disabled", ["1", None, "0"])
def test_main_dotenv_loading(disabled):
    env = os.environ.copy()
    env.pop("PYTHON_DOTENV_DISABLED", None)
    if disabled is not None:
        env["PYTHON_DOTENV_DISABLED"] = disabled
    backend_dir = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-c", """
import json
import os
import secrets
from unittest.mock import patch
from cryptography.fernet import Fernet

os.environ["FERNET_KEY"] = Fernet.generate_key().decode()
os.environ["JWT_SECRET"] = secrets.token_hex(32)
os.environ["OPENROUTER_API_KEY"] = "test-key"
os.environ["DATABASE_PATH"] = ":memory:"
with patch("dotenv.load_dotenv") as load:
    import src.main
    print(json.dumps([
        {"path": str(call.args[0]), "override": call.kwargs["override"]}
        for call in load.call_args_list
    ]))
"""],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    calls = json.loads(result.stdout)
    expected = [] if disabled == "1" else [
        {"path": str(backend_dir / ".env"), "override": True}
    ]
    assert calls == expected
