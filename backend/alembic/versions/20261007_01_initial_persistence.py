"""initial durable FinAgent persistence

Revision ID: 20261007_01
Revises:
Create Date: 2026-10-07
"""
from alembic import op
import sqlalchemy as sa

revision = "20261007_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users", sa.Column("id", sa.String(36), primary_key=True), sa.Column("email", sa.String(320), unique=True), sa.Column("display_name", sa.String(200)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("companies", sa.Column("symbol", sa.String(32), primary_key=True), sa.Column("name", sa.String(300)), sa.Column("exchange", sa.String(50)), sa.Column("sector", sa.String(150)), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("research_runs", sa.Column("id", sa.String(36), primary_key=True), sa.Column("company_symbol", sa.String(32), sa.ForeignKey("companies.symbol"), nullable=False), sa.Column("question", sa.Text(), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_research_runs_company_symbol", "research_runs", ["company_symbol"])
    op.create_table("research_reports", sa.Column("id", sa.String(36), primary_key=True), sa.Column("run_id", sa.String(36), sa.ForeignKey("research_runs.id"), unique=True, nullable=False), sa.Column("summary", sa.Text(), nullable=False), sa.Column("findings", sa.JSON(), nullable=False), sa.Column("warnings", sa.JSON(), nullable=False), sa.Column("activity", sa.JSON(), nullable=False), sa.Column("provenance", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("documents", sa.Column("id", sa.String(36), primary_key=True), sa.Column("name", sa.String(300), nullable=False), sa.Column("company_symbol", sa.String(32), sa.ForeignKey("companies.symbol")), sa.Column("content_type", sa.String(100), nullable=False), sa.Column("checksum", sa.String(64), unique=True, nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("ingestion_error", sa.Text()), sa.Column("metadata_json", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_documents_company_symbol", "documents", ["company_symbol"])
    op.create_index("ix_documents_checksum", "documents", ["checksum"])
    op.create_table("document_chunks", sa.Column("id", sa.String(36), primary_key=True), sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False), sa.Column("chunk_index", sa.Integer(), nullable=False), sa.Column("page_number", sa.Integer()), sa.Column("section", sa.String(500)), sa.Column("content", sa.Text(), nullable=False), sa.Column("vector_id", sa.String(64), unique=True, nullable=False))
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_table("portfolios", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id")), sa.Column("name", sa.String(200), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("holdings", sa.Column("id", sa.String(36), primary_key=True), sa.Column("portfolio_id", sa.String(36), sa.ForeignKey("portfolios.id"), nullable=False), sa.Column("company_symbol", sa.String(32), sa.ForeignKey("companies.symbol"), nullable=False), sa.Column("quantity", sa.Float(), nullable=False), sa.Column("average_price", sa.Float()))
    op.create_index("ix_holdings_portfolio_id", "holdings", ["portfolio_id"])
    op.create_table("data_source_metadata", sa.Column("id", sa.String(36), primary_key=True), sa.Column("company_symbol", sa.String(32), sa.ForeignKey("companies.symbol")), sa.Column("source", sa.String(100), nullable=False), sa.Column("data_type", sa.String(100), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False), sa.Column("data_timestamp", sa.DateTime(timezone=True)), sa.Column("payload", sa.JSON(), nullable=False))
    op.create_index("ix_data_source_metadata_company_symbol", "data_source_metadata", ["company_symbol"])


def downgrade() -> None:
    op.drop_table("data_source_metadata")
    op.drop_table("holdings")
    op.drop_table("portfolios")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("research_reports")
    op.drop_table("research_runs")
    op.drop_table("companies")
    op.drop_table("users")
