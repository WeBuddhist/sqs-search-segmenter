from sqlalchemy import Column, String, Integer, Text, ForeignKey, CheckConstraint, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
from uuid import uuid4

# Create Base here to avoid circular import
Base = declarative_base()


class RootJob(Base):
    __tablename__ = "root_jobs"

    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    manifestation_id = Column(Text, nullable=False)
    status = Column(
        String(20),
        CheckConstraint(
            "status IN ('QUEUED','IN_PROGRESS','COMPLETED','FAILED')",
            name="root_job_status_check"
        ),
        nullable=False
    )
    total_segments = Column(Integer, default=0, nullable=False)
    completed_segments = Column(Integer, default=0, nullable=False)
    result_json = Column(JSONB, nullable=True)
    merged_result_location = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# class ManifestationTask(Base):
#     __tablename__ = "manifestation_tasks"

#     task_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
#     job_id = Column(UUID(as_uuid=True), ForeignKey("root_jobs.job_id"), nullable=False)
#     manifestation_id = Column(Text, nullable=False)
#     status = Column(
#         String(20),
#         CheckConstraint(
#             "status IN ('QUEUED','IN_PROGRESS','COMPLETED','FAILED','RETRYING')",
#             name="manifestation_task_status_check"
#         ),
#         nullable=False
#     )
#     result_json = Column(JSONB, nullable=True)
#     result_location = Column(Text, nullable=True)
#     error_message = Column(Text, nullable=True)
#     created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
#     updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

#     root_job = relationship("RootJob", back_populates="manifestation_tasks")