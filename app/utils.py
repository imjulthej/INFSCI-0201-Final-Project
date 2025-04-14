from datetime import datetime, timedelta
from flask import url_for, current_app
from flask_mail import Message
from app.extensions import mail, db
from app.models import Event, Subscription

def export_to_calendar(event, service='google'):
    if service == 'google':
        start = event.start_time.strftime('%Y%m%dT%H%M%SZ')
        end = event.end_time.strftime('%Y%m%dT%H%M%SZ')
        return (f'https://www.google.com/calendar/render?action=TEMPLATE'
                f'&text={event.title}&dates={start}/{end}'
                f'&details={event.description}&location={event.location}')
    elif service == 'outlook':
        start = event.start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        end = event.end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        return (f'https://outlook.live.com/calendar/0/deeplink/compose?'
                f'path=/calendar/action/compose&rru=addevent'
                f'&subject={event.title}&startdt={start}&enddt={end}'
                f'&body={event.description}&location={event.location}')
    elif service == 'apple':
        return url_for('download_ical', event_id=event.id)
    return '#'

def generate_ical(event):
    ical = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "PRODID:-//JJK Presents Events//EN\n"
        "BEGIN:VEVENT\n"
        f"UID:{event.id}@jjkpresents.com\n"
        f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}\n"
        f"DTSTART:{event.start_time.strftime('%Y%m%dT%H%M%SZ')}\n"
        f"DTEND:{event.end_time.strftime('%Y%m%dT%H%M%SZ')}\n"
        f"SUMMARY:{event.title}\n"
        f"DESCRIPTION:{event.description}\n"
        f"LOCATION:{event.location}\n"
        "END:VEVENT\n"
        "END:VCALENDAR"
    )
    return ical

def get_upcoming_events(user=None, limit=5):
    query = Event.query.filter(
        Event.end_time >= datetime.utcnow(),
        Event.is_cancelled == False
    ).order_by(Event.start_time)
    
    if user:
        subscribed_organizers = [sub.organizer_id for sub in user.subscriptions.filter(
            Subscription.organizer_id.isnot(None)).all()]
        subscribed_tags = [sub.tag for sub in user.subscriptions.filter(
            Subscription.tag.isnot(None)).all()]
        
        if subscribed_organizers or subscribed_tags:
            query = query.filter(
                (Event.organizer_id.in_(subscribed_organizers)) | 
                (Event.tags.contains('|'.join(subscribed_tags))))
    
    return query.limit(limit).all()

def send_email(subject, recipients, body, html=None):
    msg = Message(subject, sender=current_app.config['MAIL_USERNAME'], recipients=recipients)
    msg.body = body
    if html:
        msg.html = html
    mail.send(msg)

def send_event_reminders():
    now = datetime.utcnow()
    tomorrow_start = now + timedelta(days=1)
    tomorrow_end = tomorrow_start + timedelta(hours=24)

    events = Event.query.filter(
        Event.start_time >= tomorrow_start,
        Event.start_time <= tomorrow_end,
        Event.is_cancelled == False
    ).all()

    for event in events:
        for attendee in event.attendees:
            subject = f"Reminder: '{event.title}' is happening tomorrow!"
            body = (
                f"Hi {attendee.username},\n\n"
                f"This is a reminder that you're attending '{event.title}' tomorrow.\n\n"
                f"🗓 Date & Time: {event.start_time.strftime('%A, %B %d at %I:%M %p')}\n"
                f"📍 Location: {event.location}\n\n"
                f"See you there!\n"
            )
            send_email(subject, [attendee.email], body)