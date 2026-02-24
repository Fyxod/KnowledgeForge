"""
Unit tests for agent.tools.sql_query — SQL execution and schema retrieval.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.unit
class TestExecuteSqlQuery:
    @pytest.mark.asyncio
    @patch("agent.tools.sql_query.SQLiteManager")
    async def test_no_spreadsheet_data(self, mock_mgr):
        from agent.tools.sql_query import execute_sql_query

        mock_mgr.has_spreadsheet_data.return_value = False
        result = await execute_sql_query("u1", "t1", "SELECT 1")
        assert "No spreadsheet data" in result

    @pytest.mark.asyncio
    @patch("agent.tools.sql_query.SQLiteManager")
    async def test_successful_query(self, mock_mgr):
        from agent.tools.sql_query import execute_sql_query

        mock_mgr.has_spreadsheet_data.return_value = True
        mock_mgr.execute_query.return_value = {
            "success": True,
            "row_count": 5,
            "data": "col1\n1\n2\n3\n4\n5",
            "truncated": False,
        }
        result = await execute_sql_query("u1", "t1", "SELECT * FROM test")
        assert "Query executed successfully" in result
        assert "Rows returned: 5" in result

    @pytest.mark.asyncio
    @patch("agent.tools.sql_query.SQLiteManager")
    async def test_failed_query(self, mock_mgr):
        from agent.tools.sql_query import execute_sql_query

        mock_mgr.has_spreadsheet_data.return_value = True
        mock_mgr.execute_query.return_value = {
            "success": False,
            "error": "no such table: missing_table",
        }
        result = await execute_sql_query("u1", "t1", "SELECT * FROM missing_table")
        assert "SQL query failed" in result

    @pytest.mark.asyncio
    @patch("agent.tools.sql_query.SQLiteManager")
    async def test_truncated_results(self, mock_mgr):
        from agent.tools.sql_query import execute_sql_query

        mock_mgr.has_spreadsheet_data.return_value = True
        mock_mgr.execute_query.return_value = {
            "success": True,
            "row_count": 1000,
            "data": "...",
            "truncated": True,
        }
        result = await execute_sql_query("u1", "t1", "SELECT *")
        assert "Showing first 500" in result


@pytest.mark.unit
class TestGetSqlSchema:
    @patch("agent.tools.sql_query.SQLiteManager")
    def test_returns_schema(self, mock_mgr):
        from agent.tools.sql_query import get_sql_schema

        mock_mgr.get_schema.return_value = "CREATE TABLE test (id INT)"
        result = get_sql_schema("u1", "t1")
        assert "CREATE TABLE" in result
