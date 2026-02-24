# Testing Guide — PRISM NotebookLM Backend

## Quick Start

```powershell
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov --cov-report=term-missing

# Or use the helper script (Windows)
.\run_tests.ps1             # All tests + coverage
.\run_tests.ps1 unit        # Unit tests only
.\run_tests.ps1 integration # Integration tests only
.\run_tests.ps1 e2e         # E2E tests only
.\run_tests.ps1 fast        # Parallel with pytest-xdist
.\run_tests.ps1 coverage    # HTML coverage report
```

---

## Test Structure

```
tests/
├── conftest.py            # Root fixtures (DB mocks, auth, clients)
├── factories.py           # Deterministic test data builders
├── __init__.py
├── unit/                  # Isolated function-level tests
│   ├── __init__.py
│   ├── test_auth.py
│   ├── test_bcrypt.py
│   ├── test_combination.py
│   ├── test_compress_data.py
│   ├── test_config.py
│   ├── test_constants.py
│   ├── test_count_tokens.py
│   ├── test_decomposition.py
│   ├── test_extensions.py
│   ├── test_extra_done_check.py
│   ├── test_generation_status.py
│   ├── test_graph_helpers.py
│   ├── test_graph_nodes.py
│   ├── test_llm_client.py
│   ├── test_llm_output_sanitizer.py
│   ├── test_mind_map.py
│   ├── test_models.py
│   ├── test_retriever.py
│   ├── test_sanitize_schema.py
│   ├── test_search_tool.py
│   ├── test_socket_handler.py
│   ├── test_sql_query.py
│   ├── test_studio_features.py
│   └── test_vectorstore.py
├── integration/           # API endpoint tests (FastAPI + mocked DB)
│   ├── __init__.py
│   ├── test_documents_api.py
│   ├── test_export_api.py
│   ├── test_extra_api.py
│   ├── test_health_api.py
│   ├── test_query_api.py
│   ├── test_studio_features_api.py
│   ├── test_thread_api.py
│   ├── test_upload_api.py
│   └── test_user_api.py
└── e2e/                   # Full user journey tests
    ├── __init__.py
    └── test_user_journey.py
```

---

## Test Categories

| Marker                     | Command                 | Scope                              |
| -------------------------- | ----------------------- | ---------------------------------- |
| `@pytest.mark.unit`        | `pytest -m unit`        | Isolated pure-logic tests          |
| `@pytest.mark.integration` | `pytest -m integration` | HTTP endpoint tests with mocked DB |
| `@pytest.mark.e2e`         | `pytest -m e2e`         | Multi-step user flows              |
| `@pytest.mark.slow`        | `pytest -m slow`        | Long-running tests                 |

---

## Coverage Enforcement

Coverage is configured in `pytest.ini`:

- **Minimum threshold**: 90% (tests fail if coverage drops below)
- **Source directories**: `app`, `core`, `agent`
- **Excluded**: config files, prompt templates, output schemas, `__pycache__`

### View coverage report

```bash
# Terminal summary
python -m pytest --cov --cov-report=term-missing

# HTML report (open htmlcov/index.html)
python -m pytest --cov --cov-report=html
```

---

## Key Fixtures (in `conftest.py`)

| Fixture                                | Purpose                                    |
| -------------------------------------- | ------------------------------------------ |
| `mock_db`                              | Clean mongomock database                   |
| `patched_db`                           | Patches `core.database.db` globally        |
| `populated_db`                         | Pre-inserts a test user with one thread    |
| `auth_token` / `auth_headers`          | Valid JWT token + headers                  |
| `async_client`                         | httpx `AsyncClient` wrapping FastAPI app   |
| `mock_sio`                             | Mocked Socket.IO to prevent real emissions |
| `mock_invoke_llm`                      | Mocked LLM invocation                      |
| `mock_tavily`                          | Mocked web search                          |
| `mock_embeddings` / `mock_vectorstore` | Mocked embedding + vector operations       |
| `tmp_data_dir`                         | Temporary file tree mimicking `data/`      |

---

## Writing New Tests

### Adding a unit test

1. Create a file in `tests/unit/test_<module>.py`
2. Mark your test class/function with `@pytest.mark.unit`
3. Mock external dependencies, test one function at a time

```python
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.unit
class TestMyFunction:
    def test_basic_case(self):
        from core.utils.my_module import my_function
        result = my_function("input")
        assert result == "expected"

    @patch("core.utils.my_module.external_call")
    def test_with_mock(self, mock_call):
        mock_call.return_value = "mocked"
        from core.utils.my_module import my_function
        assert my_function("x") == "mocked"
```

### Adding an integration test for a new endpoint

1. Create a file in `tests/integration/test_<route>_api.py`
2. Use `async_client`, `populated_db`, and `auth_headers` fixtures
3. Test success path, auth failures, validation errors, and edge cases

```python
import pytest

@pytest.mark.integration
class TestMyEndpoint:
    @pytest.mark.asyncio
    async def test_success(self, async_client, populated_db, auth_headers):
        response = await async_client.get("/my-endpoint", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    @pytest.mark.asyncio
    async def test_no_auth(self, async_client, patched_db):
        response = await async_client.get("/my-endpoint")
        assert response.status_code == 401
```

### Adding an E2E test

1. Add to `tests/e2e/test_user_journey.py` or create a new file
2. Chain multiple API calls simulating a real user flow
3. Verify cross-endpoint state consistency

---

## CI/CD Integration

The GitHub Actions workflow (`.github/workflows/backend-tests.yml`) runs on all
pushes and PRs to `main` and `develop`:

1. **Matrix**: Tests on Python 3.11 and 3.12
2. **Coverage**: Enforces 90% minimum, uploads XML report as artifact
3. **Lint**: Runs `ruff` on source directories
4. **Artifacts**: Test results (JUnit XML) + coverage report uploaded per run

---

## Troubleshooting

### Tests hang or time out

- Check for unmocked async calls (LLM, embeddings, socket emissions)
- Add `@pytest.mark.timeout(10)` to suspect tests
- Ensure `mock_sio` fixture is included for any test importing the app

### Coverage below 90%

```bash
# Find uncovered lines
python -m pytest --cov --cov-report=term-missing | grep "MISS"

# Generate detailed HTML report
python -m pytest --cov --cov-report=html
# Open htmlcov/index.html in a browser
```

### Import errors

- Run from the `backend/` directory
- Ensure `requirements-test.txt` dependencies are installed
- Test environment variables are set in `conftest.py` (line 23-42)

### MongoDB mock issues

- Use `patched_db` fixture — it patches `core.database.db` globally
- For tests that insert data, use `populated_db` (user + thread pre-inserted)
- Mongomock has limitations with aggregation pipelines; mock those directly
