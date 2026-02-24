"""
Unit tests for core.studio_features.mind_map — mind map building logic.
"""

import pytest


@pytest.mark.unit
class TestBuildMindmapGlobal:
    def test_single_root_node(self):
        from core.studio_features.mind_map import build_mindmap_global

        flat_nodes = [
            {"id": "1", "title": "Root", "parent_id": None, "description": "Root node"},
        ]
        result = build_mindmap_global(flat_nodes, "u1", "t1")
        assert len(result.roots) == 1
        assert result.roots[0].title == "Root"

    def test_parent_child_relationship(self):
        from core.studio_features.mind_map import build_mindmap_global

        flat_nodes = [
            {"id": "1", "title": "Root", "parent_id": None, "description": "Root"},
            {"id": "2", "title": "Child 1", "parent_id": "1", "description": "Child"},
            {"id": "3", "title": "Child 2", "parent_id": "1", "description": "Child"},
        ]
        result = build_mindmap_global(flat_nodes, "u1", "t1")
        assert len(result.roots) == 1
        assert len(result.roots[0].children) == 2

    def test_nested_hierarchy(self):
        from core.studio_features.mind_map import build_mindmap_global

        flat_nodes = [
            {"id": "1", "title": "Root", "parent_id": None, "description": "R"},
            {"id": "2", "title": "L1", "parent_id": "1", "description": "L1"},
            {"id": "3", "title": "L2", "parent_id": "2", "description": "L2"},
        ]
        result = build_mindmap_global(flat_nodes, "u1", "t1")
        assert len(result.roots) == 1
        assert len(result.roots[0].children) == 1
        assert len(result.roots[0].children[0].children) == 1

    def test_multiple_roots(self):
        from core.studio_features.mind_map import build_mindmap_global

        flat_nodes = [
            {"id": "1", "title": "Root A", "parent_id": None, "description": "A"},
            {"id": "2", "title": "Root B", "parent_id": None, "description": "B"},
        ]
        result = build_mindmap_global(flat_nodes, "u1", "t1")
        assert len(result.roots) == 2

    def test_empty_nodes(self):
        from core.studio_features.mind_map import build_mindmap_global

        result = build_mindmap_global([], "u1", "t1")
        assert len(result.roots) == 0

    def test_orphan_node_becomes_root(self):
        from core.studio_features.mind_map import build_mindmap_global

        flat_nodes = [
            {"id": "1", "title": "Root", "parent_id": None, "description": "R"},
            {
                "id": "2",
                "title": "Orphan",
                "parent_id": "999",
                "description": "O",
            },  # parent doesn't exist
        ]
        result = build_mindmap_global(flat_nodes, "u1", "t1")
        # Root should have 0 children (orphan's parent doesn't exist)
        assert len(result.roots) == 1

    def test_user_and_thread_ids_set(self):
        from core.studio_features.mind_map import build_mindmap_global

        result = build_mindmap_global([], "user_abc", "thread_xyz")
        assert result.user_id == "user_abc"
        assert result.thread_id == "thread_xyz"
