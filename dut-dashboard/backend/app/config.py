import os
from pathlib import Path

ROOT_DIR = Path(os.getenv("DUT_BROWSER_ROOT", Path(__file__).resolve().parents[3]))
DATA_DIR = Path(os.getenv("DUT_BROWSER_DATA_DIR", ROOT_DIR / "dut-dashboard"))
LOG_DIR = DATA_DIR / "logs"
SNAPSHOT_FILE = LOG_DIR / "snapshots.jsonl"
TOOLS_DIR = ROOT_DIR / "dut-dashboard" / "tools"
ANALYZER_SCRIPT = TOOLS_DIR / "analyzer3.py"
ANALYZER_OUTPUT_DIR = LOG_DIR / "analyzer_output"
