from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from todo_agent.config import settings

engine = create_engine(settings.database_dsn)

# SQLAlchemy ORM session factory bound to this engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for the classes (tables) definitions
Base = declarative_base()
