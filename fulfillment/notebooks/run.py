# Databricks notebook source
import sys, json, platform, unittest
from pathlib import Path
import importlib.metadata

dbutils.widgets.text("dataset", "pilot")
dbutils.widgets.text("output_name", "pilot_v1")
path = (
    dbutils.notebook.entry_point.getDbutils()
    .notebook()
    .getContext()
    .notebookPath()
    .get()
)
root = Path("/Workspace" + path).parent.parent
sys.path.insert(0, str(root))
from evaluate import run
from report import build

suite = unittest.defaultTestLoader.discover(str(root / "tests"))
checks = unittest.TextTestRunner(verbosity=2).run(suite)
assert checks.wasSuccessful()
out = root / "outputs" / dbutils.widgets.get("output_name")
out.mkdir(parents=True, exist_ok=True)
(out / "runtime.json").write_text(
    json.dumps(
        {
            "python": platform.python_version(),
            "databricks_sdk": importlib.metadata.version("databricks-sdk"),
            "compute": "Databricks Free Edition serverless notebook",
            "tests_passed": checks.testsRun,
        },
        indent=2,
    )
)
rows = run(root / "data" / (dbutils.widgets.get("dataset") + ".json"), out)
summary = build(out)
assert len({(r["id"], r["arm"]) for r in rows}) == len(rows)
assert len(rows) == 2 * len(
    json.loads((root / "data" / (dbutils.widgets.get("dataset") + ".json")).read_text())
)
(out / "validation.json").write_text(
    json.dumps(
        {
            "tests_passed": checks.testsRun,
            "unique_observations": len(rows),
            "all_expected_observations_present": True,
        },
        indent=2,
    )
)
print(json.dumps(summary, indent=2))
dbutils.notebook.exit(json.dumps(summary))
