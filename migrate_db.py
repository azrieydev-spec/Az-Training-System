
"""
Database migration script to transition from OAuth to email/password authentication.
Run this ONCE after deploying the new authentication system.
"""

from app import app, db
from models import User

def migrate_database():
    with app.app_context():
        print("Starting database migration...")
        
        # Drop old OAuth table if it exists
        try:
            db.session.execute(db.text("DROP TABLE IF EXISTS o_auth CASCADE"))
            db.session.commit()
            print("✓ Dropped old OAuth table")
        except Exception as e:
            print(f"Note: {e}")
            db.session.rollback()
        
        # Recreate all tables with new schema
        db.drop_all()
        db.create_all()
        print("✓ Recreated database tables")
        
        # Create default admin user
        admin_email = 'azrieydev@gmail.com'
        admin = User.query.filter_by(email=admin_email).first()
        
        if not admin:
            admin = User(email=admin_email, role='admin')
            admin.set_password('admin123')  # Change this password immediately after first login!
            db.session.add(admin)
            db.session.commit()
            print(f"✓ Created admin user: {admin_email}")
            print("  Default password: admin123")
            print("  ⚠️  IMPORTANT: Change this password immediately after logging in!")
        else:
            print(f"✓ Admin user already exists: {admin_email}")
        
        print("\nMigration complete!")
        print("\nNext steps:")
        print("1. Login with azrieydev@gmail.com / admin123")
        print("2. Change the admin password immediately")
        print("3. Users will need to register new accounts")

if __name__ == '__main__':
    migrate_database()
