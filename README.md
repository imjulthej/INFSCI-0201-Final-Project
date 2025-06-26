# INFSCI 0201 Final Project: *JJK Presents Events*

## Introduction
*JJK Presents Events* is a web app built with Python that allows users to create, manage, search, and sign up for events. The system supports authentication, event categorization, a search function, user profiles, and management capabilities for event organizers.

## Key Features
### Base Functionality
1. User Authentication
    - Registration, login, logout with secure password hashing
2. Event Discovery
    - Keyword and tag-based search, filter by type/location/date
3. Event Details
    - Includes map location, calendar exportation, and tag-based suggestions
4. User Profiles
    - Displays upcoming and past events, recommendations based on subscriptions
5. Settings
    - Allows updating username and login info
6. Event Signup/Cancelling
    - Users can join or leave events with real-time attendee tracking
7. Dark Mode
    - Persistent theme toggle with icon animation
8. Mobile Optimization
    - Fully responsive for phones and tablets
### Manager/Admin Features
1. Event Management Dashboard
    - Create, edit, cancel events
2. CSV Import and Export
    - Batch event creation and attendee exports
3. User Management Panel
    - Promote/demote users, assign organizers
4. Analytics Page
    - View attendee stats, event breakdowns, and export to CSV
5. Organizer Tools
    - Create and edit organizers, assign users

## System Architecture
The system follows an MVC architecture based around files for SQLAlchemy models for users, events, and organizers, view functions and page logic, WTForms definitions, and Jinja2 templates with Bootstrap and custom CSS and JS files.

## Installation
1. Clone the repository.
2. Edit .env.example with your specifications.
3. Create and activate a virtual environment.

       python -m venv venv
       source venv/bin/activate
4. Install dependencies.

       pip install -r requirements.txt
5. Set up the database.

       python init_db.py
6. Run the server.

       python run.py

## Unit Tests
To run unit tests, execute the following command:

       pytest -v --cov=app
