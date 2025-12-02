#!/usr/bin/env python3
"""
Check if database schema is in sync with SQLModel models.
This helps detect when you've changed models but haven't created a migration yet.
"""
import sys
import os

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine
from core.db.engine import DATABASE_URL

def check_schema_drift():
    """Check if there are pending model changes that need a migration."""
    
    # Create Alembic config
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)
    
    # Get current database revision
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_rev = context.get_current_revision()
    
    # Get head revision from migrations
    head_rev = script.get_current_head()
    
    print("🔍 Schema Drift Check")
    print("=" * 50)
    print(f"Current database revision: {current_rev}")
    print(f"Latest migration revision: {head_rev}")
    print()
    
    if current_rev == head_rev:
        print("✅ Database is up to date!")
        print()
        print("💡 If you've changed models, run:")
        print("   make migration msg='describe your changes'")
        return 0
    elif current_rev is None:
        print("⚠️  No migrations have been applied to the database!")
        print()
        print("Run: make migrate")
        return 1
    else:
        print("⚠️  Database is behind the latest migration!")
        print()
        print("Run: make migrate")
        return 1

if __name__ == "__main__":
    sys.exit(check_schema_drift())
