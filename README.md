# INFSCI 0201 Final Project: *JJK Presents Events*

## Introduction
*JJK Presents Events* is a web app built with Python that allows users to create, manage, search, and sign up for events. The system supports authentication, event categorization, a search function, user profiles, and management capabilities for event organizers.

## System Architecture
### Architectural Design
The system follows an MVC architecture based around different components relating to user authentication, event management, search and filtering, notification, data storage, the API, and the UI.

### Decomposition
  1. The UI communicates with the API for user and event data retrieval.
  2. The API connects to data storage for persistent storage access.
  3. Authentication ensures secure access control before gaining access to the UI.
  4. Event management then accesses the API to process event-related requests and the search and filter and notification functions then access it.

### Design Rationale
The MVC architecture of the system was chosen to ensure scalability and maintainability. Each component of the system is responsible for a specific functionality, making it easier to develop, test, and extend. The use of a relational database ensures data integrity while the API allows for multi-platform use.

## Installation
1. Clone the repository.
2. Create and activate a virtual environment.

       python -m venv venv
       source venv/bin/activate
3. Install dependencies.

       pip install -r requirements.txt
4. Set up the database.

       flask db init
       flask db migrate
       flask db upgrade