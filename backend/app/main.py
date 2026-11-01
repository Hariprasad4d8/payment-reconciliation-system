
from datetime import datetime, timezone, date
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import Base, engine, get_db
from backend.app import models

from backend.app.schemas import (
    MerchantCreate,
    MerchantResponse,
    PaymentCreate,
    PaymentResponse,
    CaptureRequest,
    SettlementRequest,
    BankStatementCreate,
    ResolutionRequest
)


app = FastAPI(
    title="Payment Reconciliation System",
    version="1.0.0",
    description="Payment processing, settlement and reconciliation management API"
)


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)


# --------------------------------------------------
# HOME AND HEALTH
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Payment Reconciliation API is running",
        "database": "PostgreSQL connected"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# --------------------------------------------------
# MERCHANT APIs
# --------------------------------------------------

@app.post("/merchants", response_model=MerchantResponse)
def create_merchant(
    data: MerchantCreate,
    db: Session = Depends(get_db)
):
    existing = db.query(models.Merchant).filter(
        models.Merchant.merchant_id == data.merchant_id
    ).first()

    if existing:
        raise HTTPException(409, "Merchant already exists")

    existing_email = db.query(models.Merchant).filter(
        models.Merchant.email == data.email
    ).first()

    if existing_email:
        raise HTTPException(409, "Email already exists")

    now = datetime.now(timezone.utc)

    merchant = models.Merchant(
        **data.model_dump(),
        status="ACTIVE",
        created_at=now,
        updated_at=now
    )

    try:
        db.add(merchant)
        db.commit()
        db.refresh(merchant)
    except Exception:
        db.rollback()
        raise HTTPException(500, "Merchant creation failed")

    return merchant


@app.get("/merchants", response_model=list[MerchantResponse])
def get_merchants(db: Session = Depends(get_db)):
    return db.query(models.Merchant).all()


# --------------------------------------------------
# PAYMENT APIs
# --------------------------------------------------

@app.post("/payments", response_model=PaymentResponse)
def create_payment(
    data: PaymentCreate,
    db: Session = Depends(get_db)
):
    merchant = db.query(models.Merchant).filter(
        models.Merchant.merchant_id == data.merchant_id
    ).first()

    if not merchant:
        raise HTTPException(404, "Merchant not found")

    if merchant.status != "ACTIVE":
        raise HTTPException(400, "Merchant is not active")

    existing = db.query(models.PaymentOrder).filter(
        models.PaymentOrder.payment_id == data.payment_id
    ).first()

    if existing:
        raise HTTPException(409, "Payment already exists")

    existing_order = db.query(models.PaymentOrder).filter(
        models.PaymentOrder.order_reference == data.order_reference
    ).first()

    if existing_order:
        raise HTTPException(409, "Order reference already exists")

    now = datetime.now(timezone.utc)

    payment = models.PaymentOrder(
        **data.model_dump(),
        status="CREATED",
        created_at=now,
        updated_at=now
    )

    try:
        db.add(payment)
        db.commit()
        db.refresh(payment)
    except Exception:
        db.rollback()
        raise HTTPException(500, "Payment creation failed")

    return payment


@app.get("/payments", response_model=list[PaymentResponse])
def get_payments(db: Session = Depends(get_db)):
    return db.query(models.PaymentOrder).all()


# --------------------------------------------------
# PAYMENT CAPTURE API
# --------------------------------------------------

@app.post("/payments/{payment_id}/capture")
def capture_payment(
    payment_id: str,
    data: CaptureRequest,
    db: Session = Depends(get_db)
):
    payment = db.query(models.PaymentOrder).filter(
        models.PaymentOrder.payment_id == payment_id
    ).first()

    if not payment:
        raise HTTPException(404, "Payment not found")

    if payment.status == "SUCCEEDED":
        raise HTTPException(409, "Payment already captured")

    attempt_id = f"ATT-{payment_id}-01"
    event_id = f"EVT-{payment_id}-CAPTURE-01"

    existing_attempt = db.query(models.PaymentAttempt).filter(
        models.PaymentAttempt.attempt_id == attempt_id
    ).first()

    if existing_attempt:
        raise HTTPException(409, "Payment attempt already exists")

    now = datetime.now(timezone.utc)

    attempt = models.PaymentAttempt(
        attempt_id=attempt_id,
        payment_id=payment.payment_id,
        attempt_number=1,
        processor_name=data.processor_name,
        processor_reference=data.processor_reference,
        attempt_amount=payment.amount,
        currency=payment.currency,
        status="CAPTURED",
        initiated_at=now,
        completed_at=now,
        created_at=now,
        updated_at=now
    )

    event = models.ProcessorEvent(
        event_id=event_id,
        attempt_id=attempt_id,
        payment_id=payment.payment_id,
        processor_event_id=data.processor_reference,
        processor_name=data.processor_name,
        event_type="PAYMENT_CAPTURED",
        event_amount=payment.amount,
        currency=payment.currency,
        event_status="PROCESSED",
        occurred_at=now,
        received_at=now,
        processed_at=now,
        idempotency_key=f"{data.processor_name}:{data.processor_reference}",
        payload_hash="DEMO_CAPTURE_EVENT",
        created_at=now
    )

    payment.status = "SUCCEEDED"
    payment.updated_at = now

    try:
        db.add(attempt)
        db.add(event)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(409, "Could not record payment capture")

    return {
        "message": "Payment captured successfully",
        "payment_id": payment_id,
        "attempt_id": attempt_id,
        "event_id": event_id,
        "amount": str(payment.amount),
        "currency": payment.currency,
        "payment_status": payment.status,
        "processor_event": "PAYMENT_CAPTURED"
    }


# --------------------------------------------------
# SETTLEMENT GENERATION API
# --------------------------------------------------

@app.post("/settlements/generate")
def generate_settlement(
    data: SettlementRequest,
    db: Session = Depends(get_db)
):
    merchant = db.query(models.Merchant).filter(
        models.Merchant.merchant_id == data.merchant_id
    ).first()

    if not merchant:
        raise HTTPException(404, "Merchant not found")

    captured_events = db.query(models.ProcessorEvent).join(
        models.PaymentOrder,
        models.ProcessorEvent.payment_id == models.PaymentOrder.payment_id
    ).filter(
        models.ProcessorEvent.event_type == "PAYMENT_CAPTURED",
        models.ProcessorEvent.event_status == "PROCESSED",
        models.PaymentOrder.merchant_id == data.merchant_id,
        models.ProcessorEvent.processor_name == data.processor_name,
        models.ProcessorEvent.currency == merchant.default_currency
    ).all()

    eligible_events = []

    for event in captured_events:
        existing_line = db.query(models.SettlementLine).filter(
            models.SettlementLine.event_id == event.event_id
        ).first()

        if not existing_line:
            eligible_events.append(event)

    if not eligible_events:
        raise HTTPException(
            400,
            "No unprocessed captured payments available for settlement"
        )

    gross_amount = sum(
        (event.event_amount for event in eligible_events),
        Decimal("0.00")
    )

    fee_amount = (
        gross_amount * data.fee_percentage / Decimal("100")
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    net_amount = gross_amount - fee_amount

    now = datetime.now(timezone.utc)
    batch_id = f"SET-{uuid4().hex[:12].upper()}"

    batch = models.SettlementBatch(
        batch_id=batch_id,
        merchant_id=data.merchant_id,
        processor_name=data.processor_name,
        settlement_reference=f"REF-{batch_id}",
        currency=merchant.default_currency,
        gross_capture_amount=gross_amount,
        refund_amount=Decimal("0.00"),
        processing_fee=fee_amount,
        adjustment_amount=Decimal("0.00"),
        net_settlement_amount=net_amount,
        transaction_count=len(eligible_events),
        settlement_status="CREATED",
        settlement_date=date.today(),
        settlement_window_start=min(
            event.occurred_at for event in eligible_events
        ),
        settlement_window_end=max(
            event.occurred_at for event in eligible_events
        ),
        created_at=now,
        updated_at=now
    )

    db.add(batch)

    for event in eligible_events:

        line_fee = (
            event.event_amount * data.fee_percentage / Decimal("100")
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        line = models.SettlementLine(
            settlement_line_id=f"SL-{uuid4().hex[:12].upper()}",
            batch_id=batch_id,
            payment_id=event.payment_id,
            attempt_id=event.attempt_id,
            event_id=event.event_id,
            line_type="CAPTURE",
            amount=event.event_amount,
            fee_amount=line_fee,
            net_amount=event.event_amount - line_fee,
            currency=event.currency,
            created_at=now
        )

        db.add(line)

    try:
        db.commit()
        db.refresh(batch)
    except Exception:
        db.rollback()
        raise HTTPException(500, "Settlement generation failed")

    return {
        "message": "Settlement batch generated successfully",
        "batch_id": batch.batch_id,
        "merchant_id": batch.merchant_id,
        "currency": batch.currency,
        "gross_amount": str(batch.gross_capture_amount),
        "processing_fee": str(batch.processing_fee),
        "net_settlement_amount": str(batch.net_settlement_amount),
        "transaction_count": batch.transaction_count,
        "status": batch.settlement_status
    }


# --------------------------------------------------
# BANK STATEMENT APIs
# --------------------------------------------------

@app.post("/bank-statements")
def create_bank_statement(
    data: BankStatementCreate,
    db: Session = Depends(get_db)
):
    merchant = db.query(models.Merchant).filter(
        models.Merchant.merchant_id == data.merchant_id
    ).first()

    if not merchant:
        raise HTTPException(404, "Merchant not found")

    existing = db.query(models.BankStatementLine).filter(
        models.BankStatementLine.bank_line_id == data.bank_line_id
    ).first()

    if existing:
        raise HTTPException(409, "Bank statement line already exists")

    bank_line = models.BankStatementLine(
        bank_line_id=data.bank_line_id,
        merchant_id=data.merchant_id,
        bank_reference=data.bank_reference,
        transaction_date=data.transaction_date,
        value_date=data.transaction_date.date(),
        description=data.description,
        amount=data.amount,
        currency=data.currency,
        transaction_type="CREDIT",
        imported_at=datetime.now(timezone.utc),
        source_file="demo_bank_statement.csv"
    )

    try:
        db.add(bank_line)
        db.commit()
        db.refresh(bank_line)
    except Exception:
        db.rollback()
        raise HTTPException(500, "Bank statement import failed")

    return {
        "message": "Bank statement imported successfully",
        "bank_line_id": bank_line.bank_line_id,
        "merchant_id": bank_line.merchant_id,
        "amount": str(bank_line.amount),
        "currency": bank_line.currency
    }


@app.get("/bank-statements")
def get_bank_statements(db: Session = Depends(get_db)):
    return db.query(models.BankStatementLine).all()


# --------------------------------------------------
# RECONCILIATION API
# --------------------------------------------------

@app.post("/reconciliation/{batch_id}/{bank_line_id}")
def reconcile_settlement(
    batch_id: str,
    bank_line_id: str,
    db: Session = Depends(get_db)
):
    batch = db.query(models.SettlementBatch).filter(
        models.SettlementBatch.batch_id == batch_id
    ).first()

    if not batch:
        raise HTTPException(404, "Settlement batch not found")

    bank_line = db.query(models.BankStatementLine).filter(
        models.BankStatementLine.bank_line_id == bank_line_id
    ).first()

    if not bank_line:
        raise HTTPException(404, "Bank statement line not found")

    if bank_line.merchant_id != batch.merchant_id:
        raise HTTPException(400, "Merchant mismatch")

    lines = db.query(models.SettlementLine).filter(
        models.SettlementLine.batch_id == batch_id
    ).all()

    if len(lines) != 1:
        raise HTTPException(
            400,
            "This demo currently supports one settlement line per batch"
        )

    line = lines[0]

    existing = db.query(models.ReconciliationMatch).filter(
        models.ReconciliationMatch.settlement_line_id == line.settlement_line_id,
        models.ReconciliationMatch.bank_line_id == bank_line_id
    ).first()

    if existing:
        raise HTTPException(409, "Already reconciled")

    now = datetime.now(timezone.utc)

    if line.currency != bank_line.currency:
        match_type = "CURRENCY_MISMATCH"
        match_status = "MISMATCHED"
        exception_type = "CURRENCY_MISMATCH"

    elif line.net_amount != bank_line.amount:
        match_type = "AMOUNT_MISMATCH"
        match_status = "MISMATCHED"
        exception_type = "AMOUNT_MISMATCH"

    else:
        match_type = "EXACT"
        match_status = "MATCHED"
        exception_type = None

    difference = bank_line.amount - line.net_amount

    match = models.ReconciliationMatch(
        match_id=f"MATCH-{uuid4().hex[:12].upper()}",
        settlement_line_id=line.settlement_line_id,
        bank_line_id=bank_line_id,
        match_type=match_type,
        match_status=match_status,
        expected_amount=line.net_amount,
        actual_amount=bank_line.amount,
        difference_amount=difference,
        confidence_score=(
            Decimal("100.00")
            if not exception_type
            else Decimal("0.00")
        ),
        matched_at=now,
        matching_rule="EXACT_AMOUNT_AND_CURRENCY"
    )

    try:
        db.add(match)
        db.flush()

        if exception_type:
            exception = models.ExceptionRecord(
                exception_id=f"EXC-{uuid4().hex[:12].upper()}",
                settlement_line_id=line.settlement_line_id,
                bank_line_id=bank_line_id,
                match_id=match.match_id,
                exception_type=exception_type,
                severity="HIGH",
                status="OPEN",
                description=(
                    f"Expected {line.net_amount} {line.currency}; "
                    f"received {bank_line.amount} {bank_line.currency}"
                ),
                detected_at=now,
                created_at=now
            )

            db.add(exception)

        db.commit()
        db.refresh(match)

    except Exception:
        db.rollback()
        raise HTTPException(500, "Reconciliation failed")

    return {
        "message": "Reconciliation completed",
        "match_id": match.match_id,
        "batch_id": batch_id,
        "bank_line_id": bank_line_id,
        "match_status": match_status,
        "match_type": match_type,
        "expected_amount": str(line.net_amount),
        "actual_amount": str(bank_line.amount),
        "difference": str(difference)
    }


# --------------------------------------------------
# EXCEPTION MANAGEMENT APIs
# --------------------------------------------------

@app.get("/exceptions")
def get_exceptions(db: Session = Depends(get_db)):

    exceptions = db.query(
        models.ExceptionRecord
    ).order_by(
        models.ExceptionRecord.detected_at.desc()
    ).all()

    return [
        {
            "exception_id": item.exception_id,
            "payment_id": item.payment_id,
            "settlement_line_id": item.settlement_line_id,
            "bank_line_id": item.bank_line_id,
            "match_id": item.match_id,
            "exception_type": item.exception_type,
            "severity": item.severity,
            "status": item.status,
            "description": item.description,
            "detected_at": item.detected_at
        }
        for item in exceptions
    ]


@app.get("/exceptions/{exception_id}")
def get_exception(
    exception_id: str,
    db: Session = Depends(get_db)
):
    item = db.query(models.ExceptionRecord).filter(
        models.ExceptionRecord.exception_id == exception_id
    ).first()

    if not item:
        raise HTTPException(404, "Exception not found")

    return {
        "exception_id": item.exception_id,
        "payment_id": item.payment_id,
        "settlement_line_id": item.settlement_line_id,
        "bank_line_id": item.bank_line_id,
        "match_id": item.match_id,
        "exception_type": item.exception_type,
        "severity": item.severity,
        "status": item.status,
        "description": item.description,
        "detected_at": item.detected_at
    }


@app.post("/exceptions/{exception_id}/resolve")
def resolve_exception(
    exception_id: str,
    data: ResolutionRequest,
    db: Session = Depends(get_db)
):
    exception = db.query(models.ExceptionRecord).filter(
        models.ExceptionRecord.exception_id == exception_id
    ).first()

    if not exception:
        raise HTTPException(404, "Exception not found")

    if exception.status == "RESOLVED":
        raise HTTPException(409, "Exception already resolved")

    now = datetime.now(timezone.utc)

    resolution = models.Resolution(
        resolution_id=f"RES-{uuid4().hex[:12].upper()}",
        exception_id=exception_id,
        resolution_type=data.resolution_type,
        resolution_notes=data.resolution_notes,
        resolved_by=data.resolved_by,
        resolved_at=now,
        created_at=now
    )

    exception.status = "RESOLVED"

    try:
        db.add(resolution)
        db.commit()
        db.refresh(resolution)
    except Exception:
        db.rollback()
        raise HTTPException(500, "Could not save exception resolution")

    return {
        "message": "Exception resolved successfully",
        "exception_id": exception_id,
        "resolution_id": resolution.resolution_id,
        "status": exception.status,
        "resolution_type": resolution.resolution_type,
        "resolved_by": resolution.resolved_by,
        "resolved_at": resolution.resolved_at
    }
