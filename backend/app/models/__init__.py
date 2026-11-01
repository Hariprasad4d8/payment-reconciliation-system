from sqlalchemy import (
    Column, String, Integer, SmallInteger, Numeric,
    DateTime, Date, ForeignKey, Boolean, Text,
    UniqueConstraint
)
from backend.app.database import Base


class Merchant(Base):
    __tablename__ = "merchants"

    merchant_id = Column(String(30), primary_key=True)
    merchant_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True)
    country = Column(String(2), nullable=False)
    default_currency = Column(String(3), nullable=False)
    status = Column(String(20), default="ACTIVE")
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))


class PaymentOrder(Base):
    __tablename__ = "payment_orders"

    payment_id = Column(String(30), primary_key=True)
    merchant_id = Column(String(30), ForeignKey("merchants.merchant_id"), nullable=False)
    customer_reference = Column(String(50))
    order_reference = Column(String(60), unique=True, nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    payment_method = Column(String(20), nullable=False)
    status = Column(String(30), default="CREATED")
    created_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"

    attempt_id = Column(String(50), primary_key=True)
    payment_id = Column(String(30), ForeignKey("payment_orders.payment_id"), nullable=False)
    attempt_number = Column(SmallInteger, nullable=False)
    processor_name = Column(String(50), nullable=False)
    processor_reference = Column(String(100))
    attempt_amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(String(20), default="INITIATED")
    failure_code = Column(String(50))
    failure_reason = Column(Text)
    initiated_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("payment_id", "attempt_number"),
    )


class ProcessorEvent(Base):
    __tablename__ = "processor_events"

    event_id = Column(String(50), primary_key=True)
    attempt_id = Column(String(50), ForeignKey("payment_attempts.attempt_id"), nullable=False)
    payment_id = Column(String(30), ForeignKey("payment_orders.payment_id"), nullable=False)
    processor_event_id = Column(String(150), nullable=False)
    processor_name = Column(String(50), nullable=False)
    event_type = Column(String(40), nullable=False)
    event_amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    event_status = Column(String(20), default="RECEIVED")
    occurred_at = Column(DateTime(timezone=True))
    received_at = Column(DateTime(timezone=True))
    processed_at = Column(DateTime(timezone=True))
    idempotency_key = Column(String(200), unique=True)
    duplicate_of_event_id = Column(
        String(50), ForeignKey("processor_events.event_id")
    )
    payload_hash = Column(String(64))
    created_at = Column(DateTime(timezone=True))


class SettlementBatch(Base):
    __tablename__ = "settlement_batches"

    batch_id = Column(String(30), primary_key=True)
    merchant_id = Column(String(30), ForeignKey("merchants.merchant_id"), nullable=False)
    processor_name = Column(String(50), nullable=False)
    settlement_reference = Column(String(100), unique=True, nullable=False)
    currency = Column(String(3), nullable=False)
    gross_capture_amount = Column(Numeric(18, 2), default=0)
    refund_amount = Column(Numeric(18, 2), default=0)
    processing_fee = Column(Numeric(18, 2), default=0)
    adjustment_amount = Column(Numeric(18, 2), default=0)
    net_settlement_amount = Column(Numeric(18, 2), nullable=False)
    transaction_count = Column(Integer, default=0)
    settlement_status = Column(String(30), default="CREATED")
    settlement_date = Column(Date)
    settlement_window_start = Column(DateTime(timezone=True))
    settlement_window_end = Column(DateTime(timezone=True))
    settled_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))


class SettlementLine(Base):
    __tablename__ = "settlement_lines"

    settlement_line_id = Column(String(50), primary_key=True)
    batch_id = Column(String(30), ForeignKey("settlement_batches.batch_id"), nullable=False)
    payment_id = Column(String(30), ForeignKey("payment_orders.payment_id"))
    attempt_id = Column(String(50), ForeignKey("payment_attempts.attempt_id"))
    event_id = Column(String(50), ForeignKey("processor_events.event_id"))
    line_type = Column(String(30), nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    fee_amount = Column(Numeric(18, 2), default=0)
    net_amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    created_at = Column(DateTime(timezone=True))


class BankStatementLine(Base):
    __tablename__ = "bank_statement_lines"

    bank_line_id = Column(String(50), primary_key=True)
    merchant_id = Column(String(30), ForeignKey("merchants.merchant_id"), nullable=False)
    bank_reference = Column(String(100), nullable=False)
    transaction_date = Column(DateTime(timezone=True))
    value_date = Column(Date)
    description = Column(Text)
    amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    transaction_type = Column(String(30))
    imported_at = Column(DateTime(timezone=True))
    source_file = Column(String(150))


class ReconciliationMatch(Base):
    __tablename__ = "reconciliation_matches"

    match_id = Column(String(50), primary_key=True)
    settlement_line_id = Column(
        String(50), ForeignKey("settlement_lines.settlement_line_id")
    )
    bank_line_id = Column(
        String(50), ForeignKey("bank_statement_lines.bank_line_id")
    )
    match_type = Column(String(30), nullable=False)
    match_status = Column(String(30), default="MATCHED")
    expected_amount = Column(Numeric(18, 2))
    actual_amount = Column(Numeric(18, 2))
    difference_amount = Column(Numeric(18, 2))
    confidence_score = Column(Numeric(5, 2))
    matched_at = Column(DateTime(timezone=True))
    matching_rule = Column(String(100))

    __table_args__ = (
        UniqueConstraint("settlement_line_id", "bank_line_id"),
    )


class ExceptionRecord(Base):
    __tablename__ = "exceptions"

    exception_id = Column(String(50), primary_key=True)
    payment_id = Column(String(30), ForeignKey("payment_orders.payment_id"))
    settlement_line_id = Column(
        String(50), ForeignKey("settlement_lines.settlement_line_id")
    )
    bank_line_id = Column(
        String(50), ForeignKey("bank_statement_lines.bank_line_id")
    )
    match_id = Column(
        String(50), ForeignKey("reconciliation_matches.match_id")
    )
    exception_type = Column(String(50), nullable=False)
    severity = Column(String(20), default="MEDIUM")
    status = Column(String(20), default="OPEN")
    description = Column(Text)
    detected_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True))


class Resolution(Base):
    __tablename__ = "resolutions"

    resolution_id = Column(String(50), primary_key=True)
    exception_id = Column(
        String(50), ForeignKey("exceptions.exception_id"), nullable=False
    )
    resolution_type = Column(String(50), nullable=False)
    resolution_notes = Column(Text)
    resolved_by = Column(String(100))
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True))