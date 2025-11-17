#!/usr/bin/env python3
"""
Script to run process_manifestation_task directly from terminal for testing.
Usage: python run_task.py <manifestation_id> [job_id]
"""
import sys
import uuid
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv(override=True)

from app.tasks import process_manifestation_task
from app.db.postgres import SessionLocal
from app.db.models import RootJob

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_task.py <manifestation_id> [job_id]")
        print("Example: python run_task.py qqyEEnVA4IrQ510gxvxWD")
        sys.exit(1)
    
    manifestation_id = sys.argv[1]
    
    # Use provided job_id or generate a new one
    if len(sys.argv) >= 3:
        job_id = sys.argv[2]
    else:
        job_id = str(uuid.uuid4())
        print(f"Generated job_id: {job_id}")
    
    print(f"Processing manifestation: {manifestation_id}")
    print(f"Job ID: {job_id}")
    
    # Create a RootJob entry in the database
    print("Creating RootJob entry in database...")
    try:
        with SessionLocal() as session:
            # Check if job already exists
            existing_job = session.query(RootJob).filter(RootJob.job_id == job_id).first()
            if not existing_job:
                root_job = RootJob(
                    job_id=job_id,
                    manifestation_id=manifestation_id,
                    status="QUEUED",
                    total_segments=0,
                    completed_segments=0
                )
                session.add(root_job)
                session.commit()
                print(f"Created RootJob with job_id: {job_id}")
            else:
                print(f"RootJob already exists with job_id: {job_id}")
    except Exception as e:
        print(f"Failed to create RootJob: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("-" * 50)
    
    try:
        result = process_manifestation_task(job_id=job_id, manifestation_id=manifestation_id)
        print("-" * 50)
        print("Task completed successfully!")
        print(f"Result: {result}")
    except Exception as e:
        print("-" * 50)
        print(f"Task failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

