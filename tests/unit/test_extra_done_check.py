"""
Unit tests for core.utils.extra_done_check — thread extra_done flag management.
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.unit
class TestIsExtraDone:
    @patch("core.utils.extra_done_check.db")
    def test_returns_true_when_extra_done(self, mock_db):
        from core.utils.extra_done_check import is_extra_done

        mock_db.users.find_one.return_value = {"threads": {"t1": {"extra_done": True}}}
        assert is_extra_done("user1", "t1") is True

    @patch("core.utils.extra_done_check.db")
    def test_returns_false_when_not_done(self, mock_db):
        from core.utils.extra_done_check import is_extra_done

        mock_db.users.find_one.return_value = {"threads": {"t1": {"extra_done": False}}}
        assert is_extra_done("user1", "t1") is False

    @patch("core.utils.extra_done_check.db")
    def test_returns_false_when_user_not_found(self, mock_db):
        from core.utils.extra_done_check import is_extra_done

        mock_db.users.find_one.return_value = None
        assert is_extra_done("user1", "t1") is False

    @patch("core.utils.extra_done_check.db")
    def test_returns_false_when_no_threads(self, mock_db):
        from core.utils.extra_done_check import is_extra_done

        mock_db.users.find_one.return_value = {"threads": {}}
        assert is_extra_done("user1", "t1") is False

    @patch("core.utils.extra_done_check.db")
    def test_returns_false_when_missing_key(self, mock_db):
        from core.utils.extra_done_check import is_extra_done

        mock_db.users.find_one.return_value = {"threads": {"t1": {}}}
        assert is_extra_done("user1", "t1") is False


@pytest.mark.unit
class TestMarkExtraDone:
    @patch("core.utils.extra_done_check.db")
    def test_marks_done_successfully(self, mock_db):
        from core.utils.extra_done_check import mark_extra_done

        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_db.users.update_one.return_value = mock_result
        assert mark_extra_done("user1", "t1") is True

    @patch("core.utils.extra_done_check.db")
    def test_returns_false_when_no_modification(self, mock_db):
        from core.utils.extra_done_check import mark_extra_done

        mock_result = MagicMock()
        mock_result.modified_count = 0
        mock_db.users.update_one.return_value = mock_result
        assert mark_extra_done("user1", "t1") is False

    @patch("core.utils.extra_done_check.db")
    def test_handles_exception(self, mock_db):
        from core.utils.extra_done_check import mark_extra_done

        mock_db.users.update_one.side_effect = Exception("DB error")
        assert mark_extra_done("user1", "t1") is False

    @patch("core.utils.extra_done_check.db")
    def test_mark_undone(self, mock_db):
        from core.utils.extra_done_check import mark_extra_done

        mock_result = MagicMock()
        mock_result.modified_count = 1
        mock_db.users.update_one.return_value = mock_result
        assert mark_extra_done("user1", "t1", value=False) is True
        # Verify the update call had value=False
        call_args = mock_db.users.update_one.call_args
        assert call_args[0][1]["$set"]["threads.t1.extra_done"] is False
