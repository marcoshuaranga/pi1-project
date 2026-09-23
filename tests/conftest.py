"""Test-session hermeticity: never let a bare Settings()/KedbStore() touch
the real /data/... paths.

Settings defaults to absolute /data/... paths, which are correct inside the
Docker containers (writable volumes) but not outside one. On a real Linux
CI runner, the default non-root user gets PermissionError creating /data at
all; on this repo's local dev machine it happens to resolve into a writable
location, which is exactly why this went unnoticed until CI actually ran
the suite for real (previously workflow_dispatch-only). Force these to a
session tmp dir before any test imports pi_core.config, so the class defaults
are never actually reached — this only affects the process-wide
get_settings()/get_kedb_store() singletons; tests that build their own
Settings(kedb_db_path=...) with a tmp_path fixture are unaffected, since
explicit kwargs always take priority over env vars.
"""

import os
import tempfile

_TMP_ROOT = tempfile.mkdtemp(prefix="pi1-test-data-")
os.environ["KEDB_DB_PATH"] = os.path.join(_TMP_ROOT, "kedb", "kedb.db")
os.environ["KEDB_DOCS_PATH"] = os.path.join(_TMP_ROOT, "kedb", "articles")
os.environ["DATA_PROCESSED_PATH"] = os.path.join(_TMP_ROOT, "processed")
