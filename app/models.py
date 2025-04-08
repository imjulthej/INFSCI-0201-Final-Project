from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login

event_attendees = db.Table('event_attendees',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    is_manager = db.Column(db.Boolean, default=False)
    organizer_id = db.Column(db.Integer, db.ForeignKey('organizer.id'))
    
    created_events = db.relationship('Event', backref='creator', lazy='dynamic')

    events_attending = db.relationship(
        'Event',
        secondary=event_attendees,
        back_populates='attendees'
    )

    subscriptions = db.relationship('Subscription', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Organizer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), index=True, unique=True)
    description = db.Column(db.Text)
    events = db.relationship('Event', backref='organizer', lazy='dynamic')
    managers = db.relationship('User', backref='organizer_ref', lazy='dynamic')
    users = db.relationship("User", backref="organizer", lazy="dynamic")
    events = db.relationship("Event", backref="organizer", lazy="dynamic")

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), index=True)
    description = db.Column(db.Text)
    event_type = db.Column(db.String(50))
    tags = db.Column(db.String(200))
    start_time = db.Column(db.DateTime, index=True)
    end_time = db.Column(db.DateTime, index=True)
    location = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    image_url = db.Column(db.String(200))
    is_cancelled = db.Column(db.Boolean, default=False)

    organizer_id = db.Column(db.Integer, db.ForeignKey('organizer.id'))
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    attendees = db.relationship(
        'User',
        secondary=event_attendees,
        back_populates='events_attending'
    )

    def is_past(self):
        return self.end_time < datetime.utcnow()

class EventAttendee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    organizer_id = db.Column(db.Integer, db.ForeignKey('organizer.id'))
    tag = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))