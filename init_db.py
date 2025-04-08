from app import create_app, db
from app.models import User, Organizer

app = create_app()

with app.app_context():
    db.create_all()
    
    if not Organizer.query.first():
        org = Organizer(name='JJK Presents', description='Main organizer')
        db.session.add(org)
        db.session.commit()
        
        admin = User(
            username='admin',
            email='admin@example.com',
            is_manager=True,
            organizer_id=org.id
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
    
    print("Database initialized successfully!")