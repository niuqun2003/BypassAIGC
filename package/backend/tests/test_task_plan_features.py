import asyncio
import importlib
import sys
from io import BytesIO
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import Base
from app.models.models import OptimizationSegment, OptimizationSession, User
from app.routes import admin, optimization


def make_session(tmp_path, name="app.db"):
    db_path = tmp_path / name
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine, TestingSessionLocal()


def create_user(db, *, card_key="CARD-001", usage_limit=10, usage_count=3):
    user = User(
        card_key=card_key,
        access_link=f"https://example.com/{card_key}",
        is_active=True,
        usage_limit=usage_limit,
        usage_count=usage_count,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_session(
    db,
    user,
    *,
    session_id="sess-001",
    status="completed",
    original_text="original text",
):
    session = OptimizationSession(
        user_id=user.id,
        session_id=session_id,
        original_text=original_text,
        current_stage="polish",
        status=status,
        progress=100.0 if status == "completed" else 0.0,
        current_position=0,
        total_segments=1,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def create_segment(
    db,
    session,
    *,
    segment_index=0,
    original_text="original",
    polished_text="polished",
    enhanced_text="enhanced",
    status="completed",
):
    segment = OptimizationSegment(
        session_id=session.id,
        segment_index=segment_index,
        stage="polish",
        original_text=original_text,
        polished_text=polished_text,
        enhanced_text=enhanced_text,
        status=status,
        is_title=False,
    )
    db.add(segment)
    db.commit()
    db.refresh(segment)
    return segment


def test_verify_card_key_returns_usage_fields(tmp_path):
    _, db = make_session(tmp_path)
    user = create_user(db, usage_limit=12, usage_count=4)

    payload = admin.CardKeyVerify(card_key=user.card_key)
    result = asyncio.run(admin.verify_card_key(payload, db))

    assert result["valid"] is True
    assert result["user_id"] == user.id
    assert result["usage_limit"] == 12
    assert result["usage_count"] == 4


def test_submit_feedback_stores_rating_for_completed_session(tmp_path):
    _, db = make_session(tmp_path)
    user = create_user(db)
    session = create_session(db, user, session_id="sess-feedback")
    schemas = importlib.import_module("app.schemas")

    response = asyncio.run(
        optimization.submit_feedback(
            session.session_id,
            user.card_key,
            getattr(schemas, "SessionFeedback")(rating=5, comment="很好"),
            db,
        )
    )

    db.refresh(session)
    assert response["rating"] == 5
    assert session.user_rating == 5
    assert session.user_comment == "很好"


def test_get_user_stats_aggregates_completed_data(tmp_path):
    _, db = make_session(tmp_path)
    user = create_user(db, usage_limit=8, usage_count=2)
    completed = create_session(db, user, session_id="sess-completed", original_text="abcd")
    create_segment(db, completed, segment_index=0, status="completed")
    create_segment(db, completed, segment_index=1, status="completed")
    completed.user_rating = 4

    queued = create_session(db, user, session_id="sess-queued", status="queued", original_text="queue")
    create_segment(db, queued, segment_index=0, status="pending")
    db.commit()

    result = asyncio.run(optimization.get_user_stats(user.card_key, db))

    assert result["total_sessions"] == 2
    assert result["completed_sessions"] == 1
    assert result["total_segments"] == 2
    assert result["total_chars"] == 4
    assert result["avg_rating"] == 4.0
    assert result["usage_limit"] == 8
    assert result["usage_count"] == 2


def test_edit_segment_updates_export_fallback_chain(tmp_path):
    _, db = make_session(tmp_path)
    user = create_user(db)
    session = create_session(db, user, session_id="sess-edit")
    create_segment(
        db,
        session,
        original_text="原文",
        polished_text="润色",
        enhanced_text="增强",
    )
    schemas = importlib.import_module("app.schemas")

    asyncio.run(
        optimization.edit_segment(
            session.session_id,
            user.card_key,
            getattr(schemas, "SegmentEdit")(segment_index=0, edited_text="用户改写"),
            db,
        )
    )

    export_response = asyncio.run(
        optimization.export_session(
            session.session_id,
            user.card_key,
            schemas.ExportConfirmation(
                session_id=session.session_id,
                acknowledge_academic_integrity=True,
                export_format="txt",
            ),
            db,
        )
    )

    assert export_response["content"] == "用户改写"


def test_schema_migration_adds_feedback_and_edit_columns(tmp_path, monkeypatch):
    database = importlib.import_module("app.database")
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE optimization_sessions (
                    id INTEGER PRIMARY KEY,
                    session_id VARCHAR(255),
                    processing_mode VARCHAR(50)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE optimization_segments (
                    id INTEGER PRIMARY KEY,
                    session_id INTEGER,
                    segment_index INTEGER,
                    is_title BOOLEAN DEFAULT 0
                )
                """
            )
        )

    monkeypatch.setattr(database, "engine", engine)
    database._migrate_database_schema()

    inspector = inspect(engine)
    session_columns = {column["name"] for column in inspector.get_columns("optimization_sessions")}
    segment_columns = {column["name"] for column in inspector.get_columns("optimization_segments")}

    assert {"user_rating", "user_comment"}.issubset(session_columns)
    assert "user_edited_text" in segment_columns


def test_export_docx_prefers_user_edited_text(tmp_path):
    _, db = make_session(tmp_path)
    user = create_user(db)
    session = create_session(db, user, session_id="sess-docx")
    segment = create_segment(db, session, original_text="原文", polished_text="润色", enhanced_text="增强")
    segment.user_edited_text = "终稿"
    db.commit()

    export_routes = importlib.import_module("app.routes.export")
    response = asyncio.run(export_routes.export_docx(session.session_id, user.card_key, db))
    content = asyncio.run(_collect_streaming_response(response))

    document = importlib.import_module("docx").Document(BytesIO(content))
    full_text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "终稿" in full_text


def test_upload_extract_text_supports_docx_and_rejects_other_files():
    upload_routes = importlib.import_module("app.routes.upload")
    docx_module = importlib.import_module("docx")
    upload_file_cls = importlib.import_module("starlette.datastructures").UploadFile

    document = docx_module.Document()
    document.add_paragraph("第一段")
    document.add_paragraph("第二段")
    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)

    response = asyncio.run(
        upload_routes.extract_text(
            upload_file_cls(filename="sample.docx", file=BytesIO(buffer.getvalue()))
        )
    )
    assert response["text"] == "第一段\n\n第二段"

    with pytest.raises(Exception):
        asyncio.run(
            upload_routes.extract_text(
                upload_file_cls(filename="sample.txt", file=BytesIO(b"plain text"))
            )
        )


async def _collect_streaming_response(response):
    chunks = []
    async for chunk in response.body_iterator:
        if isinstance(chunk, str):
            chunks.append(chunk.encode())
        else:
            chunks.append(chunk)
    return b"".join(chunks)
