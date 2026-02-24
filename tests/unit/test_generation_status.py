"""
Unit tests for core.utils.generation_status — async file-based generation status tracking.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestWritePendingStatus:
    @pytest.mark.asyncio
    async def test_creates_file(self, tmp_path):
        from core.utils.generation_status import write_pending_status

        file_path = str(tmp_path / "subdir" / "status.json")
        await write_pending_status(file_path)
        assert os.path.exists(file_path)

    @pytest.mark.asyncio
    async def test_creates_subdirectories(self, tmp_path):
        from core.utils.generation_status import write_pending_status

        file_path = str(tmp_path / "a" / "b" / "c" / "status.json")
        await write_pending_status(file_path)
        assert os.path.exists(file_path)

    @pytest.mark.asyncio
    async def test_contains_pending_status(self, tmp_path):
        from core.utils.generation_status import write_pending_status

        file_path = str(tmp_path / "status.json")
        await write_pending_status(file_path)
        with open(file_path) as f:
            data = json.load(f)
        assert data["_status"] == "pending"
        assert "started_at" in data


@pytest.mark.unit
class TestWriteFailedStatus:
    @pytest.mark.asyncio
    async def test_writes_failed_status(self, tmp_path):
        from core.utils.generation_status import write_failed_status

        file_path = str(tmp_path / "status.json")
        await write_failed_status(file_path, "Something went wrong")
        with open(file_path) as f:
            data = json.load(f)
        assert data["_status"] == "failed"
        assert data["error"] == "Something went wrong"
        assert "failed_at" in data

    @pytest.mark.asyncio
    async def test_handles_write_error_gracefully(self):
        from core.utils.generation_status import write_failed_status

        # Invalid path should not raise
        await write_failed_status(
            "/nonexistent/path/that/cant/be/written/status.json", "err"
        )


@pytest.mark.unit
class TestWriteResult:
    @pytest.mark.asyncio
    async def test_writes_result_data(self, tmp_path):
        from core.utils.generation_status import write_result

        file_path = str(tmp_path / "result.json")
        data = {"key": "value", "count": 42}
        await write_result(file_path, data)
        with open(file_path) as f:
            loaded = json.load(f)
        assert loaded["key"] == "value"
        assert loaded["count"] == 42


@pytest.mark.unit
class TestReadGenerationStatus:
    @pytest.mark.asyncio
    async def test_nonexistent_file_returns_none(self, tmp_path):
        from core.utils.generation_status import read_generation_status

        result = await read_generation_status(str(tmp_path / "nope.json"))
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_file_returns_failed(self, tmp_path):
        from core.utils.generation_status import read_generation_status

        file_path = tmp_path / "empty.json"
        file_path.write_text("")
        result = await read_generation_status(str(file_path))
        assert result["state"] == "failed"

    @pytest.mark.asyncio
    async def test_corrupted_json_returns_failed(self, tmp_path):
        from core.utils.generation_status import read_generation_status

        file_path = tmp_path / "bad.json"
        file_path.write_text("{not valid json")
        result = await read_generation_status(str(file_path))
        assert result["state"] == "failed"

    @pytest.mark.asyncio
    async def test_pending_status_returns_pending(self, tmp_path):
        from core.utils.generation_status import read_generation_status

        file_path = tmp_path / "pending.json"
        data = {
            "_status": "pending",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        file_path.write_text(json.dumps(data))
        result = await read_generation_status(str(file_path))
        assert result["state"] == "pending"

    @pytest.mark.asyncio
    async def test_stale_pending_returns_failed(self, tmp_path):
        from core.utils.generation_status import read_generation_status

        file_path = tmp_path / "stale.json"
        old_time = datetime.now(timezone.utc) - timedelta(minutes=15)
        data = {"_status": "pending", "started_at": old_time.isoformat()}
        file_path.write_text(json.dumps(data))
        result = await read_generation_status(str(file_path))
        assert result["state"] == "failed"
        assert "timed out" in result["error"]

    @pytest.mark.asyncio
    async def test_failed_status_returns_failure(self, tmp_path):
        from core.utils.generation_status import read_generation_status

        file_path = tmp_path / "failed.json"
        data = {"_status": "failed", "error": "LLM error"}
        file_path.write_text(json.dumps(data))
        result = await read_generation_status(str(file_path))
        assert result["state"] == "failed"
        assert result["error"] == "LLM error"

    @pytest.mark.asyncio
    async def test_completed_result(self, tmp_path):
        from core.utils.generation_status import read_generation_status

        file_path = tmp_path / "done.json"
        data = {"title": "My Summary", "content": "Summary text"}
        file_path.write_text(json.dumps(data))
        result = await read_generation_status(str(file_path))
        assert result["state"] == "completed"
        assert result["data"]["title"] == "My Summary"

    @pytest.mark.asyncio
    async def test_non_dict_json_returns_failed(self, tmp_path):
        from core.utils.generation_status import read_generation_status

        file_path = tmp_path / "array.json"
        file_path.write_text(json.dumps([1, 2, 3]))
        result = await read_generation_status(str(file_path))
        assert result["state"] == "failed"
