from flask import jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import User, Event, EventAttendee, Subscription, Organizer
from datetime import datetime
from . import api

# This module handles user-related API endpoints, including user creation, fetching user details, and managing subscriptions to organizers and tags.
@api.route('/users', methods=['POST'])
def create_user():
    data = request.get_json() or {}
    if 'username' not in data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    user = User(username=data['username'], email=data['email'])
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201

# This endpoint retrieves a user's details by their ID.
@api.route('/users/<int:id>', methods=['GET'])
@login_required
def get_user(id):
    if current_user.id != id and not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    user = User.query.get_or_404(id)
    return jsonify(user.to_dict())

# The following three endpoints work in conjunction to retrieve a list of events that a user is attending.
@api.route('/users/me', methods=['GET'])
@login_required
def get_current_user():
    return jsonify(current_user.to_dict())

@api.route('/users/me/events', methods=['GET'])
@login_required
def get_user_events():
    upcoming_events = current_user.events.filter(Event.end_time >= datetime.utcnow()).all()
    past_events = current_user.events.filter(Event.end_time < datetime.utcnow()).all()
    
    return jsonify({
        'upcoming_events': [event.to_dict() for event in upcoming_events],
        'past_events': [event.to_dict() for event in past_events]
    })

@api.route('/users/me/subscriptions', methods=['GET'])
@login_required
def get_user_subscriptions():
    subscribed_organizers = [sub.organizer_id for sub in current_user.subscriptions.filter(
        Subscription.organizer_id.isnot(None)).all()]
    subscribed_tags = [sub.tag for sub in current_user.subscriptions.filter(
        Subscription.tag.isnot(None)).all()]
    
    recommended_events = Event.query.filter(
        (Event.organizer_id.in_(subscribed_organizers)) | 
        (Event.tags.contains('|'.join(subscribed_tags)))).filter(
        Event.end_time >= datetime.utcnow()).order_by(Event.start_time).all()
    
    return jsonify({
        'subscribed_organizers': subscribed_organizers,
        'subscribed_tags': subscribed_tags,
        'recommended_events': [event.to_dict() for event in recommended_events]
    })

# This endpoint allows users to subscribe to an organizer.
@api.route('/users/me/subscriptions/organizer/<int:organizer_id>', methods=['POST'])
@login_required
def subscribe_organizer(organizer_id):
    organizer = Organizer.query.get_or_404(organizer_id)
    if Subscription.query.filter_by(user_id=current_user.id, organizer_id=organizer.id).first():
        return jsonify({'error': 'Already subscribed to this organizer'}), 400
    
    subscription = Subscription(user_id=current_user.id, organizer_id=organizer.id)
    db.session.add(subscription)
    db.session.commit()
    return jsonify({'result': 'Subscribed successfully'})

# This endpoint allows users to subscribe to a tag.
@api.route('/users/me/subscriptions/tag/<tag>', methods=['POST'])
@login_required
def subscribe_tag(tag):
    if Subscription.query.filter_by(user_id=current_user.id, tag=tag).first():
        return jsonify({'error': 'Already subscribed to this tag'}), 400
    
    subscription = Subscription(user_id=current_user.id, tag=tag)
    db.session.add(subscription)
    db.session.commit()
    return jsonify({'result': 'Subscribed successfully'})

# This endpoint allows users to unsubscribe from an organizer.
@api.route('/users/me/subscriptions/organizer/<int:organizer_id>', methods=['DELETE'])
@login_required
def unsubscribe_organizer(organizer_id):
    subscription = Subscription.query.filter_by(
        user_id=current_user.id, organizer_id=organizer_id).first()
    if not subscription:
        return jsonify({'error': 'Not subscribed to this organizer'}), 400
    
    db.session.delete(subscription)
    db.session.commit()
    return jsonify({'result': 'Unsubscribed successfully'})

# This endpoint allows users to unsubscribe from a tag.
@api.route('/users/me/subscriptions/tag/<tag>', methods=['DELETE'])
@login_required
def unsubscribe_tag(tag):
    subscription = Subscription.query.filter_by(user_id=current_user.id, tag=tag).first()
    if not subscription:
        return jsonify({'error': 'Not subscribed to this tag'}), 400
    
    db.session.delete(subscription)
    db.session.commit()
    return jsonify({'result': 'Unsubscribed successfully'})