"""Run the staged Space folder (deploy/_space) locally on port 8502, importing its own copy of the package,
to prove the Space contains every file the app needs before publishing."""
import os
import subprocess
import sys
from pathlib import Path

stage = Path(__file__).resolve().parent / "_space"
env = {**os.environ, "PYTHONPATH": str(stage / "src")}
sys.exit(subprocess.call([sys.executable, "-m", "streamlit", "run", "app/app.py", "--server.port", "8502",
                          "--server.headless", "true", "--browser.gatherUsageStats", "false"], cwd=stage, env=env))
