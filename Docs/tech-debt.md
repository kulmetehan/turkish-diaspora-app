# Technical Debt Documentation

This document tracks technical debt issues, their fixes, and future refactoring opportunities.

## Fixed Issues

### Python 3.13 Importlib/Dataclass Compatibility Issue

**Issue**: `AttributeError: 'NoneType' object has no attribute '__dict__'` when loading modules with dataclasses via `importlib.util.spec_from_file_location` in Python 3.13.

**Location**: `Backend/tests/test_migrate_google_to_osm.py`

**Root Cause**: Python 3.13 introduced stricter module namespace initialization checks. When dataclass decorators execute during module loading via `spec_from_file_location`, the module namespace may not be fully initialized unless the module is registered in `sys.modules` before `exec_module()` is called.

**Fix Applied**: Insert the module into `sys.modules` before calling `exec_module()`:

```python
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
# Insert module into sys.modules before exec_module to ensure proper namespace
# initialization for Python 3.13 dataclass compatibility
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
```

**Reference**: See `Backend/tests/test_migrate_google_to_osm.py` lines 5-11.

**Status**: Fixed (October 2025)

---

### Missing sys.path Setup in news_ingest_bot.py

**Issue**: `ModuleNotFoundError: No module named 'services'` when pytest imports `news_ingest_bot` because `Backend/` is not on `sys.path`.

**Location**: `Backend/app/workers/news_ingest_bot.py`

**Root Cause**: The worker was missing the standard `BACKEND_DIR` path setup that other workers use. When pytest imports the worker module, Python cannot resolve `from services.news_ingest_service` imports because `Backend/` is not in `sys.path`.

**Fix Applied**: Added the standard path setup pattern used by other workers:

```python
import sys
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent.parent           # .../Backend/app
BACKEND_DIR = APP_DIR.parent                # .../Backend

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))    # .../Backend
```

**Reference**: See `Backend/app/workers/news_ingest_bot.py` lines 10-18. Matches pattern from `Backend/app/workers/verify_locations.py`, `Backend/app/workers/discovery_bot.py`, `Backend/app/workers/monitor_bot.py`, and `Backend/app/workers/alert_bot.py`.

**Status**: Fixed (October 2025)

---

## Known Remaining Technical Debt

### Worker Import Path Consistency

**Location**: `Backend/app/workers/news_classify_bot.py`

**Issue**: `news_classify_bot.py` may also be missing the standard sys.path setup pattern, similar to the issue fixed in `news_ingest_bot.py`. This was explicitly out-of-scope for the current fix.

**Recommendation**: Audit all workers in `Backend/app/workers/` to ensure consistent import path handling. Consider standardizing worker bootstrap to avoid per-file sys.path manipulation.

**Status**: Not addressed (future work)

---

## Future Refactoring Opportunities

### Standardize Worker Bootstrap

**Goal**: Remove per-file `sys.path` manipulation from workers.

**Current State**: Multiple workers manually manipulate `sys.path` to add `Backend/` directory:

- `verify_locations.py`
- `discovery_bot.py`
- `monitor_bot.py`
- `alert_bot.py`
- `news_ingest_bot.py` (recently fixed)
- Potentially others

**Proposed Solutions**:

1. **Package Structure**: Convert workers to a proper package structure with `__init__.py` files that handle path setup centrally.

2. **PYTHONPATH Setup**: Configure `PYTHONPATH` environment variable in CI/CD, development environments, and runtime scripts to include `Backend/` directory.

3. **Shared Bootstrap Module**: Create a `Backend/app/workers/_bootstrap.py` that workers import to ensure path setup is consistent and centralized.

4. **Direct Imports**: Refactor workers to use relative imports or ensure project root is always in `sys.path` through entry points.

**Benefits**: 
- Reduces code duplication
- Centralizes path management
- Simplifies worker maintenance
- Reduces risk of import errors

**Priority**: Medium (nice-to-have, not blocking)

---

### Legacy Script Import Patterns

**Issue**: `test_migrate_google_to_osm.py` uses `importlib.util.spec_from_file_location` to load a script as a module, which is non-standard and fragile.

**Location**: `Backend/tests/test_migrate_google_to_osm.py` loading `Backend/scripts/migrate_google_to_osm.py`

**Current Approach**: Dynamic module loading via importlib.

**Proposed Solutions**:

1. **Direct Import**: Convert `migrate_google_to_osm.py` to a proper module that can be imported directly with standard Python import mechanism.

2. **Test Utilities Module**: Extract `normalize_name` and `similarity_ratio` functions from the script into a shared utility module that both the script and tests can import.

3. **Script Package Structure**: Create `Backend/scripts/__init__.py` and structure scripts as importable modules.

**Benefits**:
- Eliminates fragile importlib patterns
- Makes functions testable without dynamic loading
- Aligns with Python best practices
- Easier to maintain and debug

**Priority**: Low (script is legacy and not actively used, but good for code quality)

---

## Notes

- All fixes maintain backward compatibility with Python 3.11.9 (CI) and Python 3.13 (local dev).
- No functional changes were made to ingest, discovery, or classification pipelines.
- Test suite should now run without collection errors on both Python versions.










