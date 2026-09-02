"""
Tests for restocking recommendation and order endpoints.
"""
import pytest


class TestRestockingRecommendations:
    """Test suite for the restocking recommendations endpoint."""

    def test_get_recommendations_success(self, client):
        """Test getting recommendations returns expected structure."""
        response = client.get("/api/restocking/recommendations?budget=10000")
        assert response.status_code == 200

        data = response.json()
        assert "budget" in data
        assert "recommendations" in data
        assert "total_cost" in data
        assert "budget_remaining" in data
        assert "items_recommended_count" in data
        assert isinstance(data["recommendations"], list)

    def test_recommendations_respect_budget(self, client):
        """Test that recommended total cost never exceeds the budget."""
        response = client.get("/api/restocking/recommendations?budget=5000")
        data = response.json()
        assert data["total_cost"] <= 5000

    def test_recommendations_zero_budget_returns_empty(self, client):
        """Test that a zero budget recommends nothing."""
        response = client.get("/api/restocking/recommendations?budget=0")
        assert response.status_code == 200

        data = response.json()
        assert data["recommendations"] == []
        assert data["total_cost"] == 0

    def test_recommendations_negative_budget_rejected(self, client):
        """Test that a negative budget is rejected."""
        response = client.get("/api/restocking/recommendations?budget=-100")
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data

    def test_recommendations_priority_items_ranked_first(self, client):
        """Test that priority items (backlog / below reorder point) sort before others."""
        response = client.get("/api/restocking/recommendations?budget=25000")
        data = response.json()

        priority_flags = [r["is_priority"] for r in data["recommendations"]]
        assert priority_flags == sorted(priority_flags, key=lambda is_priority: not is_priority)

    def test_recommendation_item_structure(self, client):
        """Test that each recommendation has the expected fields and types."""
        response = client.get("/api/restocking/recommendations?budget=25000")
        data = response.json()
        assert len(data["recommendations"]) > 0

        item = data["recommendations"][0]
        for field in ["item_sku", "item_name", "current_demand", "forecasted_demand",
                      "trend", "quantity", "unit_cost", "line_total", "is_priority", "priority_reason"]:
            assert field in item

        assert item["quantity"] > 0
        assert item["priority_reason"] in ["backlog", "below_reorder_point", "demand_growth"]

    def test_no_items_with_negative_gap_recommended(self, client):
        """Test that items whose forecasted demand is below current demand are never recommended."""
        response = client.get("/api/restocking/recommendations?budget=25000")
        data = response.json()

        skus = [r["item_sku"] for r in data["recommendations"]]
        assert "MTR-304" not in skus  # forecasted_demand (35) < current_demand (50)

    def test_recommendation_unit_cost_matches_forecast_data(self, client):
        """Test that unit_cost on a recommendation matches the demand_forecasts.json fixture value."""
        response = client.get("/api/restocking/recommendations?budget=25000")
        data = response.json()

        by_sku = {r["item_sku"]: r for r in data["recommendations"]}
        assert "GSK-203" in by_sku
        assert by_sku["GSK-203"]["unit_cost"] == 6.50

    def test_backlog_items_are_priority(self, client):
        """Test that items present in the backlog are flagged as priority with the correct reason."""
        response = client.get("/api/restocking/recommendations?budget=25000")
        data = response.json()

        backlog_skus = ["FLT-405", "MTR-304", "VLV-506", "WDG-001"]
        for r in data["recommendations"]:
            if r["item_sku"] in backlog_skus:
                assert r["is_priority"] is True
                assert r["priority_reason"] == "backlog"


class TestRestockingOrders:
    """Test suite for submitting and listing restocking orders."""

    def test_create_order_success(self, client):
        """Test submitting a restocking order."""
        response = client.post("/api/restocking/orders", json={"budget": 10000})
        assert response.status_code == 201

        order = response.json()
        assert "id" in order
        assert "order_number" in order
        assert order["status"] == "Submitted"
        assert order["lead_time_days"] == 7
        assert len(order["items"]) > 0

    def test_create_order_expected_delivery_matches_lead_time(self, client):
        """Test that expected_delivery is exactly lead_time_days after order_date."""
        import datetime

        response = client.post("/api/restocking/orders", json={"budget": 10000})
        order = response.json()

        order_date = datetime.datetime.fromisoformat(order["order_date"])
        expected_delivery = datetime.datetime.fromisoformat(order["expected_delivery"])
        assert (expected_delivery - order_date).days == order["lead_time_days"]

    def test_create_order_zero_budget_rejected(self, client):
        """Test that a zero budget is rejected (nothing to recommend)."""
        response = client.post("/api/restocking/orders", json={"budget": 0})
        assert response.status_code == 400

    def test_create_order_negative_budget_rejected(self, client):
        """Test that a negative budget is rejected."""
        response = client.post("/api/restocking/orders", json={"budget": -500})
        assert response.status_code == 400

    def test_create_order_missing_budget_rejected(self, client):
        """Test that a missing budget field is a validation error."""
        response = client.post("/api/restocking/orders", json={})
        assert response.status_code == 422

    def test_order_total_cost_matches_line_totals(self, client):
        """Test that total_cost equals the sum of item line totals."""
        response = client.post("/api/restocking/orders", json={"budget": 10000})
        order = response.json()

        calculated = sum(item["line_total"] for item in order["items"])
        assert abs(order["total_cost"] - calculated) < 0.01

    def test_order_item_structure(self, client):
        """Test that submitted order items have the expected fields."""
        response = client.post("/api/restocking/orders", json={"budget": 10000})
        order = response.json()

        for item in order["items"]:
            for field in ["sku", "name", "quantity", "unit_cost", "line_total"]:
                assert field in item

    def test_submitted_order_appears_in_list(self, client):
        """Test that a submitted order shows up in GET /api/restocking/orders."""
        create_response = client.post("/api/restocking/orders", json={"budget": 10000})
        order_number = create_response.json()["order_number"]

        list_response = client.get("/api/restocking/orders")
        assert list_response.status_code == 200

        order_numbers = [o["order_number"] for o in list_response.json()]
        assert order_number in order_numbers

    def test_get_restocking_orders_returns_list(self, client):
        """Test that the orders list endpoint returns an array."""
        response = client.get("/api/restocking/orders")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
