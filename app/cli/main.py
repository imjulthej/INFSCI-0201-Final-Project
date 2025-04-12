import click
from flask import current_app
from flask.cli import with_appcontext
from app import create_app, db
from app.models import User, Event, Organizer
from datetime import datetime
import csv

app = create_app()

@app.cli.command('init-db')
@with_appcontext
def init_db():
    db.create_all()
    click.echo('Initialized the database.')

@app.cli.command('create-admin')
@click.argument('username')
@click.argument('email')
@click.argument('password')
@with_appcontext
def create_admin(username, email, password):
    organizer = Organizer(name='JJK Presents', description='Main organizer for JJK Presents Events')
    db.session.add(organizer)
    db.session.commit()
    
    user = User(username=username, email=email, is_manager=True, organizer_id=organizer.id)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f'Created admin user {username}.')

@app.cli.command('import-events')
@click.argument('filename')
@with_appcontext
def import_events(filename):
    organizer = Organizer.query.filter_by(name='JJK Presents').first()
    if not organizer:
        click.echo('Organizer not found. Please create an organizer first.')
        return
    
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
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
                organizer_id=organizer.id
            )
            db.session.add(event)
        
        db.session.commit()
        click.echo(f'Imported {reader.line_num - 1} events.')

@app.cli.command('export-events')
@click.argument('filename')
@with_appcontext
def export_events(filename):
    events = Event.query.all()
    if not events:
        click.echo('No events found.')
        return
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['title', 'description', 'event_type', 'tags', 'start_time', 'end_time', 
                        'location', 'latitude', 'longitude', 'image_url', 'organizer_id'])
        
        for event in events:
            writer.writerow([
                event.title,
                event.description,
                event.event_type,
                event.tags,
                event.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                event.end_time.strftime('%Y-%m-%d %H:%M:%S'),
                event.location,
                event.latitude,
                event.longitude,
                event.image_url,
                event.organizer_id
            ])
        
        click.echo(f'Exported {len(events)} events to {filename}.')

if __name__ == '__main__':
    app.cli()