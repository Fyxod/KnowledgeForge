"""Unit tests for core.sensing.sources.youtube_videos."""

from unittest.mock import patch

import pytest

from core.sensing.sources.youtube_videos import fetch_youtube_videos


@pytest.mark.unit
class TestFetchYoutubeVideos:
    @pytest.mark.asyncio
    @patch("core.sensing.sources.youtube_videos._ddgs_video_search")
    async def test_returns_youtube_videos(self, mock_search):
        mock_search.return_value = [
            {
                "title": "TurboQuant Tutorial",
                "content": "https://www.youtube.com/watch?v=abc123",
                "description": "A tutorial on TurboQuant",
                "publisher": "YouTube",
                "uploader": "Tech Channel",
                "duration": "12:34",
                "published": "2026-03-25",
                "statistics": {"viewCount": "15000"},
                "images": {
                    "medium": "https://img.youtube.com/vi/abc123/mqdefault.jpg"
                },
            }
        ]

        videos = await fetch_youtube_videos(["TurboQuant"])
        assert len(videos) == 1
        assert videos[0].technology_name == "TurboQuant"
        assert videos[0].title == "TurboQuant Tutorial"
        assert "youtube.com" in videos[0].url
        assert videos[0].view_count == 15000
        assert videos[0].uploader == "Tech Channel"
        assert videos[0].thumbnail_url == "https://img.youtube.com/vi/abc123/mqdefault.jpg"

    @pytest.mark.asyncio
    @patch("core.sensing.sources.youtube_videos._ddgs_video_search")
    async def test_filters_non_youtube_results(self, mock_search):
        mock_search.return_value = [
            {
                "title": "Vimeo Video",
                "content": "https://vimeo.com/123456",
                "description": "Not YouTube",
                "publisher": "Vimeo",
                "uploader": "Someone",
                "duration": "5:00",
                "published": "2026-03-20",
                "statistics": {"viewCount": "100"},
                "images": {},
            }
        ]

        videos = await fetch_youtube_videos(["SomeTech"])
        assert len(videos) == 0

    @pytest.mark.asyncio
    @patch("core.sensing.sources.youtube_videos._ddgs_video_search")
    async def test_handles_search_failure(self, mock_search):
        mock_search.side_effect = Exception("Rate limited")

        videos = await fetch_youtube_videos(["FailTech"])
        assert videos == []

    @pytest.mark.asyncio
    @patch("core.sensing.sources.youtube_videos._ddgs_video_search")
    async def test_respects_max_technologies(self, mock_search):
        mock_search.return_value = []
        techs = [f"Tech{i}" for i in range(20)]

        await fetch_youtube_videos(techs, max_technologies=5)

        assert mock_search.call_count == 5

    @pytest.mark.asyncio
    @patch("core.sensing.sources.youtube_videos._ddgs_video_search")
    async def test_handles_missing_statistics(self, mock_search):
        mock_search.return_value = [
            {
                "title": "No Stats Video",
                "content": "https://www.youtube.com/watch?v=xyz",
                "description": "",
                "publisher": "YouTube",
                "uploader": "Channel",
                "duration": "3:00",
                "published": "",
                "statistics": {},
                "images": {},
            }
        ]

        videos = await fetch_youtube_videos(["TestTech"])
        assert len(videos) == 1
        assert videos[0].view_count == 0
        assert videos[0].thumbnail_url == ""

    @pytest.mark.asyncio
    @patch("core.sensing.sources.youtube_videos._ddgs_video_search")
    async def test_limits_videos_per_technology(self, mock_search):
        mock_search.return_value = [
            {
                "title": f"Video {i}",
                "content": f"https://www.youtube.com/watch?v=vid{i}",
                "description": f"Description {i}",
                "publisher": "YouTube",
                "uploader": "Channel",
                "duration": "5:00",
                "published": "2026-03-25",
                "statistics": {"viewCount": "1000"},
                "images": {"medium": f"https://img.youtube.com/vi/vid{i}/mqdefault.jpg"},
            }
            for i in range(10)
        ]

        videos = await fetch_youtube_videos(["TestTech"], max_videos_per_tech=3)
        assert len(videos) == 3

    @pytest.mark.asyncio
    @patch("core.sensing.sources.youtube_videos._ddgs_video_search")
    async def test_youtu_be_urls_accepted(self, mock_search):
        mock_search.return_value = [
            {
                "title": "Short URL Video",
                "content": "https://youtu.be/abc123",
                "description": "Uses short URL",
                "publisher": "YouTube",
                "uploader": "Channel",
                "duration": "2:00",
                "published": "2026-03-25",
                "statistics": {"viewCount": "500"},
                "images": {},
            }
        ]

        videos = await fetch_youtube_videos(["TestTech"])
        assert len(videos) == 1
        assert "youtu.be" in videos[0].url
