from flask import jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import Event, Organizer, EventAttendee
from datetime import datetime
from . import api

# This module handles the API endpoints for managing events.
@api.route('/events', methods=['GET'])
def get_events():
    query = request.args.get('q', '')
    tag = request.args.get('tag', '')
    event_type = request.args.get('type', '')
    location = request.args.get('location', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    events = Event.query.filter(Event.end_time >= datetime.utcnow(), 
                              Event.is_cancelled == False)
    
    if query:
        events = events.filter(Event.title.contains(query) | Event.description.contains(query))
    if tag:
        events = events.filter(Event.tags.contains(tag))
    if event_type:
        events = events.filter_by(event_type=event_type)
    if location:
        events = events.filter(Event.location.contains(location))
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            events = events.filter(Event.start_time >= start_date)
        except ValueError:
            pass
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            events = events.filter(Event.start_time <= end_date)
        except ValueError:
            pass
    
    events = events.order_by(Event.start_time).all()
    return jsonify([event.to_dict() for event in events])

# This endpoint retrieves a specific event by its ID.
@api.route('/events/<int:id>', methods=['GET'])
def get_event(id):
    event = Event.query.get_or_404(id)
    return jsonify(event.to_dict())

# This endpoint retrieves all events organized by a specific organizer.
@api.route('/events', methods=['POST'])
@login_required
def create_event():
    if not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json() or {}
    if 'title' not in data or 'description' not in data or 'start_time' not in data or 'end_time' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    
    event = Event(
        title=data['title'],
        description=data['description'],
        event_type=data.get('event_type', 'conference'),
        tags=data.get('tags', ''),
        start_time=datetime.fromisoformat(data['start_time']),
        end_time=datetime.fromisoformat(data['end_time']),
        location=data.get('location', ''),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        image_url=data.get('image_url'),
        organizer_id=current_user.organizer_id
    )
    db.session.add(event)
    db.session.commit()
    return jsonify(event.to_dict()), 201

# This endpoint updates an existing event.
@api.route('/events/<int:id>', methods=['PUT'])
@login_required
def update_event(id):
    event = Event.query.get_or_404(id)
    if not current_user.is_manager or event.organizer_id != current_user.organizer_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json() or {}
    if 'title' in data:
        event.title = data['title']
    if 'description' in data:
        event.description = data['description']
    if 'event_type' in data:
        event.event_type = data['event_type']
    if 'tags' in data:
        event.tags = data['tags']
    if 'start_time' in data:
        event.start_time = datetime.fromisoformat(data['start_time'])
    if 'end_time' in data:
        event.end_time = datetime.fromisoformat(data['end_time'])
    if 'location' in data:
        event.location = data['location']
    if 'latitude' in data:
        event.latitude = data['latitude']
    if 'longitude' in data:
        event.longitude = data['longitude']
    if 'image_url' in data:
        event.image_url = data['image_url']
    
    db.session.commit()
    return jsonify(event.to_dict())

# This endpoint deletes an event.
@api.route('/events/<int:id>', methods=['DELETE'])
@login_required
def delete_event(id):
    event = Event.query.get_or_404(id)
    if not current_user.is_manager or event.organizer_id != current_user.organizer_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    event.is_cancelled = True
    db.session.commit()
    return jsonify({'result': 'Event cancelled'})

# This endpoint allows users to sign up for an event.
@api.route('/events/<int:id>/attend', methods=['POST'])
@login_required
def attend_event(id):
    event = Event.query.get_or_404(id)
    if event.is_past() or event.is_cancelled:
        return jsonify({'error': 'Cannot sign up for this event'}), 400
    
    if EventAttendee.query.filter_by(event_id=event.id, user_id=current_user.id).first():
        return jsonify({'error': 'Already signed up for this event'}), 400
    
    attendance = EventAttendee(event_id=event.id, user_id=current_user.id)
    db.session.add(attendance)
    db.session.commit()
    return jsonify({'result': 'Successfully signed up'})

# This endpoint allows users to cancel their attendance for an event.
@api.route('/events/<int:id>/cancel_attendance', methods=['POST'])
@login_required
def cancel_attendance(id):
    event = Event.query.get_or_404(id)
    if event.is_past() or event.is_cancelled:
        return jsonify({'error': 'Cannot cancel attendance for this event'}), 400
    
    attendance = EventAttendee.query.filter_by(event_id=event.id, user_id=current_user.id).first()
    if not attendance:
        return jsonify({'error': 'Not signed up for this event'}), 400
    
    db.session.delete(attendance)
    db.session.commit()
    return jsonify({'result': 'Attendance cancelled'})

# This endpoint allows managers to upload a batch of events from a CSV file.
@api.route('/events/batch', methods=['POST'])
@login_required
def batch_events():
    if not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'File must be a CSV'}), 400
    
    try:
        import csv
        from io import StringIO
        
        stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        events = []
        for row in csv_reader:
            event = Event(
                title=row['title'],
                description=row['description'],
                event_type=row.get('event_type', 'conference'),
                tags=row.get('tags', ''),
                start_time=datetime.strptime(row['start_time'], '%Y-%m-%d %H:%M:%S'),
                end_time=datetime.strptime(row['end_time'], '%Y-%m-%d %H:%M:%S'),
                location=row.get('location', ''),
                latitude=float(row['latitude']) if row.get('latitude') else None,
                longitude=float(row['longitude']) if row.get('longitude') else None,
                image_url=row.get('image_url'),
                organizer_id=current_user.organizer_id
            )
            db.session.add(event)
            events.append(event)
        
        db.session.commit()
        return jsonify([event.to_dict() for event in events]), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400