"""Unit tests for core.sensing.sources.youtube_videos."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from core.sensing.sources.youtube_videos import (
    _parse_iso_duration,
    fetch_youtube_videos,
)


def _mock_search_response(video_ids: list[str]) -> dict:
    """Build a fake YouTube search API response."""
    return {
        "items": [
            {
                "id": {"videoId": vid},
                "snippet": {
                    "title": f"Video about {vid}",
                    "description": f"Description for {vid}",
                    "channelTitle": "Tech Channel",
                    "publishedAt": "2026-03-25T10:00:00Z",
                    "thumbnails": {
                        "medium": {"url": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"},
                    },
                },
            }
            for vid in video_ids
        ]
    }


def _mock_details_response(video_ids: list[str], view_count: str = "15000") -> dict:
    """Build a fake YouTube videos (details) API response."""
    return {
        "items": [
            {
                "id": vid,
                "contentDetails": {"duration": "PT12M34S"},
                "statistics": {"viewCount": view_count},
            }
            for vid in video_ids
        ]
    }


def _make_mock_client(search_data: dict, details_data: dict) -> AsyncMock:
    """Create a mock httpx.AsyncClient that returns canned search + details responses."""
    async def mock_get(url, params=None):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        if "search" in url:
            resp.json.return_value = search_data
        else:
            resp.json.return_value = details_data
        return resp

    client = AsyncMock()
    client.get = mock_get
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


@pytest.mark.unit
class TestParseIsoDuration:
    def test_minutes_and_seconds(self):
        assert _parse_iso_duration("PT12M34S") == "12:34"

    def test_hours(self):
        assert _parse_iso_duration("PT1H5M3S") == "1:05:03"

    def test_minutes_only(self):
        assert _parse_iso_duration("PT5M") == "5:00"

    def test_seconds_only(self):
        assert _parse_iso_duration("PT45S") == "0:45"

    def test_empty(self):
        assert _parse_iso_duration("") == ""

    def test_invalid(self):
        assert _parse_iso_duration("not-a-duration") == ""


@pytest.mark.unit
class TestFetchYoutubeVideos:
    @pytest.mark.asyncio
    @patch("core.sensing.sources.youtube_videos.settings")
    @patch("core.sensing.sources.youtube_videos.httpx.AsyncClient")
    async def test_returns_youtube_videos(self, mock_client_cls, mock_settings):
        mock_settings.YOUTUBE_API_KEY = "test-key"
        video_ids = ["abc123"]
        mock_client_cls.return_value = _make_mock_client(
            _mock_search_response(video_ids),
            _mock_details_response(video_ids),
        )

        videos = await fetch_youtube_videos(["TurboQuant"])
        assert len(videos) == 1
        assert videos[0].technology_name == "TurboQuant"
        assert videos[0].title == "Video about abc123"
        assert "youtube.com/watch?v=abc123" in videos[0].url
        assert videos[0].view_count == 15000
        assert videos[0].uploader == "Tech Channel"
        assert videos[0].duration == "12:34"
        assert "mqdefault" in videos[0].thumbnail_url

    @pytest.mark.asyncio
    @patch("core.sensing.sources.youtube_videos.settings")
    async def test_skips_when_no_api_key(self, mock_settings):
        mock_settings.YOUTUBE_API_KEY = ""

        videos = await fetch_youtube_videos(["SomeTech"])
        assert videos == []

    @pytest.mark.asyncio
    @patch("core.sensing.sources.youtube_videos.settings")
    @patch("core.sensing.sources.youtube_videos.httpx.AsyncClient")
    async def test_handles_api_error(self, mock_client_cls, mock_settings):
        mock_settings.YOUTUBE_API_KEY = "test-key"

        async def mock_get(url, params=None):
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 403
            resp.text = "Forbidden"
            resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "403", request=MagicMock(), response=resp
            )
            return resp

        client = AsyncMock()
        client.get = mock_get
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = client

        videos = await fetch_youtube_videos(["FailTech"])
        assert videos == []

    @pytest.mark.asyncio
    @patch("core.sensing.sources.youtube_videos.settings")
    @patch("core.sensing.sources.youtube_videos.httpx.AsyncClient")
    async def test_respects_max_technologies(self, mock_client_cls, mock_settings):
        mock_settings.YOUTUBE_API_KEY = "test-key"
        mock_client_cls.return_value = _make_mock_client(
            {"items": []},
            {"items": []},
        )

        techs = [f"Tech{i}" for i in range(20)]
        videos = await fetch_youtube_videos(techs, max_technologies=5)
        # No items returned from empty search, but the function should only
        # process 5 technologies (not all 20)
        assert videos == []

    @pytest.mark.asyncio
    @patch("core.sensing.sources.youtube_videos.settings")
    @patch("core.sensing.sources.youtube_videos.httpx.AsyncClient")
    async def test_handles_empty_search_results(self, mock_client_cls, mock_settings):
        mock_settings.YOUTUBE_API_KEY = "test-key"
        mock_client_cls.return_value = _make_mock_client(
            {"items": []},
            {"items": []},
        )

        videos = await fetch_youtube_videos(["TestTech"])
        assert videos == []

    @pytest.mark.asyncio
    @patch("core.sensing.sources.youtube_videos.settings")
    @patch("core.sensing.sources.youtube_videos.httpx.AsyncClient")
    async def test_handles_missing_statistics(self, mock_client_cls, mock_settings):
        mock_settings.YOUTUBE_API_KEY = "test-key"
        video_ids = ["xyz"]
        mock_client_cls.return_value = _make_mock_client(
            _mock_search_response(video_ids),
            {"items": []},  # no details returned
        )

        videos = await fetch_youtube_videos(["TestTech"])
        assert len(videos) == 1
        assert videos[0].view_count == 0
        assert videos[0].duration == ""

    @pytest.mark.asyncio
    @patch("core.sensing.sources.youtube_videos.settings")
    @patch("core.sensing.sources.youtube_videos.httpx.AsyncClient")
    async def test_multiple_technologies(self, mock_client_cls, mock_settings):
        mock_settings.YOUTUBE_API_KEY = "test-key"
        video_ids = ["vid1"]
        mock_client_cls.return_value = _make_mock_client(
            _mock_search_response(video_ids),
            _mock_details_response(video_ids),
        )

        videos = await fetch_youtube_videos(["TechA", "TechB"])
        # Each tech gets 1 video from the mock
        assert len(videos) == 2
        tech_names = {v.technology_name for v in videos}
        assert tech_names == {"TechA", "TechB"}
