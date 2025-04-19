from flask import jsonify, request
from flask_login import login_user, logout_user, login_required
from app.models import User
from . import api

# Login route for API
@api.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    if 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Missing username or password'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    if user is None or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    login_user(user)
    return jsonify({'result': 'Logged in successfully'})

# Logout route for API
@api.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'result': 'Logged out successfully'})