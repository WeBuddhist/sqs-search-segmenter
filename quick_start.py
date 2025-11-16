#!/usr/bin/env python3
"""
Quick Start Script for SQS Search Segmenter

This script helps you quickly set up and verify your environment.

Usage:
    python quick_start.py check       # Check all prerequisites
    python quick_start.py setup       # Setup database
    python quick_start.py test        # Test the system
    python quick_start.py run         # Run the application
"""

import sys
import os
import subprocess
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Colors:
    """Terminal colors for pretty output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_step(message):
    """Print a step message"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}➜ {message}{Colors.END}")


def print_success(message):
    """Print a success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message):
    """Print an error message"""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_warning(message):
    """Print a warning message"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")


def check_python_version():
    """Check Python version"""
    print_step("Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print_success(f"Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor} - Requires Python 3.9+")
        return False


def check_env_file():
    """Check if .env file exists"""
    print_step("Checking environment configuration...")
    if Path(".env").exists():
        print_success(".env file exists")
        return True
    else:
        print_warning(".env file not found")
        if Path("env.example").exists():
            print("  Run: cp env.example .env")
            print("  Then edit .env with your configuration")
        return False


def check_required_env_vars():
    """Check if required environment variables are set"""
    print_step("Checking required environment variables...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'POSTGRES_URL',
        'NEO4J_URI',
        'NEO4J_USER',
        'NEO4J_PASSWORD',
        'AWS_REGION',
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'SQS_QUEUE_URL'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if not missing:
        print_success("All required environment variables are set")
        return True
    else:
        print_error(f"Missing environment variables: {', '.join(missing)}")
        return False


def check_postgres_connection():
    """Check PostgreSQL connection"""
    print_step("Checking PostgreSQL connection...")
    try:
        from app.db.postgres import engine
        connection = engine.connect()
        connection.close()
        print_success("PostgreSQL connection successful")
        return True
    except Exception as e:
        print_error(f"PostgreSQL connection failed: {e}")
        return False


def check_neo4j_connection():
    """Check Neo4j connection"""
    print_step("Checking Neo4j connection...")
    try:
        from app.neo4j_database import Neo4JDatabase
        db = Neo4JDatabase()
        # Try to get a session
        with db.get_session() as session:
            session.run("RETURN 1").single()
        print_success("Neo4j connection successful")
        return True
    except Exception as e:
        print_error(f"Neo4j connection failed: {e}")
        return False


def check_aws_credentials():
    """Check AWS credentials"""
    print_step("Checking AWS credentials and SQS access...")
    try:
        import boto3
        from app.config import get
        
        sqs = boto3.client(
            'sqs',
            region_name=get('AWS_REGION'),
            aws_access_key_id=get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=get('AWS_SECRET_ACCESS_KEY')
        )
        
        queue_url = get('SQS_QUEUE_URL')
        if queue_url:
            response = sqs.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['ApproximateNumberOfMessages']
            )
            print_success(f"AWS SQS connection successful")
            print(f"  Queue messages: {response['Attributes']['ApproximateNumberOfMessages']}")
            return True
        else:
            print_error("SQS_QUEUE_URL not configured")
            return False
            
    except Exception as e:
        print_error(f"AWS connection failed: {e}")
        return False


def setup_database():
    """Initialize database tables"""
    print_step("Setting up database...")
    try:
        from app.db.postgres import engine
        from app.db.models import Base
        
        Base.metadata.create_all(bind=engine)
        print_success("Database tables created successfully")
        return True
    except Exception as e:
        print_error(f"Database setup failed: {e}")
        return False


def run_checks():
    """Run all prerequisite checks"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}SQS Search Segmenter - Environment Check{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")
    
    checks = [
        ("Python Version", check_python_version),
        ("Environment File", check_env_file),
        ("Environment Variables", check_required_env_vars),
        ("PostgreSQL Connection", check_postgres_connection),
        ("Neo4j Connection", check_neo4j_connection),
        ("AWS SQS Access", check_aws_credentials),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"Error during {name} check: {e}")
            results.append((name, False))
    
    # Print summary
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}Summary{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.GREEN}✓ PASS{Colors.END}" if result else f"{Colors.RED}✗ FAIL{Colors.END}"
        print(f"  {name:<30} {status}")
    
    print(f"\n{Colors.BOLD}Result: {passed}/{total} checks passed{Colors.END}\n")
    
    if passed == total:
        print_success("All checks passed! You're ready to run the application.")
        print("\nNext steps:")
        print("  1. python quick_start.py setup   # Initialize database")
        print("  2. python quick_start.py run     # Start the application")
    else:
        print_error("Some checks failed. Please fix the issues above.")
    
    return passed == total


def run_application():
    """Start the application"""
    print_step("Starting application...")
    try:
        import uvicorn
        uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
    except Exception as e:
        print_error(f"Failed to start application: {e}")


def test_system():
    """Run a simple system test"""
    print_step("Testing the system...")
    
    try:
        import requests
        import time
        
        base_url = "http://localhost:8080"
        
        # Check if service is running
        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                print_success("Service is running")
            else:
                print_error(f"Service returned status code {response.status_code}")
                return False
        except requests.exceptions.RequestException:
            print_error("Service is not running. Start it first with: python quick_start.py run")
            return False
        
        # Test job creation (example)
        print("\nTo test job creation:")
        print(f"""
curl -X POST "{base_url}/jobs/create" \\
  -H "Content-Type: application/json" \\
  -d '{{"manifestation_id": "test-001"}}'
        """)
        
        return True
        
    except ImportError:
        print_warning("requests library not installed. Install with: pip install requests")
        return False


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} [check|setup|test|run]")
        print("\nCommands:")
        print("  check  - Check all prerequisites")
        print("  setup  - Initialize database")
        print("  test   - Test the system")
        print("  run    - Run the application")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "check":
        success = run_checks()
        sys.exit(0 if success else 1)
    
    elif command == "setup":
        success = setup_database()
        sys.exit(0 if success else 1)
    
    elif command == "test":
        success = test_system()
        sys.exit(0 if success else 1)
    
    elif command == "run":
        run_application()
    
    else:
        print_error(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()

