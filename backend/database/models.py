import json
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, BigInteger
from sqlalchemy.orm import relationship
from database.db import Base, get_db
import database.json_db as jdb

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password = Column(String(255), nullable=True)
    oauth_provider = Column(String(50), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    files = relationship("File", back_populates="user", cascade="all, delete-orphan")
    histories = relationship("History", back_populates="user", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="user")
    oauth_tokens = relationship("OAuthToken", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            '_id': str(self.id),
            'name': self.name,
            'email': self.email,
            'password': self.password,
            'oauth_provider': self.oauth_provider,
            'avatar_url': self.avatar_url,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

class File(Base):
    __tablename__ = 'files'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_type = Column(String(50))
    file_path = Column(String(500))
    size = Column(BigInteger)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="files")
    histories = relationship("History", back_populates="file", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="file", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            '_id': str(self.id),
            'user_id': str(self.user_id),
            'filename': self.filename,
            'original_name': self.original_name,
            'file_type': self.file_type,
            'file_path': self.file_path,
            'size': self.size,
            'created_at': self.created_at,
        }

class History(Base):
    __tablename__ = 'history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    file_id = Column(Integer, ForeignKey('files.id'), nullable=True)
    operation = Column(String(100))
    result = Column(Text)
    metadata_ = Column("metadata", JSON)  # metadata is reserved by SQLAlchemy
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="histories")
    file = relationship("File", back_populates="histories")

    def to_dict(self):
        return {
            '_id': str(self.id),
            'user_id': str(self.user_id) if self.user_id else None,
            'file_id': str(self.file_id) if self.file_id else None,
            'operation': self.operation,
            'result': self.result,
            'metadata': self.metadata_,
            'created_at': self.created_at,
        }

class Chat(Base):
    __tablename__ = 'chat'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    file_id = Column(Integer, ForeignKey('files.id'), nullable=True)
    messages = Column(JSON)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="chats")
    file = relationship("File", back_populates="chats")

    def to_dict(self):
        return {
            '_id': str(self.id),
            'user_id': str(self.user_id) if self.user_id else None,
            'file_id': str(self.file_id) if self.file_id else None,
            'messages': self.messages,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

class Feedback(Base):
    __tablename__ = 'feedback'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    rating = Column(Integer)
    message = Column(Text)
    page = Column(String(255))
    user_agent = Column(String(500))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="feedbacks")

    def to_dict(self):
        return {
            '_id': str(self.id),
            'user_id': str(self.user_id) if self.user_id else None,
            'rating': self.rating,
            'message': self.message,
            'page': self.page,
            'user_agent': self.user_agent,
            'created_at': self.created_at,
        }

class OAuthToken(Base):
    __tablename__ = 'oauth_tokens'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    provider = Column(String(50), index=True)
    token = Column(Text, nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_uri = Column(String(255), nullable=True)
    client_id = Column(String(255), nullable=True)
    client_secret = Column(String(255), nullable=True)
    
    user = relationship("User", back_populates="oauth_tokens")
    
    def to_dict(self):
        return {
            '_id': str(self.id),
            'user_id': str(self.user_id),
            'provider': self.provider,
            'token': self.token,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_uri': self.token_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }

def _parse_id(id_str):
    if not id_str:
        return None
    try:
        return int(id_str)
    except ValueError:
        return None

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def create_user(name: str, email: str, password_hash: str) -> dict | None:
    session = get_db()
    if session is None:
        return jdb.json_create_user(name, email, password_hash)
    try:
        user = User(
            name=name,
            email=email.lower().strip(),
            password=password_hash
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.to_dict()
    except Exception as e:
        session.rollback()
        print(f"[Models] create_user error: {e}")
        return None

def create_oauth_user(name: str, email: str, provider: str, avatar_url: str = None) -> dict | None:
    session = get_db()
    email_clean = email.lower().strip()
    
    existing = find_user_by_email(email_clean)
    if existing is not None:
        user_id = str(existing['_id'])
        update_fields = {}
        if not existing.get('oauth_provider'):
            update_fields['oauth_provider'] = provider
        if avatar_url and not existing.get('avatar_url'):
            update_fields['avatar_url'] = avatar_url
            
        if update_fields:
            update_user(user_id, update_fields)
            existing = find_user_by_id(user_id)
        return existing
        
    if session is None:
        return jdb.json_create_oauth_user(name, email_clean, provider, avatar_url)
        
    try:
        user = User(
            name=name,
            email=email_clean,
            oauth_provider=provider,
            avatar_url=avatar_url
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.to_dict()
    except Exception as e:
        session.rollback()
        print(f"[Models] create_oauth_user error: {e}")
        return None

def find_user_by_email(email: str) -> dict | None:
    session = get_db()
    if session is None:
        return jdb.json_find_user_by_email(email)
    try:
        user = session.query(User).filter(User.email == email.lower().strip()).first()
        return user.to_dict() if user else None
    except Exception as e:
        print(f"[Models] find_user_by_email error: {e}")
        return None

def find_user_by_id(user_id: str) -> dict | None:
    session = get_db()
    if session is None:
        return jdb.json_find_user_by_id(user_id)
    uid = _parse_id(user_id)
    if uid is None: return None
    try:
        user = session.query(User).filter(User.id == uid).first()
        return user.to_dict() if user else None
    except Exception as e:
        print(f"[Models] find_user_by_id error: {e}")
        return None

def update_user(user_id: str, update_fields: dict) -> bool:
    session = get_db()
    if session is None:
        return jdb.json_update_user(user_id, update_fields)
    uid = _parse_id(user_id)
    if uid is None: return False
    try:
        if 'email' in update_fields:
            update_fields['email'] = update_fields['email'].lower().strip()
        
        user = session.query(User).filter(User.id == uid).first()
        if not user:
            return False
            
        for key, value in update_fields.items():
            if hasattr(user, key):
                setattr(user, key, value)
                
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"[Models] update_user error: {e}")
        return False

# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

def save_file_record(user_id: str, filename: str, original_name: str,
                     file_type: str, file_path: str, size: int) -> dict | None:
    session = get_db()
    if session is None:
        return jdb.json_save_file_record(user_id, filename, original_name, file_type, file_path, size)
    uid = _parse_id(user_id)
    if uid is None: return None
    try:
        f = File(
            user_id=uid,
            filename=filename,
            original_name=original_name,
            file_type=file_type,
            file_path=file_path,
            size=size
        )
        session.add(f)
        session.commit()
        session.refresh(f)
        return f.to_dict()
    except Exception as e:
        session.rollback()
        print(f"[Models] save_file_record error: {e}")
        return None

def get_user_files(user_id: str) -> list:
    session = get_db()
    if session is None:
        return jdb.json_get_user_files(user_id)
    uid = _parse_id(user_id)
    if uid is None: return []
    try:
        files = session.query(File).filter(File.user_id == uid).order_by(File.created_at.desc()).all()
        return [f.to_dict() for f in files]
    except Exception as e:
        print(f"[Models] get_user_files error: {e}")
        return []

def get_file_by_id(file_id: str) -> dict | None:
    session = get_db()
    if session is None:
        return jdb.json_get_file_by_id(file_id)
    fid = _parse_id(file_id)
    if fid is None: return None
    try:
        f = session.query(File).filter(File.id == fid).first()
        if f:
            d = f.to_dict()
            # If R2 is configured and file is missing locally, restore it
            import os
            from services.file_service import download_from_r2
            if not os.path.exists(d['file_path']):
                os.makedirs(os.path.dirname(d['file_path']), exist_ok=True)
                download_from_r2(d['filename'], d['file_path'])
            return d
        return None
    except Exception as e:
        print(f"[Models] get_file_by_id error: {e}")
        return None

def delete_file_record(file_id: str) -> bool:
    session = get_db()
    if session is None:
        return jdb.json_delete_file_record(file_id)
    fid = _parse_id(file_id)
    if fid is None: return False
    try:
        f = session.query(File).filter(File.id == fid).first()
        if f:
            session.delete(f)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        print(f"[Models] delete_file_record error: {e}")
        return False

# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

def save_history(user_id: str, file_id: str, operation: str,
                 result: str, metadata: dict | None = None) -> dict | None:
    session = get_db()
    if session is None:
        return jdb.json_save_history(user_id, file_id, operation, result, metadata)
    uid = _parse_id(user_id)
    fid = _parse_id(file_id) if file_id else None
    
    try:
        h = History(
            user_id=uid,
            file_id=fid,
            operation=operation,
            result=result,
            metadata_=metadata or {}
        )
        session.add(h)
        session.commit()
        session.refresh(h)
        return h.to_dict()
    except Exception as e:
        session.rollback()
        print(f"[Models] save_history error: {e}")
        return None

def get_user_history(user_id: str, limit: int = 50) -> list:
    session = get_db()
    if session is None:
        return jdb.json_get_user_history(user_id, limit)
    uid = _parse_id(user_id)
    if uid is None: return []
    try:
        histories = session.query(History).filter(History.user_id == uid).order_by(History.created_at.desc()).limit(limit).all()
        return [h.to_dict() for h in histories]
    except Exception as e:
        print(f"[Models] get_user_history error: {e}")
        return []

# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

def save_chat(user_id: str, file_id: str, messages: list) -> dict | None:
    session = get_db()
    if session is None:
        return jdb.json_save_chat(user_id, file_id, messages)
    uid = _parse_id(user_id)
    fid = _parse_id(file_id) if file_id else None
    try:
        c = Chat(
            user_id=uid,
            file_id=fid,
            messages=messages
        )
        session.add(c)
        session.commit()
        session.refresh(c)
        return c.to_dict()
    except Exception as e:
        session.rollback()
        print(f"[Models] save_chat error: {e}")
        return None

def get_chat(chat_id: str) -> dict | None:
    session = get_db()
    if session is None:
        return jdb.json_get_chat(chat_id)
    cid = _parse_id(chat_id)
    if cid is None: return None
    try:
        c = session.query(Chat).filter(Chat.id == cid).first()
        return c.to_dict() if c else None
    except Exception as e:
        print(f"[Models] get_chat error: {e}")
        return None

def get_chat_by_file(user_id: str, file_id: str) -> dict | None:
    session = get_db()
    if session is None:
        return jdb.json_get_chat_by_file(user_id, file_id)
    uid = _parse_id(user_id)
    fid = _parse_id(file_id) if file_id else None
    try:
        c = session.query(Chat).filter(Chat.user_id == uid, Chat.file_id == fid).order_by(Chat.updated_at.desc()).first()
        return c.to_dict() if c else None
    except Exception as e:
        print(f"[Models] get_chat_by_file error: {e}")
        return None

def update_chat_messages(chat_id: str, messages: list) -> bool:
    session = get_db()
    if session is None:
        return jdb.json_update_chat_messages(chat_id, messages)
    cid = _parse_id(chat_id)
    if cid is None: return False
    try:
        c = session.query(Chat).filter(Chat.id == cid).first()
        if c:
            c.messages = messages
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        print(f"[Models] update_chat_messages error: {e}")
        return False

def get_user_chats(user_id: str) -> list:
    session = get_db()
    if session is None:
        return jdb.json_get_user_chats(user_id)
    uid = _parse_id(user_id)
    if uid is None: return []
    try:
        chats = session.query(Chat).filter(Chat.user_id == uid).order_by(Chat.updated_at.desc()).all()
        return [c.to_dict() for c in chats]
    except Exception as e:
        print(f"[Models] get_user_chats error: {e}")
        return []
