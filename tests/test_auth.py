import pytest
from app import db
from app.models import User

def test_register(client, test_app):
    response = client.post("/register", data={
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass",
        "confirm": "testpass"
    }, follow_redirects=True)

    assert b"Login" in response.data

def test_login_logout(client, test_app):
    # Create user
    user = User(username="loginuser", email="login@example.com")
    user.set_password("testpass")
    db.session.add(user)
    db.session.commit()

    # Login
    login = client.post("/login", data={
        "username": "loginuser",
        "password": "testpass"
    }, follow_redirects=True)
    assert b"Logout" in login.data

    # Logout
    logout = client.get("/logout", follow_redirects=True)
    assert b"Login" in logout.data