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



def run_checks():
    """Run all prerequisite checks"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}SQS Search Segmenter - Environment Check{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")
    
    checks = [
        ("Python Version", check_python_version),
        ("Environment File", check_env_file),
        ("Environment Variables", check_required_env_vars),
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
        print_success("All checks passed! You're ready to run the workers.")
        print("\nNext steps:")
        print("  1. python quick_start.py setup        # Initialize database")
        print("  2. docker-compose up worker           # Start SQS workers")
        print("\nNote: API service is deployed separately")
    else:
        print_error("Some checks failed. Please fix the issues above.")
    
    return passed == total


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} [check|setup]")
        print("\nCommands:")
        print("  check  - Check all prerequisites")
        print("  setup  - Initialize database")
        print("\nNote: API commands (test/run) have been removed.")
        print("      The API is deployed separately.")
        print("      To run workers: docker-compose up worker")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "check":
        success = run_checks()
        sys.exit(0 if success else 1)
    
    else:
        print_error(f"Unknown command: {command}")
        print("Available commands: check")
        sys.exit(1)


if __name__ == "__main__":
    main()

