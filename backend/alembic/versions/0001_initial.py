"""Initial Todo AI schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-30
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("roles", sa.Column("id", sa.Integer(), nullable=False), sa.Column("name", sa.String(50), nullable=False), sa.Column("description", sa.String(255)), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("name"))
    op.create_index("ix_roles_name", "roles", ["name"])
    op.create_table("users", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("email", sa.String(320), nullable=False), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("full_name", sa.String(120), nullable=False), sa.Column("timezone", sa.String(64), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("email"))
    op.create_index("ix_users_email", "users", ["email"]); op.create_index("ix_users_is_active", "users", ["is_active"])
    op.create_table("user_roles", sa.Column("user_id", sa.Uuid(), nullable=False), sa.Column("role_id", sa.Integer(), nullable=False), sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("user_id", "role_id"))
    op.create_table("refresh_tokens", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("user_id", sa.Uuid(), nullable=False), sa.Column("token_hash", sa.String(64), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("revoked_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("token_hash"))
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"]); op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"]); op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])
    op.create_table("categories", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("user_id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(80), nullable=False), sa.Column("color", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("user_id", "name", name="uq_categories_user_name")); op.create_index("ix_categories_user_id", "categories", ["user_id"])
    op.create_table("tags", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("user_id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(40), nullable=False), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("user_id", "name", name="uq_tags_user_name")); op.create_index("ix_tags_user_id", "tags", ["user_id"])
    op.create_table("todos", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("user_id", sa.Uuid(), nullable=False), sa.Column("category_id", sa.Uuid()), sa.Column("title", sa.String(200), nullable=False), sa.Column("description", sa.Text()), sa.Column("status", sa.String(20), nullable=False), sa.Column("priority", sa.String(20), nullable=False), sa.Column("due_at", sa.DateTime(timezone=True)), sa.Column("reminder_at", sa.DateTime(timezone=True)), sa.Column("reminder_sent_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    for column in ("user_id", "category_id", "title", "status", "priority", "due_at", "reminder_at"): op.create_index(f"ix_todos_{column}", "todos", [column])
    op.create_table("todo_tags", sa.Column("todo_id", sa.Uuid(), nullable=False), sa.Column("tag_id", sa.Uuid(), nullable=False), sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["todo_id"], ["todos.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("todo_id", "tag_id"))
    op.create_table("notifications", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("user_id", sa.Uuid(), nullable=False), sa.Column("todo_id", sa.Uuid()), sa.Column("title", sa.String(160), nullable=False), sa.Column("message", sa.Text(), nullable=False), sa.Column("kind", sa.String(40), nullable=False), sa.Column("is_read", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("read_at", sa.DateTime(timezone=True)), sa.ForeignKeyConstraint(["todo_id"], ["todos.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    for column in ("user_id", "todo_id", "is_read", "created_at"): op.create_index(f"ix_notifications_{column}", "notifications", [column])
    op.create_table("ai_conversations", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("user_id", sa.Uuid(), nullable=False), sa.Column("title", sa.String(160), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id")); op.create_index("ix_ai_conversations_user_id", "ai_conversations", ["user_id"])
    op.create_table("ai_messages", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("conversation_id", sa.Uuid(), nullable=False), sa.Column("role", sa.String(20), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id")); op.create_index("ix_ai_messages_conversation_id", "ai_messages", ["conversation_id"])
    op.create_table("audit_logs", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("actor_id", sa.Uuid()), sa.Column("action", sa.String(100), nullable=False), sa.Column("target_type", sa.String(60), nullable=False), sa.Column("target_id", sa.String(64)), sa.Column("details", sa.JSON()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"))
    for column in ("actor_id", "action", "created_at"): op.create_index(f"ix_audit_logs_{column}", "audit_logs", [column])


def downgrade() -> None:
    for table in ("audit_logs", "ai_messages", "ai_conversations", "notifications", "todo_tags", "todos", "tags", "categories", "refresh_tokens", "user_roles", "users", "roles"):
        op.drop_table(table)
