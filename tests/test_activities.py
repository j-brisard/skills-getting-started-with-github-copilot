"""
Test suite for the Mergington High School API activities endpoints.

Tests cover:
- GET /activities endpoint
- POST /activities/{activity_name}/signup endpoint
- DELETE /activities/{activity_name}/unregister endpoint
- Error scenarios and edge cases
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Fixture to provide a TestClient instance for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """
    Fixture to reset the in-memory activities database before each test.
    This ensures test isolation and prevents test pollution.
    """
    # Store original state
    original_activities = {
        activity_name: {
            "description": data["description"],
            "schedule": data["schedule"],
            "max_participants": data["max_participants"],
            "participants": data["participants"].copy()
        }
        for activity_name, data in activities.items()
    }
    
    yield
    
    # Restore original state after test
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    """Test cases for the GET /activities endpoint."""
    
    def test_get_all_activities(self, client, reset_activities):
        """Test that GET /activities returns all activities."""
        response = client.get("/activities")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that we have activities
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Check that specific activities exist
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Basketball Team" in data
    
    def test_get_activities_structure(self, client, reset_activities):
        """Test that activity details contain expected fields."""
        response = client.get("/activities")
        data = response.json()
        
        # Pick any activity and verify structure
        activity = data["Chess Club"]
        
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        assert isinstance(activity["participants"], list)
    
    def test_get_activities_initial_participants(self, client, reset_activities):
        """Test that initial participants are returned correctly."""
        response = client.get("/activities")
        data = response.json()
        
        # Chess Club starts with 2 participants
        assert len(data["Chess Club"]["participants"]) == 2
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in data["Chess Club"]["participants"]


class TestSignupForActivity:
    """Test cases for the POST /activities/{activity_name}/signup endpoint."""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity."""
        email = "newstudent@mergington.edu"
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert "Chess Club" in data["message"]
        
        # Verify participant was added
        assert email in activities["Chess Club"]["participants"]
    
    def test_signup_multiple_students(self, client, reset_activities):
        """Test that multiple different students can sign up for same activity."""
        students = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for email in students:
            response = client.post(
                "/activities/Programming Class/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all students were added
        for email in students:
            assert email in activities["Programming Class"]["participants"]
        
        # Should have original 2 + 3 new = 5 participants
        assert len(activities["Programming Class"]["participants"]) == 5
    
    def test_signup_activity_not_found(self, client, reset_activities):
        """Test signup fails when activity doesn't exist."""
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_already_signed_up(self, client, reset_activities):
        """Test signup fails when student is already signed up."""
        email = "michael@mergington.edu"  # Already in Chess Club
        
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_different_activities(self, client, reset_activities):
        """Test that same student can sign up for multiple different activities."""
        email = "versatile@mergington.edu"
        activities_to_join = ["Chess Club", "Art Club", "Debate Club"]
        
        for activity in activities_to_join:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify student is in all activities
        for activity in activities_to_join:
            assert email in activities[activity]["participants"]


class TestUnregisterFromActivity:
    """Test cases for the DELETE /activities/{activity_name}/unregister endpoint."""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregister from an activity."""
        email = "michael@mergington.edu"  # Already in Chess Club
        
        # Verify student is initially signed up
        assert email in activities["Chess Club"]["participants"]
        
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert "Unregistered" in data["message"]
        
        # Verify participant was removed
        assert email not in activities["Chess Club"]["participants"]
    
    def test_unregister_activity_not_found(self, client, reset_activities):
        """Test unregister fails when activity doesn't exist."""
        response = client.delete(
            "/activities/Nonexistent Activity/unregister",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_unregister_student_not_signed_up(self, client, reset_activities):
        """Test unregister fails when student is not signed up."""
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "notstudent@mergington.edu"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"]
    
    def test_unregister_multiple_participants(self, client, reset_activities):
        """Test unregistering one participant doesn't affect others."""
        activity = "Chess Club"
        initial_participants = activities[activity]["participants"].copy()
        
        # Unregister first participant
        email_to_remove = initial_participants[0]
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email_to_remove}
        )
        
        assert response.status_code == 200
        
        # Verify correct participant was removed
        assert email_to_remove not in activities[activity]["participants"]
        
        # Verify other participants remain
        for email in initial_participants[1:]:
            assert email in activities[activity]["participants"]


class TestIntegrationScenarios:
    """Integration tests covering complete workflows."""
    
    def test_signup_then_unregister(self, client, reset_activities):
        """Test signing up and then unregistering from an activity."""
        activity = "Basketball Team"
        email = "newplayer@mergington.edu"
        
        # Verify not initially signed up
        assert email not in activities[activity]["participants"]
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert signup_response.status_code == 200
        assert email in activities[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert unregister_response.status_code == 200
        assert email not in activities[activity]["participants"]
    
    def test_participants_list_updated_correctly(self, client, reset_activities):
        """Test that participants list is updated accurately through signup/unregister."""
        activity = "Soccer Club"
        new_students = ["alice@mergington.edu", "bob@mergington.edu", "charlie@mergington.edu"]
        
        initial_count = len(activities[activity]["participants"])
        
        # Sign up all new students
        for email in new_students:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Check count increased
        assert len(activities[activity]["participants"]) == initial_count + len(new_students)
        
        # Unregister one student
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": new_students[0]}
        )
        assert response.status_code == 200
        
        # Check count decreased by 1
        assert len(activities[activity]["participants"]) == initial_count + len(new_students) - 1
        
        # Verify correct students are in the list
        activity_data = activities[activity]
        assert new_students[0] not in activity_data["participants"]
        assert new_students[1] in activity_data["participants"]
        assert new_students[2] in activity_data["participants"]
    
    def test_concurrent_signups_dont_interfere(self, client, reset_activities):
        """Test that multiple students signing up for different activities works correctly."""
        signups = [
            ("Drama Club", "student1@mergington.edu"),
            ("Science Club", "student2@mergington.edu"),
            ("Gym Class", "student3@mergington.edu"),
            ("Art Club", "student4@mergington.edu"),
        ]
        
        # Perform all signups
        for activity, email in signups:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify each signup worked
        for activity, email in signups:
            assert email in activities[activity]["participants"]
    
    def test_get_activities_reflects_changes(self, client, reset_activities):
        """Test that GET /activities reflects signup and unregister changes."""
        activity = "Debate Club"
        email = "prospect@mergington.edu"
        
        # Get initial state
        response1 = client.get("/activities")
        initial_participant_count = len(response1.json()[activity]["participants"])
        
        # Sign up
        client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Get updated state
        response2 = client.get("/activities")
        updated_participant_count = len(response2.json()[activity]["participants"])
        assert updated_participant_count == initial_participant_count + 1
        assert email in response2.json()[activity]["participants"]
        
        # Unregister
        client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        
        # Get final state
        response3 = client.get("/activities")
        final_participant_count = len(response3.json()[activity]["participants"])
        assert final_participant_count == initial_participant_count
        assert email not in response3.json()[activity]["participants"]
