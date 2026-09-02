"""
Tests for task management endpoints.
"""
import pytest


class TestGetTasks:
    """Test suite for listing tasks."""

    def test_get_tasks_returns_list(self, client):
        """Test that the tasks endpoint returns an array."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestCreateTask:
    """Test suite for creating tasks."""

    def test_create_task_success(self, client):
        """Test creating a task with all fields."""
        response = client.post("/api/tasks", json={
            "title": "Review Tokyo warehouse shipment",
            "priority": "high",
            "dueDate": "2025-11-01"
        })
        assert response.status_code == 201

        data = response.json()
        assert data["title"] == "Review Tokyo warehouse shipment"
        assert data["priority"] == "high"
        assert data["dueDate"] == "2025-11-01"
        assert data["status"] == "pending"
        assert isinstance(data["id"], int)

    def test_created_task_appears_in_list(self, client):
        """Test that a newly created task shows up in GET /api/tasks."""
        create_response = client.post("/api/tasks", json={
            "title": "Audit circuit board stock",
            "priority": "medium",
            "dueDate": "2025-11-05"
        })
        task_id = create_response.json()["id"]

        list_response = client.get("/api/tasks")
        task_ids = [t["id"] for t in list_response.json()]
        assert task_id in task_ids

    def test_create_task_ids_are_unique(self, client):
        """Test that successively created tasks get distinct ids."""
        first = client.post("/api/tasks", json={
            "title": "Task A",
            "priority": "low",
            "dueDate": "2025-11-10"
        }).json()
        second = client.post("/api/tasks", json={
            "title": "Task B",
            "priority": "low",
            "dueDate": "2025-11-11"
        }).json()
        assert first["id"] != second["id"]

    def test_create_task_missing_field_rejected(self, client):
        """Test that a task missing a required field is rejected."""
        response = client.post("/api/tasks", json={
            "title": "Incomplete task",
            "priority": "low"
        })
        assert response.status_code == 422


class TestToggleTask:
    """Test suite for toggling task status."""

    def test_toggle_task_marks_completed(self, client):
        """Test toggling a pending task marks it completed."""
        created = client.post("/api/tasks", json={
            "title": "Toggle me",
            "priority": "medium",
            "dueDate": "2025-11-15"
        }).json()

        response = client.patch(f"/api/tasks/{created['id']}")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    def test_toggle_task_twice_returns_to_pending(self, client):
        """Test toggling a task twice returns it to pending."""
        created = client.post("/api/tasks", json={
            "title": "Toggle me twice",
            "priority": "medium",
            "dueDate": "2025-11-16"
        }).json()

        client.patch(f"/api/tasks/{created['id']}")
        response = client.patch(f"/api/tasks/{created['id']}")
        assert response.status_code == 200
        assert response.json()["status"] == "pending"

    def test_toggle_nonexistent_task(self, client):
        """Test toggling a task that doesn't exist returns 404."""
        response = client.patch("/api/tasks/999999")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data


class TestDeleteTask:
    """Test suite for deleting tasks."""

    def test_delete_task_success(self, client):
        """Test deleting an existing task."""
        created = client.post("/api/tasks", json={
            "title": "Delete me",
            "priority": "low",
            "dueDate": "2025-11-20"
        }).json()

        response = client.delete(f"/api/tasks/{created['id']}")
        assert response.status_code == 200

        list_response = client.get("/api/tasks")
        task_ids = [t["id"] for t in list_response.json()]
        assert created["id"] not in task_ids

    def test_delete_nonexistent_task(self, client):
        """Test deleting a task that doesn't exist returns 404."""
        response = client.delete("/api/tasks/999999")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
