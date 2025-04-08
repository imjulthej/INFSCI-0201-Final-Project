from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app, Response
from flask_login import current_user, login_user, logout_user, login_required
from app import db
from app.models import User, Event, Organizer, EventAttendee, Subscription
from app.forms import LoginForm, RegistrationForm, EventForm, SettingsForm, BatchEventForm, UpdateAccountForm
from app.utils import send_email
from datetime import datetime, timezone
from icalendar import Calendar, Event as ICalEvent
import csv
from io import StringIO
import math
import requests

routes = Blueprint('main', __name__)

# Route for the home page
@routes.route('/')
def index():
    events = Event.query.filter(Event.end_time >= datetime.utcnow(), 
                                 Event.is_cancelled == False).order_by(Event.start_time).all()
    return render_template('index.html', events=events)

# Route for the login page
@routes.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('main.login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('main.index'))
    return render_template('auth/login.html', form=form)

# Route for the registration page
@routes.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('main.login'))
    return render_template('auth/register.html', form=form)

# Route to logout the user
@routes.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

# Route for the event details
@routes.route('/events/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    is_attending = False
    if current_user.is_authenticated:
        is_attending = event in current_user.events_attending

    google_maps_key = current_app.config.get('GOOGLE_MAPS_API_KEY')

    return render_template(
        'events/detail.html',
        event=event,
        is_attending=is_attending,
        google_maps_key=google_maps_key
    )

# Route for the event search page
@routes.route("/search")
def search_events():
    query = request.args.get("q", "")
    event_type = request.args.get("type", "")
    start_date_str = request.args.get("start_date", "")
    end_date_str = request.args.get("end_date", "")
    location = request.args.get("location", "")
    radius = request.args.get("radius", "")
    page = request.args.get("page", 1, type=int)
    tag_filter = request.args.get("tag", "")
    per_page = current_app.config.get("EVENTS_PER_PAGE", 10)

    results = Event.query
    center_coords = None
    use_radius_filter = False
    filtered_events = []

    if query:
        results = results.filter(
            (Event.title.ilike(f"%{query}%")) |
            (Event.description.ilike(f"%{query}%"))
        )

    if event_type:
        results = results.filter(Event.event_type.ilike(event_type))

    if tag_filter:
        results = results.filter(Event.tags.ilike(f"%{tag_filter}%"))

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            results = results.filter(Event.start_time >= start_date)
        except ValueError:
            flash("Invalid start date format.", "warning")

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            results = results.filter(Event.start_time <= end_date)
        except ValueError:
            flash("Invalid end date format.", "warning")

    if location and radius:
        geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": location,
            "key": current_app.config.get("GOOGLE_MAPS_API_KEY")
        }
        response = requests.get(geocode_url, params=params)
        data = response.json()

        if data["status"] == "OK":
            lat_lng = data["results"][0]["geometry"]["location"]
            center_coords = (lat_lng["lat"], lat_lng["lng"])
            radius_miles = float(radius)

            def haversine(lat1, lon1, lat2, lon2):
                from math import radians, sin, cos, sqrt, asin
                R = 3958.8
                dlat = radians(lat2 - lat1)
                dlon = radians(lon2 - lon1)
                a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
                return 2 * R * asin(sqrt(a))

            all_results = results.all()
            filtered_events = [
                e for e in all_results
                if e.latitude and e.longitude and
                haversine(center_coords[0], center_coords[1], e.latitude, e.longitude) <= radius_miles
            ]
            use_radius_filter = True
        else:
            flash("Could not geocode the location.", "warning")
            filtered_events = results.all()
            use_radius_filter = True
    else:
        results = results.order_by(Event.start_time.asc())
        pagination = results.paginate(page=page, per_page=per_page, error_out=False)
        filtered_events = pagination.items

    if use_radius_filter:
        total = len(filtered_events)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_events = filtered_events[start:end]

        class ManualPagination:
            def __init__(self, page, per_page, total):
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = (total + per_page - 1) // per_page
                self.has_prev = page > 1
                self.has_next = page < self.pages
                self.prev_num = page - 1
                self.next_num = page + 1

            def iter_pages(self, left_edge=2, right_edge=2, left_current=2, right_current=2):
                last = 0
                for num in range(1, self.pages + 1):
                    if num <= left_edge or \
                       (num >= self.page - left_current and num <= self.page + right_current) or \
                       num > self.pages - right_edge:
                        if last + 1 != num:
                            yield None
                        yield num
                        last = num

        pagination = ManualPagination(page, per_page, total)
        events = paginated_events
    else:
        events = filtered_events

    return render_template(
        "events/search.html",
        events=events,
        pagination=pagination,
        query=query,
        selected_type=event_type,
        start_date=start_date_str,
        end_date=end_date_str,
        location=location,
        radius=radius,
        tag_filter=tag_filter
    )

# Route for the user profile page
@routes.route('/profile')
@login_required
def profile():
    upcoming_events = Event.query.join(EventAttendee).filter(
        EventAttendee.user_id == current_user.id,
        Event.end_time >= datetime.utcnow()
    ).all()

    past_events = Event.query.join(EventAttendee).filter(
        EventAttendee.user_id == current_user.id,
        Event.end_time < datetime.utcnow()
    ).all()


    subscribed_organizers = [sub.organizer_id for sub in current_user.subscriptions.filter(Subscription.organizer_id.isnot(None)).all()]
    subscribed_tags = [sub.tag for sub in current_user.subscriptions.filter(Subscription.tag.isnot(None)).all()]

    recommended_events = Event.query.filter(
        (Event.organizer_id.in_(subscribed_organizers)) | 
        (Event.tags.contains('|'.join(subscribed_tags)))
    ).filter(Event.end_time >= datetime.utcnow()).order_by(Event.start_time).all()

    return render_template('users/profile.html', 
                           upcoming_events=upcoming_events,
                           past_events=past_events,
                           recommended_events=recommended_events)

# Route for the manager dashboard
@routes.route('/manager/dashboard')
@login_required
def manager_dashboard():
    if not current_user.is_manager:
        return redirect(url_for('main.index'))

    current_events = Event.query.filter_by(organizer_id=current_user.organizer_id, is_cancelled=False).filter(Event.end_time >= datetime.utcnow()).all()
    past_events = Event.query.filter_by(organizer_id=current_user.organizer_id).filter(Event.end_time < datetime.utcnow()).all()
    cancelled_events = Event.query.filter_by(organizer_id=current_user.organizer_id, is_cancelled=True).all()

    return render_template('managers/dashboard.html',
                           current_events=current_events,
                           past_events=past_events,
                           cancelled_events=cancelled_events)

# Route for the event creation page
@routes.route('/manager/events/create', methods=['GET', 'POST'])
@login_required
def create_event():
    if not current_user.is_manager:
        return redirect(url_for('main.index'))

    form = EventForm()
    if form.validate_on_submit():
        event = Event(
            title=form.title.data,
            description=form.description.data,
            event_type=form.event_type.data,
            tags=form.tags.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            location=form.location.data,
            latitude=form.latitude.data,
            longitude=form.longitude.data,
            image_url=form.image_url.data,
            organizer_id=current_user.organizer_id
        )
        db.session.add(event)
        db.session.commit()
        flash('Your event has been created!', 'success')
        return redirect(url_for('main.event_detail', event_id=event.id))
    return render_template(
        'events/create.html',
        form=form,
        google_maps_key=current_app.config['GOOGLE_MAPS_API_KEY']
    )
# Route to edit events after making them
@routes.route('/manager/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    if not current_user.is_manager:
        return redirect(url_for('main.index'))

    event = Event.query.get_or_404(event_id)
    if event.organizer_id != current_user.organizer_id:
        return redirect(url_for('main.index'))

    form = EventForm()
    if form.validate_on_submit():
        event.title = form.title.data
        event.description = form.description.data
        event.event_type = form.event_type.data
        event.tags = form.tags.data
        event.start_time = form.start_time.data
        event.end_time = form.end_time.data
        event.location = form.location.data
        event.latitude = form.latitude.data
        event.longitude = form.longitude.data
        event.image_url = form.image_url.data
        db.session.commit()
        flash('Your changes have been saved.', 'success')
        return redirect(url_for('main.event_detail', event_id=event.id))
    elif request.method == 'GET':
        form.title.data = event.title
        form.description.data = event.description
        form.event_type.data = event.event_type
        form.tags.data = event.tags
        form.start_time.data = event.start_time
        form.end_time.data = event.end_time
        form.location.data = event.location
        form.latitude.data = event.latitude
        form.longitude.data = event.longitude
        form.image_url.data = event.image_url
    return render_template(
    'events/edit.html',
    form=form,
    event=event,
    google_maps_key=current_app.config['GOOGLE_MAPS_API_KEY']
)

# Route for batch event creation from a CSV
@routes.route('/manager/batch', methods=['GET', 'POST'])
@login_required
def batch_events():
    if not current_user.is_manager:
        return redirect(url_for('main.index'))

    form = BatchEventForm()
    if form.validate_on_submit():
        csv_file = form.csv_file.data
        stream = StringIO(csv_file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)

        required_fields = ['title', 'description', 'event_type', 'start_time', 'end_time', 'location']
        missing_fields = [field for field in required_fields if field not in csv_reader.fieldnames]

        if missing_fields:
            flash(f"CSV is missing required fields: {', '.join(missing_fields)}", "danger")
            return redirect(url_for('main.manager_dashboard'))

        for idx, row in enumerate(csv_reader, start=1):
            if not all(row.get(field) for field in required_fields):
                flash(f"Row {idx} is missing required fields and was skipped.", "warning")
                continue

            try:
                event = Event(
                    title=row['title'],
                    description=row['description'],
                    event_type=row['event_type'],
                    tags=row.get('tags', ''),
                    start_time=datetime.strptime(row['start_time'], '%Y-%m-%d %H:%M:%S'),
                    end_time=datetime.strptime(row['end_time'], '%Y-%m-%d %H:%M:%S'),
                    location=row['location'],
                    latitude=float(row['latitude']) if row.get('latitude') else None,
                    longitude=float(row['longitude']) if row.get('longitude') else None,
                    image_url=row.get('image_url', ''),
                    organizer_id=current_user.organizer_id
                )
                db.session.add(event)

            except Exception as e:
                flash(f"Row {idx} failed to import: {e}", "danger")
                continue

        db.session.commit()
        flash('Events have been imported successfully!', 'success')
        return redirect(url_for('main.manager_dashboard'))

    return render_template('managers/batch.html', form=form)

# Route for event attendance by users
@routes.route('/events/<int:event_id>/attend', methods=['POST'])
@login_required
def attend_event(event_id):
    event = Event.query.get_or_404(event_id)
    if current_user not in event.attendees:
        event.attendees.append(current_user)
        db.session.commit()

        subject = f"Confirmation: You've joined '{event.title}'"
        body = (
            f"Hi {current_user.username},\n\n"
            f"You've successfully joined the event: {event.title}.\n\n"
            f"When: {event.start_time.strftime('%A, %B %d, %Y at %I:%M %p')}\n"
            f"Where: {event.location}\n\n"
            "Thank you!"
        )
        send_email(subject, [current_user.email], body)

        flash("You have successfully signed up for the event!", "success")
    else:
        flash("You're already signed up for this event.", "info")
    return redirect(url_for('main.event_detail', event_id=event.id))

# Route for cancelling attendance
@routes.route('/events/<int:event_id>/cancel', methods=['POST'])
@login_required
def cancel_attendance(event_id):
    event = Event.query.get_or_404(event_id)
    if current_user in event.attendees:
        event.attendees.remove(current_user)
        db.session.commit()
        flash("You have been removed from the event.", "success")
    else:
        flash("You were not signed up for this event.", "info")
    return redirect(url_for('main.event_detail', event_id=event.id))

# Route for completely deleting an event
@routes.route('/manager/events/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    if not current_user.is_manager:
        flash("Access denied.", "danger")
        return redirect(url_for('main.index'))

    event = Event.query.get_or_404(event_id)

    if event.organizer_id != current_user.organizer_id:
        flash("You do not have permission to delete this event.", "danger")
        return redirect(url_for('main.manager_dashboard'))

    db.session.delete(event)
    db.session.commit()
    flash("Event has been permanently deleted.", "success")
    return redirect(url_for('main.manager_dashboard'))

# Route for exporting events to CSV
@routes.route('/manager/analytics/export')
@login_required
def export_events_csv():
    if not current_user.is_manager:
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    query = Event.query.filter_by(organizer_id=current_user.organizer_id)

    if start_date_str:
        start = datetime.strptime(start_date_str, "%Y-%m-%d")
        query = query.filter(Event.start_time >= start)

    if end_date_str:
        end = datetime.strptime(end_date_str, "%Y-%m-%d")
        end = end.replace(hour=23, minute=59, second=59)
        query = query.filter(Event.start_time <= end)

    events = query.all()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["Title", "Type", "Start Time", "End Time", "Location", "Attendees"])

    for event in events:
        writer.writerow([
            event.title,
            event.event_type,
            event.start_time.strftime("%Y-%m-%d %H:%M"),
            event.end_time.strftime("%Y-%m-%d %H:%M"),
            event.location,
            len(event.attendees)
        ])

    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=events.csv"}
    )

# Route for exporting event attendees to CSV
@routes.route('/manager/events/<int:event_id>/attendees/export')
@login_required
def export_attendees_csv(event_id):
    if not current_user.is_manager:
        flash("Access denied.", "danger")
        return redirect(url_for('main.index'))

    event = Event.query.get_or_404(event_id)

    if event.organizer_id != current_user.organizer_id:
        flash("You do not have permission to export this event's attendees.", "danger")
        return redirect(url_for('main.manager_dashboard'))

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Username', 'Email'])

    for attendee in event.attendees:
        writer.writerow([attendee.username, attendee.email])

    output = Response(si.getvalue(), mimetype='text/csv')
    output.headers['Content-Disposition'] = f'attachment; filename=event_{event.id}_attendees.csv'
    return output

# Route for user settings page
@routes.route("/settings", methods=["GET", "POST"])
@login_required
def user_settings():
    form = UpdateAccountForm()

    if request.method == "GET":
        form.username.data = current_user.username
        form.email.data = current_user.email

    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data

        if form.password.data:
            current_user.set_password(form.password.data)

        db.session.commit()
        flash("Your account has been updated.", "success")
        return redirect(url_for("main.user_settings"))

    return render_template("users/settings.html", form=form)

# Route for deleting user account
@routes.route("/delete-account", methods=["POST"])
@login_required
def delete_account():
    user = current_user
    db.session.delete(user)
    db.session.commit()
    flash("Your account has been deleted.", "success")
    return redirect(url_for("main.index"))

# Route for downloading calendar event
@routes.route("/events/<int:event_id>/calendar")
@login_required
def download_calendar_event(event_id):
    event = Event.query.get_or_404(event_id)

    cal = Calendar()
    ical_event = ICalEvent()
    ical_event.add('summary', event.title)
    ical_event.add('dtstart', event.start_time.replace(tzinfo=timezone.utc))
    ical_event.add('dtend', event.end_time.replace(tzinfo=timezone.utc))
    ical_event.add('location', event.location)
    ical_event.add('description', event.description)

    cal.add_component(ical_event)

    response = Response(cal.to_ical(), mimetype='text/calendar')
    response.headers.set('Content-Disposition', 'attachment', filename=f"{event.title}.ics")
    return response

# Route for managers to manage users
@routes.route('/manager/users')
@login_required
def manage_users():
    if not current_user.is_manager:
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    page = request.args.get('page', 1, type=int)
    per_page = 10
    search = request.args.get('q', '')

    query = User.query.order_by(User.username)
    if search:
        query = query.filter(User.username.ilike(f"%{search}%"))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items
    all_organizers = Organizer.query.order_by(Organizer.name).all()

    return render_template(
        'managers/users.html',
        users=users,
        pagination=pagination,
        search=search,
        all_organizers=all_organizers
    )

# Route to toggle manager status of a user
@routes.route('/manager/users/<int:user_id>/toggle-manager', methods=['POST'])
@login_required
def toggle_manager_status(user_id):
    if not current_user.is_manager:
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    user = User.query.get_or_404(user_id)
    if user == current_user:
        flash("You can't change your own role.", "warning")
        return redirect(url_for("main.manage_users"))

    user.is_manager = not user.is_manager
    db.session.commit()
    flash(f"{'Promoted' if user.is_manager else 'Demoted'} {user.username}.", "success")
    return redirect(url_for("main.manage_users"))

# Route for managers to delete a user account
@routes.route('/manager/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user_account(user_id):
    if not current_user.is_manager:
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    user = User.query.get_or_404(user_id)
    if user == current_user:
        flash("You can't delete your own account here.", "warning")
        return redirect(url_for("main.manage_users"))

    db.session.delete(user)
    db.session.commit()
    flash(f"Deleted {user.username}.", "success")
    return redirect(url_for("main.manage_users"))

# Route for managers to assign an organizer to a user
@routes.route('/manager/users/<int:user_id>/assign-organizer', methods=['POST'])
@login_required
def assign_organizer(user_id):
    if not current_user.is_manager:
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    user = User.query.get_or_404(user_id)
    organizer_id = request.form.get("organizer_id")

    if organizer_id:
        organizer = Organizer.query.get(organizer_id)
        if organizer:
            user.organizer_id = organizer.id
            flash(f"{user.username} assigned to organizer '{organizer.name}'.", "success")
        else:
            flash("Organizer not found.", "warning")
    else:
        user.organizer_id = None
        flash(f"{user.username} has been unassigned from an organizer.", "info")

    db.session.commit()
    return redirect(url_for("main.manage_users"))

# Route for managers to create a new organizer
@routes.route('/manager/organizers/create', methods=['GET', 'POST'])
@login_required
def create_organizer():
    if not current_user.is_manager:
        flash("Access denied.", "danger")
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')

        if not name:
            flash("Organizer name is required.", "warning")
            return redirect(url_for('main.create_organizer'))

        from app.models import Organizer
        from app import db

        organizer = Organizer(name=name, description=description)
        db.session.add(organizer)
        db.session.commit()
        flash(f"Organizer '{name}' created successfully!", "success")
        return redirect(url_for('main.manage_users'))

    return render_template('managers/create_organizer.html')

# Route for managers to manage organizers
@routes.route('/manager/organizers')
@login_required
def manage_organizers():
    if not current_user.is_manager:
        flash("Access denied.", "danger")
        return redirect(url_for('main.index'))

    sort = request.args.get('sort', 'name')
    search = request.args.get('q', '')

    query = Organizer.query

    if search:
        query = query.filter(Organizer.name.ilike(f"%{search}%"))

    if sort == 'name':
        query = query.order_by(Organizer.name.asc())
    elif sort == 'users':
        query = query.outerjoin(Organizer.users).group_by(Organizer.id).order_by(db.func.count().desc())
    elif sort == 'events':
        query = query.outerjoin(Organizer.events).group_by(Organizer.id).order_by(db.func.count().desc())

    organizers = query.all()

    return render_template("managers/organizers.html", organizers=organizers, sort=sort, search=search)

# Route for managers to edit an organizer
@routes.route('/manager/organizers/<int:organizer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_organizer(organizer_id):
    if not current_user.is_manager:
        flash("Access denied.", "danger")
        return redirect(url_for('main.index'))

    organizer = Organizer.query.get_or_404(organizer_id)

    if request.method == "POST":
        organizer.name = request.form.get("name")
        organizer.description = request.form.get("description")
        db.session.commit()
        flash("Organizer updated successfully.", "success")
        return redirect(url_for("main.manage_organizers"))

    return render_template("managers/edit_organizer.html", organizer=organizer)

# Route for managers to delete an organizer
@routes.route('/manager/organizers/<int:organizer_id>/delete', methods=['POST'])
@login_required
def delete_organizer(organizer_id):
    if not current_user.is_manager:
        flash("Access denied.", "danger")
        return redirect(url_for('main.index'))

    organizer = Organizer.query.get_or_404(organizer_id)

    if organizer.users.count() > 0 or organizer.events.count() > 0:
        flash("Cannot delete organizer with assigned users or events.", "warning")
        return redirect(url_for('main.manage_organizers'))

    db.session.delete(organizer)
    db.session.commit()
    flash(f"Organizer '{organizer.name}' deleted.", "success")
    return redirect(url_for('main.manage_organizers'))

# Route for managers to view users of an organizer
@routes.route('/manager/organizers/<int:organizer_id>/users')
@login_required
def view_organizer_users(organizer_id):
    if not current_user.is_manager:
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    organizer = Organizer.query.get_or_404(organizer_id)
    users = organizer.users.all()
    return render_template("managers/organizer_users.html", organizer=organizer, users=users)

# Route for managers to view events of an organizer
@routes.route('/manager/organizers/<int:organizer_id>/events')
@login_required
def view_organizer_events(organizer_id):
    if not current_user.is_manager:
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    organizer = Organizer.query.get_or_404(organizer_id)
    events = organizer.events.order_by(Event.start_time).all()
    return render_template("managers/organizer_events.html", organizer=organizer, events=events)

# Route for managers to view analytics
@routes.route('/manager/analytics')
@login_required
def manager_analytics():
    if not current_user.is_manager:
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    # Get filter values
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    from app.models import Event
    now = datetime.utcnow()

    query = Event.query.filter_by(organizer_id=current_user.organizer_id)

    if start_date_str:
        start = datetime.strptime(start_date_str, "%Y-%m-%d")
        query = query.filter(Event.start_time >= start)
    else:
        start = None

    if end_date_str:
        end = datetime.strptime(end_date_str, "%Y-%m-%d")
        end = end.replace(hour=23, minute=59, second=59)  # include entire end day
        query = query.filter(Event.start_time <= end)
    else:
        end = None

    events = query.all()

    total_events = len(events)
    upcoming_events = [e for e in events if e.start_time > now]
    past_events = [e for e in events if e.start_time <= now]
    total_attendees = sum(len(e.attendees) for e in events)

    from collections import Counter
    event_type_counts = Counter(e.event_type for e in events)

    return render_template(
        "managers/analytics.html",
        total_events=total_events,
        total_attendees=total_attendees,
        upcoming_count=len(upcoming_events),
        past_count=len(past_events),
        event_type_counts=event_type_counts,
        start_date=start_date_str,
        end_date=end_date_str
    )