"""Run retained Python suites in separate processes and import scopes."""
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
for directory, arguments in [
    (root / "packages/source-adapters", ["-m", "unittest", "discover", "-s", "tests"]),
    (root / "countries/de/stepstone", ["-m", "pytest", "-q"]),
    (root / "countries/de/student-boards", ["-m", "unittest", "discover", "-s", "tests"]),
    (root / "countries/de/public-boards", ["-m", "unittest", "discover", "-s", "tests"]),
    (root / "shared/workday", ["-m", "unittest", "discover", "-s", "tests"]),
    (root / "shared/teamtailor", ["-m", "unittest", "discover", "-s", "tests"]),
    (root / "shared/dvinci", ["-m", "unittest", "discover", "-s", "tests"]),
    (root / "shared/onlyfy", ["-m", "unittest", "discover", "-s", "tests"]),
    (root / "shared/jobshop", ["-m", "unittest", "discover", "-s", "tests"]),
    (root / "shared/successfactors", ["-m", "unittest", "discover", "-s", "tests"]),
    (root / "shared/oracle", ["-m", "unittest", "discover", "-s", "tests"]),
    (root / "countries/de/discovery", ["-m", "unittest", "discover", "-s", "tests"]),
    (root / "shared/personio", ["-m", "unittest", "discover", "-s", "tests"]),
]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(root / "packages/source-adapters/src"), str(root / "countries/de/stepstone")])
    subprocess.run([sys.executable, *arguments], cwd=directory, env=env, check=True)
