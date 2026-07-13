import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from config import Config

engine = None
SessionLocal = None
Base = declarative_base()

def init_db():
    global engine, SessionLocal
    if engine is None:
        try:
            # We add pool_pre_ping=True to handle disconnected connections gracefully
            engine = create_engine(
                Config.SQLALCHEMY_DATABASE_URI,
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args={'connect_timeout': 3}
            )
            
            # Attempt a connection to verify
            with engine.connect() as conn:
                pass
            
            # Create tables if they don't exist
            from database.models import Base
            Base.metadata.create_all(bind=engine)
            
            SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
            print(f"[DB] Connected to TiDB: {Config.TIDB_DB_NAME}")
        except Exception as e:
            print(f"[DB] TiDB connection error: {e}")
            engine = None
            SessionLocal = None

def get_db():
    """
    Get SQLAlchemy scoped session. Creates connection on first call if not initialized.
    Returns None if database is not available so routes/models can handle gracefully.
    """
    global engine, SessionLocal
    if SessionLocal is None:
        init_db()
        if SessionLocal is None:
            return None
    
    try:
        from sqlalchemy import text
        # Check if the connection is still alive
        session = SessionLocal()
        session.execute(text("SELECT 1"))
        return session
    except Exception as e:
        print(f"[DB] Session error: {e}")
        # Could be a lost connection, reset it
        if SessionLocal:
            SessionLocal.remove()
        engine = None
        SessionLocal = None
        return None

def close_db(e=None):
    """Remove the scoped session at the end of the request."""
    if SessionLocal is not None:
        SessionLocal.remove()
