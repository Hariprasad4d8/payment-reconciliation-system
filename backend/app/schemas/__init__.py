
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class MerchantCreate(BaseModel):
    merchant_id: str
    merchant_name: str
    email: str
    country: str = Field(min_length=2, max_length=2)
    default_currency: str = Field(min_length=3, max_length=3)


class MerchantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    merchant_id: str
    merchant_name: str
    email: str
    country: str
    default_currency: str
    status: str


class PaymentCreate(BaseModel):
    payment_id: str
    merchant_id: str
    customer_reference: str
    order_reference: str
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    payment_method: str


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_id: str
    merchant_id: str
    order_reference: str
    amount: Decimal
    currency: str
    payment_method: str
    status: str

class CaptureRequest(BaseModel):
    processor_name: str = "DemoProcessor"
    processor_reference: str
class SettlementRequest(BaseModel):
    merchant_id: str
    processor_name: str = "DemoProcessor"
    fee_percentage: Decimal = Field(default=Decimal("2.00"), ge=0, le=100)

from datetime import datetime


class BankStatementCreate(BaseModel):
    bank_line_id: str
    merchant_id: str
    bank_reference: str
    transaction_date: datetime
    amount: Decimal
    currency: str = Field(min_length=3, max_length=3)
    description: str = "Settlement payout"
class ResolutionRequest(BaseModel):
    resolution_type: str
    resolution_notes: str
    resolved_by: str = "Admin"