import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_test_build_renames_plugin(tmp_path):
    out = tmp_path / "t.zip"
    subprocess.check_call([sys.executable, "scripts/build_plugin.py",
                           "--test", "-o", str(out)], cwd=ROOT)
    with zipfile.ZipFile(out) as zf:
        pj = json.loads(zf.read(".claude-plugin/plugin.json"))
    assert pj["name"] == "tender-ai-test"
