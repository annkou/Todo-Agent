import datetime
from typing import Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from todo_agent.db import Base, SessionLocal


class Thread(Base):
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True)
    thread_id = Column(String(100), unique=True, nullable=False, index=True)
    objective = Column(Text, nullable=False)
    status = Column(String(20), default="active")  # active, completed, failed
    created_at = Column(DateTime, default=datetime.datetime.now())
    updated_at = Column(
        DateTime, default=datetime.datetime.now(), onupdate=datetime.datetime.now()
    )

    # Relationships
    tasks = relationship("Task", back_populates="session", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "thread_id": self.thread_id,
            "objective": self.objective,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("threads.id"), nullable=False)
    task_id = Column(Integer, nullable=False)  # Task number in the plan (1, 2, 3...)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(
        String(20), default="pending"
    )  # pending, in_progress, completed, failed
    result = Column(Text, nullable=True)
    reflection = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    session = relationship("Thread", back_populates="tasks")

    def to_dict(self):
        return {
            "id": self.task_id,
            "title": self.title,
            "content": self.content,
            "status": self.status,
            "result": self.result,
            "reflection": self.reflection,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
        }


def get_session_by_thread(thread_id: str) -> Optional[Dict]:
    """Retrieve session and tasks by thread_id."""
    db = SessionLocal()
    try:
        session = db.query(Thread).filter(Thread.thread_id == thread_id).first()
        if session:
            return {
                "session": session.to_dict(),
                "tasks": [task.to_dict() for task in session.tasks],
            }
        return None
    finally:
        db.close()


def create_session(thread_id: str, objective: str, tasks: List[Dict]):
    """Create a new session with initial plan."""
    db = SessionLocal()
    try:
        # Create session
        session = Thread(thread_id=thread_id, objective=objective, status="active")
        db.add(session)
        db.flush()  # Get session.id

        # Create tasks
        for task_data in tasks:
            task = Task(
                session_id=session.id,
                task_id=task_data["id"],
                title=task_data["title"],
                content=task_data["content"],
                status="pending",
            )
            db.add(task)
        db.commit()
        return get_session_by_thread(thread_id)
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def update_task_status(
    thread_id: str,
    task_id: int,
    status: str,
    result: Optional[str] = None,
    reflection: Optional[str] = None,
):
    """Update task execution status."""
    db = SessionLocal()
    try:
        session = db.query(Thread).filter(Thread.thread_id == thread_id).first()
        if session:
            task = (
                db.query(Task)
                .filter(Task.session_id == session.id, Task.task_id == task_id)
                .first()
            )

            if task:
                task.status = status
                if result:
                    task.result = result
                if reflection:
                    task.reflection = reflection

                if status == "in_progress" and not task.started_at:
                    task.started_at = datetime.datetime.now()
                elif status in ["completed", "failed"]:
                    task.completed_at = datetime.datetime.now()

                db.commit()
    finally:
        db.close()


def get_completed_tasks(thread_id: str) -> List[Dict]:
    """Get all completed tasks for context."""
    db = SessionLocal()
    try:
        session = db.query(Thread).filter(Thread.thread_id == thread_id).first()
        if session:
            completed = (
                db.query(Task)
                .filter(Task.session_id == session.id, Task.status == "completed")
                .order_by(Task.task_id)
                .all()
            )

            return [
                {
                    "id": task.task_id,
                    "title": task.title,
                    "description": task.content,
                    "result": task.result,
                }
                for task in completed
            ]
        return []
    finally:
        db.close()


def get_pending_tasks(thread_id: str) -> List[Dict]:
    """Get remaining pending tasks."""
    db = SessionLocal()
    try:
        session = db.query(Thread).filter(Thread.thread_id == thread_id).first()
        if session:
            pending = (
                db.query(Task)
                .filter(Task.session_id == session.id, Task.status == "pending")
                .order_by(Task.task_id)
                .all()
            )

            return [task.to_dict() for task in pending]
        return []
    finally:
        db.close()


def mark_session_complete(thread_id: str):
    """Mark session as completed."""
    db = SessionLocal()
    try:
        session = db.query(Thread).filter(Thread.thread_id == thread_id).first()
        if session:
            session.status = "completed"
            session.updated_at = datetime.datetime.now()
            db.commit()
    finally:
        db.close()
