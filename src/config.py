"""Project configuration: paths, constants, benchmark dimensions."""

from pathlib import Path

# Directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
REPORTS_DIR = DATA_DIR / "reports"

# Workflow identifiers
WORKFLOW_ECC = "ecc"
WORKFLOW_OLD = "old"
WORKFLOWS = (WORKFLOW_ECC, WORKFLOW_OLD)

# Machine identifiers
MACHINE_MAC_MINI = "mac_mini"
MACHINE_MACBOOK = "macbook"
MACHINES = (MACHINE_MAC_MINI, MACHINE_MACBOOK)

# Benchmark dimensions (from docs/benchmark.md)
DIMENSIONS = (
    "setup_time",
    "implementation_speed",
    "error_rate",
    "ease_of_modification",
    "autonomy_strength",
    "safety",
    "two_device_operability",
)
