"""
Tests for purchase order endpoints.
"""
import pytest


class TestCreatePurchaseOrder:
    """Test suite for creating purchase orders."""

    def test_create_purchase_order_success(self, client):
        """Test creating a purchase order for a backlog item."""
        response = client.post("/api/purchase-orders", json={
            "backlog_item_id": "1",
            "supplier_name": "Acme Parts Co.",
            "quantity": 500,
            "unit_cost": 12.5,
            "expected_delivery_date": "2025-10-15",
            "notes": "Rush order"
        })
        assert response.status_code == 201

        data = response.json()
        assert data["backlog_item_id"] == "1"
        assert data["supplier_name"] == "Acme Parts Co."
        assert data["quantity"] == 500
        assert data["unit_cost"] == 12.5
        assert data["status"] == "Pending"
        assert data["notes"] == "Rush order"
        assert "id" in data
        assert "created_date" in data

    def test_create_purchase_order_without_notes(self, client):
        """Test creating a purchase order without the optional notes field."""
        response = client.post("/api/purchase-orders", json={
            "backlog_item_id": "2",
            "supplier_name": "Global Supply Inc.",
            "quantity": 100,
            "unit_cost": 45.0,
            "expected_delivery_date": "2025-10-20"
        })
        assert response.status_code == 201

        data = response.json()
        assert data["notes"] is None

    def test_create_purchase_order_nonexistent_backlog_item(self, client):
        """Test creating a purchase order for a backlog item that doesn't exist."""
        response = client.post("/api/purchase-orders", json={
            "backlog_item_id": "nonexistent-999",
            "supplier_name": "Acme Parts Co.",
            "quantity": 10,
            "unit_cost": 5.0,
            "expected_delivery_date": "2025-10-15"
        })
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data

    def test_create_duplicate_purchase_order_rejected(self, client):
        """Test that a second purchase order for the same backlog item is rejected."""
        first = client.post("/api/purchase-orders", json={
            "backlog_item_id": "3",
            "supplier_name": "First Supplier",
            "quantity": 50,
            "unit_cost": 10.0,
            "expected_delivery_date": "2025-10-25"
        })
        assert first.status_code == 201

        second = client.post("/api/purchase-orders", json={
            "backlog_item_id": "3",
            "supplier_name": "Second Supplier",
            "quantity": 20,
            "unit_cost": 8.0,
            "expected_delivery_date": "2025-11-01"
        })
        assert second.status_code == 400

        data = second.json()
        assert "detail" in data


class TestGetPurchaseOrderByBacklogItem:
    """Test suite for fetching a purchase order by backlog item id."""

    def test_get_purchase_order_by_backlog_item_success(self, client):
        """Test getting a purchase order right after creating it."""
        create_response = client.post("/api/purchase-orders", json={
            "backlog_item_id": "4",
            "supplier_name": "Precision Components",
            "quantity": 200,
            "unit_cost": 22.0,
            "expected_delivery_date": "2025-10-30"
        })
        assert create_response.status_code == 201

        response = client.get("/api/purchase-orders/4")
        assert response.status_code == 200

        data = response.json()
        assert data["backlog_item_id"] == "4"
        assert data["supplier_name"] == "Precision Components"

    def test_get_purchase_order_nonexistent(self, client):
        """Test getting a purchase order for a backlog item that has none."""
        response = client.get("/api/purchase-orders/no-po-for-this-item")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
