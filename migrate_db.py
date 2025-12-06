
"""
Database migration script to transition from OAuth to email/password authentication.
Run this ONCE after deploying the new authentication system.
"""

from app import app, db
from models import User

def migrate_database():
    with app.app_context():
        print("Starting database migration...")
        
        # Drop all tables to start fresh (with CASCADE to handle dependencies)
        print("Dropping all existing tables...")
        db.session.execute(db.text('DROP TABLE IF EXISTS flask_dance_oauth CASCADE'))
        db.session.execute(db.text('DROP TABLE IF EXISTS users CASCADE'))
        db.session.execute(db.text('DROP TABLE IF EXISTS documents CASCADE'))
        db.session.execute(db.text('DROP TABLE IF EXISTS chat_messages CASCADE'))
        db.session.execute(db.text('DROP TABLE IF EXISTS question_analytics CASCADE'))
        db.session.commit()
        print("✓ All tables dropped")
        
        # Recreate all tables with new schema
        print("Creating tables with new schema...")
        db.create_all()
        print("✓ Database tables created with new schema")
        
        # Create default admin user
        admin_email = 'azrieydev@gmail.com'
        admin = User.query.filter_by(email=admin_email).first()
        
        if not admin:
            admin = User(email=admin_email, role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print(f"✓ Created admin user: {admin_email}")
            print("  Default password: admin123")
            print("  ⚠️  IMPORTANT: Change this password immediately after logging in!")
        else:
            print(f"✓ Admin user already exists: {admin_email}")
        
        print("\n" + "="*60)
        print("Migration complete!")
        print("="*60)
        print("\nNext steps:")
        print("1. Login with azrieydev@gmail.com / admin123")
        print("2. Change the admin password immediately")
        print("3. Users will need to register new accounts")
        print("="*60)

if __name__ == '__main__':
    migrate_database()
