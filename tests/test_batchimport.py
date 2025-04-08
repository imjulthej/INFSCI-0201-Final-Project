import io
import pytest
from app import db
from app.models import User, Event

@pytest.fixture
def manager_user():
    user = User(username="manager", email="manager@example.com", is_manager=True)
    user.set_password("testpass")
    db.session.add(user)
    db.session.commit()
    return user

def test_batch_import_success(client, test_app, manager_user):
    # Login as manager
    client.post("/login", data={
        "username": "manager",
        "password": "testpass"
    }, follow_redirects=True)

    # Sample CSV content
    csv_data = """title,description,event_type,start_time,end_time,location
Test Event 1,Desc 1,Workshop,2025-04-10 10:00:00,2025-04-10 12:00:00,Room A
Test Event 2,Desc 2,Conference,2025-04-11 14:00:00,2025-04-11 16:00:00,Room B
"""

    data = {
        "csv_file": (io.BytesIO(csv_data.encode("utf-8")), "events.csv")
    }

    response = client.post("/manager/batch", data=data, content_type="multipart/form-data", follow_redirects=True)

    assert b"Events have been imported successfully" in response.data
    assert Event.query.count() == 2

def test_batch_import_missing_fields(client, test_app, manager_user):
    client.post("/login", data={
        "username": "manager",
        "password": "testpass"
    }, follow_redirects=True)

    # CSV missing 'title' column
    bad_csv_data = """description,event_type,start_time,end_time,location
Bad data row,Workshop,2025-04-10 10:00:00,2025-04-10 12:00:00,Room X
"""

    data = {
        "csv_file": (io.BytesIO(bad_csv_data.encode("utf-8")), "bad.csv")
    }

    response = client.post("/manager/batch", data=data, content_type="multipart/form-data", follow_redirects=True)

    assert b"CSV is missing required fields" in response.data
    assert Event.query.count() == 0