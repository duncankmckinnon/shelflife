"""multi tenancy and sync

Revision ID: c9e4a6b21f03
Revises: b4d2f3a18c75
Create Date: 2026-03-01 00:00:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'c9e4a6b21f03'
down_revision: Union[str, Sequence[str], None] = 'b4d2f3a18c75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    conn = op.get_bind()
    postgres = _is_postgres()

    # -----------------------------------------------------------------------
    # 1. Create users table
    # -----------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("api_key_hash", sa.String(64), nullable=False),
        sa.Column("api_key_prefix", sa.String(12), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_api_key_hash", "users", ["api_key_hash"], unique=True)

    # Insert default local user with a deterministic ID
    from shelflife.id import make_id
    local_user_id = make_id("local")
    conn.execute(text(
        "INSERT INTO users (id, username, email, api_key_hash, api_key_prefix, created_at) "
        "VALUES (:id, 'local', 'local@localhost', 'NO_KEY', 'local', CURRENT_TIMESTAMP)"
    ), {"id": local_user_id})

    # -----------------------------------------------------------------------
    # 2. Add sync_id + deleted_at + user_id + timezone-aware dates to books
    # -----------------------------------------------------------------------
    with op.batch_alter_table("books") as batch_op:
        batch_op.add_column(sa.Column("sync_id", sa.Uuid(as_uuid=True), nullable=True))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.alter_column("created_at", type_=sa.DateTime(timezone=True), existing_nullable=False)
        batch_op.alter_column("updated_at", type_=sa.DateTime(timezone=True), existing_nullable=False)

    # Backfill sync_id for books
    for row in conn.execute(text("SELECT id FROM books")).fetchall():
        conn.execute(text("UPDATE books SET sync_id = :sid WHERE id = :id"),
                     {"sid": _new_uuid(), "id": row[0]})

    with op.batch_alter_table("books") as batch_op:
        batch_op.alter_column("sync_id", nullable=False)
        batch_op.create_unique_constraint("uq_books_sync_id", ["sync_id"])
        batch_op.create_index("ix_books_sync_id", ["sync_id"])
        batch_op.create_index("ix_books_updated_at", ["updated_at"])

    # -----------------------------------------------------------------------
    # 3. reviews — drop unique(book_id), add user_id FK, sync_id, is_public, deleted_at
    # -----------------------------------------------------------------------
    # SQLite names auto-generated unique constraints like sqlite_autoindex_reviews_N.
    # Find it via PRAGMA so we can pass the real name to drop_constraint inside the batch.
    book_id_unique_name = None
    if not postgres:
        for row in conn.execute(text("PRAGMA index_list(reviews)")).fetchall():
            idx_name = row[1]
            info = conn.execute(text(f'PRAGMA index_info("{idx_name}")')).fetchall()
            if len(info) == 1 and info[0][2] == "book_id":
                book_id_unique_name = idx_name
                break

    with op.batch_alter_table("reviews") as batch_op:
        if book_id_unique_name:
            batch_op.drop_constraint(book_id_unique_name, type_="unique")
        batch_op.add_column(sa.Column("sync_id", sa.Uuid(as_uuid=True), nullable=True))
        batch_op.add_column(sa.Column("user_id", sa.Integer, nullable=True))
        batch_op.add_column(sa.Column("is_public", sa.Boolean, nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.alter_column("created_at", type_=sa.DateTime(timezone=True), existing_nullable=False)
        batch_op.alter_column("updated_at", type_=sa.DateTime(timezone=True), existing_nullable=False)

    # Postgres: drop the named unique constraint explicitly (no batch mode)
    if postgres:
        op.drop_constraint("reviews_book_id_key", "reviews", type_="unique")

    # Backfill user_id and sync_id on reviews
    for row in conn.execute(text("SELECT id FROM reviews")).fetchall():
        conn.execute(
            text("UPDATE reviews SET user_id = :uid, sync_id = :sid WHERE id = :id"),
            {"uid": local_user_id, "sid": _new_uuid(), "id": row[0]},
        )

    with op.batch_alter_table("reviews") as batch_op:
        batch_op.alter_column("user_id", nullable=False)
        batch_op.alter_column("sync_id", nullable=False)
        batch_op.create_foreign_key("fk_reviews_user_id", "users", ["user_id"], ["id"], ondelete="CASCADE")
        batch_op.create_unique_constraint("uq_reviews_book_id_user_id", ["book_id", "user_id"])
        batch_op.create_unique_constraint("uq_reviews_sync_id", ["sync_id"])
        batch_op.create_index("ix_reviews_sync_id", ["sync_id"])
        batch_op.create_index("ix_reviews_user_id", ["user_id"])
        batch_op.create_index("ix_reviews_updated_at", ["updated_at"])

    # -----------------------------------------------------------------------
    # 4. shelves — drop unique(name), add user_id FK, sync_id, is_public, updated_at, deleted_at
    # -----------------------------------------------------------------------
    with op.batch_alter_table("shelves") as batch_op:
        batch_op.add_column(sa.Column("sync_id", sa.Uuid(as_uuid=True), nullable=True))
        batch_op.add_column(sa.Column("user_id", sa.Integer, nullable=True))
        batch_op.add_column(sa.Column("is_public", sa.Boolean, nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.alter_column("created_at", type_=sa.DateTime(timezone=True), existing_nullable=False)

    if postgres:
        op.drop_constraint("shelves_name_key", "shelves", type_="unique")

    # Backfill
    for row in conn.execute(text("SELECT id FROM shelves")).fetchall():
        conn.execute(
            text("UPDATE shelves SET user_id = :uid, sync_id = :sid, updated_at = CURRENT_TIMESTAMP WHERE id = :id"),
            {"uid": local_user_id, "sid": _new_uuid(), "id": row[0]},
        )

    with op.batch_alter_table("shelves") as batch_op:
        batch_op.alter_column("user_id", nullable=False)
        batch_op.alter_column("sync_id", nullable=False)
        batch_op.alter_column("updated_at", nullable=False)
        batch_op.create_foreign_key("fk_shelves_user_id", "users", ["user_id"], ["id"], ondelete="CASCADE")
        batch_op.create_unique_constraint("uq_shelves_user_id_name", ["user_id", "name"])
        batch_op.create_unique_constraint("uq_shelves_sync_id", ["sync_id"])
        batch_op.create_index("ix_shelves_sync_id", ["sync_id"])
        batch_op.create_index("ix_shelves_user_id", ["user_id"])
        batch_op.create_index("ix_shelves_updated_at", ["updated_at"])

    # -----------------------------------------------------------------------
    # 5. shelf_books — add sync_id, deleted_at, updated_at; timezone dates
    # -----------------------------------------------------------------------
    with op.batch_alter_table("shelf_books") as batch_op:
        batch_op.add_column(sa.Column("sync_id", sa.Uuid(as_uuid=True), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.alter_column("date_added", type_=sa.DateTime(timezone=True), existing_nullable=False)

    for row in conn.execute(text("SELECT id FROM shelf_books")).fetchall():
        conn.execute(
            text("UPDATE shelf_books SET sync_id = :sid, updated_at = CURRENT_TIMESTAMP WHERE id = :id"),
            {"sid": _new_uuid(), "id": row[0]},
        )

    with op.batch_alter_table("shelf_books") as batch_op:
        batch_op.alter_column("sync_id", nullable=False)
        batch_op.alter_column("updated_at", nullable=False)
        batch_op.create_unique_constraint("uq_shelf_books_sync_id", ["sync_id"])
        batch_op.create_index("ix_shelf_books_sync_id", ["sync_id"])
        batch_op.create_index("ix_shelf_books_updated_at", ["updated_at"])

    # -----------------------------------------------------------------------
    # 6. readings — add user_id FK, sync_id, deleted_at; timezone dates
    # -----------------------------------------------------------------------
    with op.batch_alter_table("readings") as batch_op:
        batch_op.add_column(sa.Column("sync_id", sa.Uuid(as_uuid=True), nullable=True))
        batch_op.add_column(sa.Column("user_id", sa.Integer, nullable=True))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.alter_column("created_at", type_=sa.DateTime(timezone=True), existing_nullable=False)
        batch_op.alter_column("updated_at", type_=sa.DateTime(timezone=True), existing_nullable=False)

    for row in conn.execute(text("SELECT id FROM readings")).fetchall():
        conn.execute(
            text("UPDATE readings SET user_id = :uid, sync_id = :sid WHERE id = :id"),
            {"uid": local_user_id, "sid": _new_uuid(), "id": row[0]},
        )

    with op.batch_alter_table("readings") as batch_op:
        batch_op.alter_column("user_id", nullable=False)
        batch_op.alter_column("sync_id", nullable=False)
        batch_op.create_foreign_key("fk_readings_user_id", "users", ["user_id"], ["id"], ondelete="CASCADE")
        batch_op.create_unique_constraint("uq_readings_sync_id", ["sync_id"])
        batch_op.create_index("ix_readings_sync_id", ["sync_id"])
        batch_op.create_index("ix_readings_user_id", ["user_id"])
        batch_op.create_index("ix_readings_updated_at", ["updated_at"])

    # -----------------------------------------------------------------------
    # 7. reading_progress — add sync_id, deleted_at, updated_at; timezone dates
    # -----------------------------------------------------------------------
    with op.batch_alter_table("reading_progress") as batch_op:
        batch_op.add_column(sa.Column("sync_id", sa.Uuid(as_uuid=True), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.alter_column("created_at", type_=sa.DateTime(timezone=True), existing_nullable=False)

    for row in conn.execute(text("SELECT id FROM reading_progress")).fetchall():
        conn.execute(
            text("UPDATE reading_progress SET sync_id = :sid, updated_at = CURRENT_TIMESTAMP WHERE id = :id"),
            {"sid": _new_uuid(), "id": row[0]},
        )

    with op.batch_alter_table("reading_progress") as batch_op:
        batch_op.alter_column("sync_id", nullable=False)
        batch_op.alter_column("updated_at", nullable=False)
        batch_op.create_unique_constraint("uq_reading_progress_sync_id", ["sync_id"])
        batch_op.create_index("ix_reading_progress_sync_id", ["sync_id"])
        batch_op.create_index("ix_reading_progress_updated_at", ["updated_at"])

    # -----------------------------------------------------------------------
    # 8. tags — add sync_id, updated_at, deleted_at, user_id, is_public;
    #           drop UNIQUE(name); add UNIQUE(user_id, name)
    # -----------------------------------------------------------------------
    with op.batch_alter_table("tags") as batch_op:
        batch_op.add_column(sa.Column("sync_id", sa.Uuid(as_uuid=True), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("user_id", sa.Integer, nullable=True))
        batch_op.add_column(sa.Column("is_public", sa.Boolean, nullable=False, server_default="1"))

    # Drop the old UNIQUE(name) constraint (only exists in postgres; SQLite batch recreate handles it)
    if postgres:
        op.drop_constraint("tags_name_key", "tags", type_="unique")

    for row in conn.execute(text("SELECT id FROM tags")).fetchall():
        conn.execute(
            text("UPDATE tags SET sync_id = :sid, updated_at = CURRENT_TIMESTAMP WHERE id = :id"),
            {"sid": _new_uuid(), "id": row[0]},
        )
    # Backfill: existing tags become public community tags (user_id=NULL, is_public=True)
    # user_id stays NULL (already set by server_default absence); is_public already defaulted to True

    with op.batch_alter_table("tags") as batch_op:
        batch_op.alter_column("sync_id", nullable=False)
        batch_op.alter_column("updated_at", nullable=False)
        batch_op.create_unique_constraint("uq_tags_sync_id", ["sync_id"])
        batch_op.create_unique_constraint("uq_tags_user_id_name", ["user_id", "name"])
        batch_op.create_index("ix_tags_sync_id", ["sync_id"])
        batch_op.create_index("ix_tags_updated_at", ["updated_at"])
        batch_op.create_index("ix_tags_user_id", ["user_id"])

    # -----------------------------------------------------------------------
    # 8b. book_tags — add user_id (attribution: who applied the tag)
    # -----------------------------------------------------------------------
    with op.batch_alter_table("book_tags") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer, nullable=True))

    # -----------------------------------------------------------------------
    # 9. user_books — create table and backfill from all book-touching entities
    # -----------------------------------------------------------------------
    op.create_table(
        "user_books",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("sync_id", sa.Uuid(as_uuid=True), nullable=False, unique=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("book_id", sa.Integer, sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "book_id", name="uq_user_books_user_id_book_id"),
    )
    op.create_index("ix_user_books_sync_id", "user_books", ["sync_id"])
    op.create_index("ix_user_books_user_id", "user_books", ["user_id"])
    op.create_index("ix_user_books_updated_at", "user_books", ["updated_at"])

    # Gather all (user_id, book_id, earliest_ts) pairs from reviews, shelf_books, and readings
    book_pairs = conn.execute(text("""
        SELECT user_id, book_id, MIN(ts) as first_ts FROM (
            SELECT user_id, book_id, created_at AS ts FROM reviews
            UNION ALL
            SELECT sh.user_id, sb.book_id, sb.date_added
              FROM shelf_books sb JOIN shelves sh ON sb.shelf_id = sh.id
            UNION ALL
            SELECT user_id, book_id, created_at FROM readings
        ) combined
        GROUP BY user_id, book_id
    """)).fetchall()

    for user_id, book_id, first_ts in book_pairs:
        from shelflife.id import make_id
        ub_id = make_id(user_id, book_id)
        conn.execute(text(
            "INSERT INTO user_books (id, sync_id, user_id, book_id, added_at, updated_at) "
            "VALUES (:id, :sid, :uid, :bid, :ts, :ts)"
        ), {"id": ub_id, "sid": _new_uuid(), "uid": user_id, "bid": book_id, "ts": first_ts})


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    postgres = _is_postgres()

    op.drop_table("user_books")

    with op.batch_alter_table("book_tags") as batch_op:
        batch_op.drop_column("user_id")

    with op.batch_alter_table("tags") as batch_op:
        batch_op.drop_index("ix_tags_user_id")
        batch_op.drop_index("ix_tags_updated_at")
        batch_op.drop_index("ix_tags_sync_id")
        batch_op.drop_constraint("uq_tags_user_id_name", type_="unique")
        batch_op.drop_constraint("uq_tags_sync_id", type_="unique")
        batch_op.drop_column("is_public")
        batch_op.drop_column("user_id")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("sync_id")
        batch_op.create_unique_constraint("uq_tags_name", ["name"])

    with op.batch_alter_table("reading_progress") as batch_op:
        batch_op.drop_index("ix_reading_progress_updated_at")
        batch_op.drop_index("ix_reading_progress_sync_id")
        batch_op.drop_constraint("uq_reading_progress_sync_id", type_="unique")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("sync_id")
        batch_op.alter_column("created_at", type_=sa.DateTime(), existing_nullable=False)

    with op.batch_alter_table("readings") as batch_op:
        batch_op.drop_index("ix_readings_updated_at")
        batch_op.drop_index("ix_readings_user_id")
        batch_op.drop_index("ix_readings_sync_id")
        batch_op.drop_constraint("uq_readings_sync_id", type_="unique")
        batch_op.drop_constraint("fk_readings_user_id", type_="foreignkey")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("user_id")
        batch_op.drop_column("sync_id")
        batch_op.alter_column("created_at", type_=sa.DateTime(), existing_nullable=False)
        batch_op.alter_column("updated_at", type_=sa.DateTime(), existing_nullable=False)

    with op.batch_alter_table("shelf_books") as batch_op:
        batch_op.drop_index("ix_shelf_books_updated_at")
        batch_op.drop_index("ix_shelf_books_sync_id")
        batch_op.drop_constraint("uq_shelf_books_sync_id", type_="unique")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("sync_id")
        batch_op.alter_column("date_added", type_=sa.DateTime(), existing_nullable=False)

    with op.batch_alter_table("shelves") as batch_op:
        batch_op.drop_index("ix_shelves_updated_at")
        batch_op.drop_index("ix_shelves_user_id")
        batch_op.drop_index("ix_shelves_sync_id")
        batch_op.drop_constraint("uq_shelves_sync_id", type_="unique")
        batch_op.drop_constraint("uq_shelves_user_id_name", type_="unique")
        batch_op.drop_constraint("fk_shelves_user_id", type_="foreignkey")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("is_public")
        batch_op.drop_column("user_id")
        batch_op.drop_column("sync_id")
        batch_op.alter_column("name", nullable=False, new_column_name="name")
        batch_op.create_unique_constraint("uq_shelves_name", ["name"])
        batch_op.alter_column("created_at", type_=sa.DateTime(), existing_nullable=False)

    with op.batch_alter_table("reviews") as batch_op:
        batch_op.drop_index("ix_reviews_updated_at")
        batch_op.drop_index("ix_reviews_user_id")
        batch_op.drop_index("ix_reviews_sync_id")
        batch_op.drop_constraint("uq_reviews_sync_id", type_="unique")
        batch_op.drop_constraint("uq_reviews_book_id_user_id", type_="unique")
        batch_op.drop_constraint("fk_reviews_user_id", type_="foreignkey")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("is_public")
        batch_op.drop_column("user_id")
        batch_op.drop_column("sync_id")
        batch_op.alter_column("book_id", nullable=False)
        batch_op.create_unique_constraint("uq_reviews_book_id", ["book_id"])
        batch_op.alter_column("created_at", type_=sa.DateTime(), existing_nullable=False)
        batch_op.alter_column("updated_at", type_=sa.DateTime(), existing_nullable=False)

    with op.batch_alter_table("books") as batch_op:
        batch_op.drop_index("ix_books_updated_at")
        batch_op.drop_index("ix_books_sync_id")
        batch_op.drop_constraint("uq_books_sync_id", type_="unique")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("sync_id")
        batch_op.alter_column("created_at", type_=sa.DateTime(), existing_nullable=False)
        batch_op.alter_column("updated_at", type_=sa.DateTime(), existing_nullable=False)

    op.drop_index("ix_users_api_key_hash", table_name="users")
    op.drop_table("users")
