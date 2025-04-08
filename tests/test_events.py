import pytest
from app import db
from app.models import User, Event
from datetime import datetime, timedelta, timezone

def create_manager():
    manager = User(username="manager1", email="manager@example.com", is_manager=True)
    manager.set_password("managerpass")
    return manager

def create_event(manager):
    return Event(
        title="Test Event",
        description="Test description",
        event_type="Workshop",
        start_time=datetime.now(timezone.utc) + timedelta(days=1),
        end_time=datetime.now(timezone.utc) + timedelta(days=1, hours=2),
        location="Test Hall",
        organizer_id=manager.organizer_id,
        creator_id=manager.id,
        tags="test,tag"
    )

def test_event_creation_and_joining(client, test_app):
    # Create and add manager
    manager = create_manager()
    db.session.add(manager)
    db.session.commit()

    # Login as manager
    client.post("/login", data={"username": "manager1", "password": "managerpass"}, follow_redirects=True)

    # Simulate event creation
    event = create_event(manager)
    db.session.add(event)
    db.session.commit()

    # Create regular user
    user = User(username="user1", email="user1@example.com")
    user.set_password("userpass")
    db.session.add(user)
    db.session.commit()

    # Login as regular user
    client.get("/logout", follow_redirects=True)
    client.post("/login", data={"username": "user1", "password": "userpass"}, follow_redirects=True)

    # Join the event
    response = client.post(f"/events/{event.id}/attend", follow_redirects=True)
    assert b"successfully signed up" in response.data
    assert user in event.attendees