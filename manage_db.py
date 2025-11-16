#!/usr/bin/env python3
"""
Database management script using Alembic.

This script provides simple commands for managing database migrations.

Usage:
    python manage_db.py upgrade    # Apply all pending migrations
    python manage_db.py downgrade  # Revert last migration
    python manage_db.py current    # Show current revision
    python manage_db.py history    # Show migration history
    python manage_db.py info       # Show database info
"""
import sys
import os
import subprocess
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Colors:
    """Terminal colors"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")


def run_alembic_command(args):
    """Run an alembic command"""
    try:
        cmd = ["alembic"] + args
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=False)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print_error(f"Alembic command failed: {e}")
        return False
    except FileNotFoundError:
        print_error("Alembic not found. Install with: pip install alembic")
        return False


def upgrade_database():
    """Upgrade database to latest migration"""
    print_info("Upgrading database to latest version...")
    if run_alembic_command(["upgrade", "head"]):
        print_success("Database upgraded successfully!")
        return True
    return False


def downgrade_database(steps=1):
    """Downgrade database by N steps"""
    print_info(f"Downgrading database by {steps} step(s)...")
    revision = f"-{steps}"
    if run_alembic_command(["downgrade", revision]):
        print_success("Database downgraded successfully!")
        return True
    return False


def show_current_revision():
    """Show current database revision"""
    print_info("Current database revision:")
    return run_alembic_command(["current"])


def show_history():
    """Show migration history"""
    print_info("Migration history:")
    return run_alembic_command(["history", "--verbose"])


def show_database_info():
    """Display database information"""
    try:
        from app.db.postgres import engine
        from sqlalchemy import inspect, text
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print("\n" + "="*60)
        print("DATABASE INFORMATION")
        print("="*60)
        print(f"\nDatabase URL: {engine.url}")
        print(f"\nTables ({len(tables)}):")
        
        for table in tables:
            columns = inspector.get_columns(table)
            print(f"\n  📋 {table}")
            print(f"     Columns: {len(columns)}")
            for col in columns[:5]:  # Show first 5 columns
                print(f"       - {col['name']} ({col['type']})")
            if len(columns) > 5:
                print(f"       ... and {len(columns) - 5} more")
            
            # Show row count
            try:
                with engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"     Rows: {count}")
            except Exception as e:
                print(f"     Rows: Unable to count ({str(e)[:50]})")
        
        # Show views
        views = inspector.get_view_names()
        if views:
            print(f"\nViews ({len(views)}):")
            for view in views:
                print(f"  📊 {view}")
        
        print("\n" + "="*60 + "\n")
        return True
        
    except Exception as e:
        print_error(f"Error showing database info: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_migration(message):
    """Create a new migration"""
    print_info(f"Creating new migration: {message}")
    if run_alembic_command(["revision", "--autogenerate", "-m", message]):
        print_success("Migration created successfully!")
        return True
    return False


def reset_database():
    """Reset database (downgrade all, then upgrade)"""
    print(f"{Colors.YELLOW}⚠️  WARNING: This will reset the entire database!{Colors.END}")
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() != 'yes':
        print_info("Operation cancelled")
        return False
    
    print_info("Downgrading to base...")
    if not run_alembic_command(["downgrade", "base"]):
        return False
    
    print_info("Upgrading to head...")
    if not run_alembic_command(["upgrade", "head"]):
        return False
    
    print_success("Database reset successfully!")
    return True


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Database management using Alembic',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_db.py upgrade              Apply all pending migrations
  python manage_db.py downgrade            Revert last migration
  python manage_db.py downgrade -n 2       Revert last 2 migrations
  python manage_db.py current              Show current revision
  python manage_db.py history              Show migration history
  python manage_db.py info                 Show database information
  python manage_db.py create "add index"   Create new migration
  python manage_db.py reset                Reset database (careful!)
        """
    )
    
    parser.add_argument(
        'command',
        choices=['upgrade', 'downgrade', 'current', 'history', 'info', 'create', 'reset'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '-n', '--steps',
        type=int,
        default=1,
        help='Number of steps for downgrade (default: 1)'
    )
    
    parser.add_argument(
        '-m', '--message',
        type=str,
        help='Migration message for create command'
    )
    
    args = parser.parse_args()
    
    # Check environment
    from app.config import get
    if not get("POSTGRES_URL"):
        print_error("POSTGRES_URL not set in environment!")
        print_info("Please create a .env file with your database configuration")
        sys.exit(1)
    
    # Execute command
    success = False
    
    if args.command == 'upgrade':
        success = upgrade_database()
    
    elif args.command == 'downgrade':
        success = downgrade_database(args.steps)
    
    elif args.command == 'current':
        success = show_current_revision()
    
    elif args.command == 'history':
        success = show_history()
    
    elif args.command == 'info':
        success = show_database_info()
    
    elif args.command == 'create':
        if not args.message:
            print_error("Migration message required. Use -m 'message'")
            sys.exit(1)
        success = create_migration(args.message)
    
    elif args.command == 'reset':
        success = reset_database()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

