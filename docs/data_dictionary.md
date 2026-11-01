\# Payment Reconciliation System

\# Database Data Dictionary



\## 1. Merchant



| Field | Data Type | Required | Constraints |

|---|---|---|---|

| merchant\_id | VARCHAR(30) | Yes | Primary Key |

| merchant\_name | VARCHAR(150) | Yes | Not Null |

| email | VARCHAR(150) | Yes | Unique |

| country | CHAR(2) | Yes | ISO country code |

| default\_currency | CHAR(3) | Yes | ISO currency code |

| status | VARCHAR(20) | Yes | ACTIVE, INACTIVE, SUSPENDED |

| created\_at | TIMESTAMP | Yes | Creation timestamp |

| updated\_at | TIMESTAMP | Yes | Last update timestamp |



\## 2. PaymentOrder



\*\*Purpose:\*\* Stores the original payment instructions created by customers for merchants.



| Field | Data Type | Required | Constraints / Validation |

|---|---|---|---|

| payment\_id | VARCHAR(30) | Yes | Primary Key; format PAY-2026-00000001 |

| merchant\_id | VARCHAR(30) | Yes | Foreign Key → Merchant.merchant\_id |

| customer\_reference | VARCHAR(50) | Yes | Synthetic customer reference; no real personal data |

| order\_reference | VARCHAR(60) | Yes | Unique; external payment reference |

| amount | NUMERIC(18,2) | Yes | Must be greater than 0; currency major units |

| currency | CHAR(3) | Yes | ISO 4217 currency code |

| payment\_method | VARCHAR(20) | Yes | CARD, UPI, NET\_BANKING, WALLET |

| status | VARCHAR(20) | Yes | CREATED, PENDING, PROCESSING, SUCCEEDED, FAILED, CANCELLED, EXPIRED, PARTIALLY\_REFUNDED, REFUNDED |

| created\_at | TIMESTAMP WITH TIME ZONE | Yes | Order creation timestamp |

| expires\_at | TIMESTAMP WITH TIME ZONE | No | Must be later than created\_at |

| updated\_at | TIMESTAMP WITH TIME ZONE | Yes | Last update timestamp |



\*\*Relationships:\*\*

\- Merchant → PaymentOrder: One-to-Many (1:N).

\- PaymentOrder → PaymentAttempt: One-to-Many (1:N).



\*\*Business Rules:\*\*

1\. Every payment order must belong to an existing merchant.

2\. Payment amount must be positive.

3\. Currency must be a valid ISO 4217 code.

4\. A payment order can have multiple attempts.

5\. A successful payment order must have at least one successfully captured attempt.

6\. Refund status must be derived from actual refund events and amounts, not randomly assigned.

7\. Previous status changes must be retained in event history.









\## 3. PaymentAttempt



\*\*Purpose:\*\* Stores individual payment processing attempts associated with a payment order.



| Field | Data Type | Required | Constraints / Validation |

|---|---|---|---|

| attempt\_id | VARCHAR(50) | Yes | Primary Key; ATT-<payment-id>-01 |

| payment\_id | VARCHAR(30) | Yes | Foreign Key → PaymentOrder.payment\_id |

| attempt\_number | SMALLINT | Yes | Must be greater than 0 |

| processor\_name | VARCHAR(50) | Yes | Processor identifier |

| processor\_reference | VARCHAR(100) | No | Processor-generated reference |

| attempt\_amount | NUMERIC(18,2) | Yes | Must be greater than 0 |

| currency | CHAR(3) | Yes | Must match PaymentOrder currency |

| status | VARCHAR(20) | Yes | INITIATED, PENDING, AUTHORIZED, CAPTURED, FAILED, CANCELLED, VOIDED |

| failure\_code | VARCHAR(50) | No | Required for failed attempts |

| failure\_reason | VARCHAR(255) | No | Failure description |

| initiated\_at | TIMESTAMP WITH TIME ZONE | Yes | Attempt initiation timestamp |

| completed\_at | TIMESTAMP WITH TIME ZONE | No | Must not precede initiated\_at |

| created\_at | TIMESTAMP WITH TIME ZONE | Yes | Record creation timestamp |

| updated\_at | TIMESTAMP WITH TIME ZONE | Yes | Last update timestamp |



\*\*Relationships:\*\*

\- PaymentOrder → PaymentAttempt: One-to-Many (1:N).

\- PaymentAttempt → ProcessorEvent: One-to-Many (1:N).

\- PaymentAttempt → SettlementLine: One-to-Many (1:N), optional.



\*\*Business Rules:\*\*

1\. Every attempt must reference an existing payment order.

2\. Attempt numbers must be sequential within a payment order.

3\. Each attempt must have a unique attempt ID.

4\. Attempt currency must match the parent payment order currency.

5\. Failed attempts must have a failure code.

6\. A captured attempt must have a corresponding successful capture event.

7\. Multiple attempts may exist for one payment order.

8\. A payment order must not be captured more than once for the same payable amount unless the business explicitly supports multiple captures.

9\. State transitions must be recorded in history rather than silently overwritten.

10\. Refunds must not be represented as failed attempts; they are separate processor events.





\## 4. ProcessorEvent



\*\*Purpose:\*\* Stores payment processor notifications and transaction lifecycle events. Maintains an immutable record of incoming processor events, including duplicate deliveries.



| Field | Data Type | Required | Constraints / Validation |

|---|---|---|---|

| event\_id | VARCHAR(50) | Yes | Primary Key; deterministic internal ID |

| attempt\_id | VARCHAR(50) | Yes | Foreign Key → PaymentAttempt.attempt\_id |

| payment\_id | VARCHAR(30) | Yes | Foreign Key → PaymentOrder.payment\_id |

| processor\_event\_id | VARCHAR(150) | Yes | External processor event identifier |

| processor\_name | VARCHAR(50) | Yes | Processor identifier |

| event\_type | VARCHAR(30) | Yes | PAYMENT\_AUTHORIZED, PAYMENT\_CAPTURED, PAYMENT\_FAILED, REFUND\_INITIATED, REFUND\_COMPLETED, PAYMENT\_VOIDED |

| event\_amount | NUMERIC(18,2) | Yes | Must be greater than 0 |

| currency | CHAR(3) | Yes | ISO 4217 currency code |

| event\_status | VARCHAR(20) | Yes | RECEIVED, PROCESSED, DUPLICATE, REJECTED |

| occurred\_at | TIMESTAMP WITH TIME ZONE | Yes | Actual event occurrence timestamp |

| received\_at | TIMESTAMP WITH TIME ZONE | Yes | Timestamp received by our system |

| processed\_at | TIMESTAMP WITH TIME ZONE | No | Timestamp processing completed |

| idempotency\_key | VARCHAR(200) | Yes | Unique processor + event identifier |

| duplicate\_of\_event\_id | VARCHAR(50) | No | Self-reference → ProcessorEvent.event\_id |

| payload\_hash | VARCHAR(64) | Yes | SHA-256 hash of normalized event payload |

| created\_at | TIMESTAMP WITH TIME ZONE | Yes | Record creation timestamp |



\*\*Relationships:\*\*

\- PaymentAttempt → ProcessorEvent: One-to-Many (1:N).

\- PaymentOrder → ProcessorEvent: One-to-Many (1:N).

\- ProcessorEvent → ProcessorEvent: Optional self-referencing relationship for duplicate tracking.



\*\*Business Rules:\*\*

1\. Every processor event must reference a valid payment order and payment attempt.

2\. The payment\_id in the event must match the payment\_id of its parent attempt.

3\. Processor event IDs must be unique within their processor namespace.

4\. Repeated delivery of the same processor event must not create a second financial effect.

5\. Duplicate deliveries must be recorded with DUPLICATE status and linked to the original event.

6\. Captured events must not exceed the authorized amount unless multiple captures are explicitly supported.

7\. Refund events must be associated with a previously captured transaction, even if the refund notification arrives before the capture notification.

8\. Event occurrence timestamps and receipt timestamps must be stored separately.

9\. Delayed and out-of-order events must be supported.

10\. Processor event history must remain immutable after ingestion.

11\. Event amounts and currencies must be validated against their parent transaction and processor rules.

12\. Only valid, successfully processed events may contribute to settlement calculations.







\## 5. SettlementBatch



\*\*Purpose:\*\* Represents a group of captured payment transactions and eligible refunds aggregated for settlement by a payment processor.



| Field | Data Type | Required | Constraints / Validation |

|---|---|---|---|

| batch\_id | VARCHAR(30) | Yes | Primary Key; format SET-2026-000001 |

| merchant\_id | VARCHAR(30) | Yes | Foreign Key → Merchant.merchant\_id |

| processor\_name | VARCHAR(50) | Yes | Processor identifier |

| settlement\_reference | VARCHAR(100) | Yes | Unique processor settlement reference |

| currency | CHAR(3) | Yes | ISO 4217 currency code |

| gross\_capture\_amount | NUMERIC(18,2) | Yes | Sum of eligible captured amounts |

| refund\_amount | NUMERIC(18,2) | Yes | Sum of eligible refunds; stored as positive amount |

| processing\_fee | NUMERIC(18,2) | Yes | Calculated processor fee; stored as positive amount |

| adjustment\_amount | NUMERIC(18,2) | Yes | Signed adjustments; positive or negative |

| net\_settlement\_amount | NUMERIC(18,2) | Yes | Gross captures - refunds - fees + adjustments |

| transaction\_count | INTEGER | Yes | Number of included transaction lines |

| settlement\_status | VARCHAR(20) | Yes | CREATED, PROCESSING, SETTLED, PARTIALLY\_SETTLED, FAILED |

| settlement\_date | DATE | Yes | Expected or actual settlement date |

| settlement\_window\_start | TIMESTAMP WITH TIME ZONE | Yes | Beginning of aggregation window |

| settlement\_window\_end | TIMESTAMP WITH TIME ZONE | Yes | End of aggregation window |

| settled\_at | TIMESTAMP WITH TIME ZONE | No | Actual settlement completion timestamp |

| created\_at | TIMESTAMP WITH TIME ZONE | Yes | Batch creation timestamp |

| updated\_at | TIMESTAMP WITH TIME ZONE | Yes | Last update timestamp |



\*\*Relationships:\*\*

\- Merchant → SettlementBatch: One-to-Many (1:N).

\- SettlementBatch → SettlementLine: One-to-Many (1:N).

\- SettlementBatch → BankStatementLine: One-to-Many (1:N), optional through reconciliation evidence and references.



\*\*Business Rules:\*\*

1\. Every settlement batch must belong to an existing merchant.

2\. Each batch must have a valid processor and currency.

3\. A batch must contain eligible captured transactions or eligible refund transactions.

4\. Only successfully captured payments may contribute to gross capture amount.

5\. Refunds must be associated with previously captured transactions.

6\. Refund amounts must not exceed the remaining refundable captured amount.

7\. Processing fees must be calculated using configured processor fee rules.

8\. Net settlement amount must equal gross captures minus refunds minus fees plus signed adjustments.

9\. All settlement lines must match the batch merchant, processor and currency.

10\. Settlement batches must not silently include the same financial event more than once.

11\. Delayed transactions must be included in the appropriate settlement window according to configured cutoff rules.

12\. Settlement history must be retained; corrections must be recorded as adjustments or new records.

13\. A settled batch must have a valid settlement completion timestamp.

14\. Partial settlement must be represented explicitly rather than treating the entire batch as settled.

