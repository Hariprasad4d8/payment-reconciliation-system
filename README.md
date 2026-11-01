\# Payment Reconciliation and Settlement Management System



\## 1. Project Overview



The Payment Reconciliation and Settlement Management System is a backend application designed to manage payment processing, settlement generation, bank statement imports, reconciliation, and exception resolution.



It uses FastAPI and PostgreSQL to maintain payment and settlement records and identify discrepancies between expected settlement amounts and actual bank credits.



\## 2. Technologies Used



\- \*\*Backend:\*\* Python, FastAPI

\- \*\*Database:\*\* PostgreSQL

\- \*\*ORM:\*\* SQLAlchemy

\- \*\*Validation:\*\* Pydantic

\- \*\*API Documentation:\*\* Swagger UI

\- \*\*Testing:\*\* Manual API testing through Swagger UI



\## 3. Core Features



\- Merchant creation and management

\- Payment order creation

\- Payment capture simulation

\- Processor event recording

\- Settlement batch generation

\- Processing fee calculation

\- Bank statement imports

\- Settlement and bank reconciliation

\- Duplicate reconciliation protection

\- Automatic exception detection

\- Exception resolution and tracking



\## 4. System Workflow



1\. Register a merchant.

2\. Create a payment order.

3\. Capture the payment through a simulated processor.

4\. Generate a settlement batch.

5\. Calculate processing fees and net settlement.

6\. Import the corresponding bank statement.

7\. Reconcile the settlement against the bank statement.

8\. Detect amount or currency mismatches.

9\. Create an exception for discrepancies.

10\. Record the resolution of an exception.



\## 5. Project Structure



```text

payment-reconciliation-system/

├── backend/

│   ├── app/

│   │   ├── models/

│   │   ├── schemas/

│   │   ├── routers/

│   │   ├── services/

│   │   ├── utils/

│   │   ├── database.py

│   │   ├── config.py

│   │   └── main.py

│   └── tests/

├── frontend/

├── data/

│   ├── generated/

│   ├── ground\_truth/

│   └── exports/

├── docs/

├── .env

├── .gitignore

└── README.md

```



\## 6. Installation and Setup



Clone the repository:



```bash

git clone YOUR\_GITHUB\_REPOSITORY\_URL

cd payment-reconciliation-system

```



Create and activate a virtual environment:



```bash

python -m venv venv

```



Windows:



```cmd

venv\\Scripts\\activate

```



Install dependencies:



```bash

pip install -r backend/requirements.txt

```



Configure PostgreSQL and create the database:



```sql

CREATE DATABASE payment\_reconciliation;

```



Configure the database connection in `.env`:



```env

DATABASE\_URL=postgresql+psycopg://postgres:YOUR\_PASSWORD@localhost:5432/payment\_reconciliation

```



Start the backend:



```bash

uvicorn backend.app.main:app --reload

```



\## 7. API Documentation



After starting the application, open:



\- Swagger UI: http://127.0.0.1:8000/docs

\- Health endpoint: http://127.0.0.1:8000/health



\### Implemented API Endpoints



| Method | Endpoint | Description |

|---|---|---|

| GET | `/` | Home |

| GET | `/health` | Health check |

| GET | `/merchants` | Get merchants |

| POST | `/merchants` | Create merchant |

| GET | `/payments` | Get payments |

| POST | `/payments` | Create payment |

| POST | `/payments/{payment\_id}/capture` | Capture payment |

| POST | `/settlements/generate` | Generate settlement |

| GET | `/bank-statements` | Get bank statements |

| POST | `/bank-statements` | Import bank statement |

| POST | `/reconciliation/{batch\_id}/{bank\_line\_id}` | Reconcile settlement |

| GET | `/exceptions` | Get exceptions |

| GET | `/exceptions/{exception\_id}` | Get exception details |

| POST | `/exceptions/{exception\_id}/resolve` | Resolve exception |



\## 8. Demonstrated Test Scenario



A payment of ₹1,000 was captured successfully.



Settlement calculation:



\- Gross amount: ₹1,000

\- Processing fee: 2%

\- Processing fee amount: ₹20

\- Expected settlement: ₹980



A bank statement containing ₹970 was imported.



The reconciliation engine detected:



\- Expected amount: ₹980

\- Actual amount: ₹970

\- Difference: ₹10

\- Exception type: `AMOUNT\_MISMATCH`

\- Severity: `HIGH`



The exception was subsequently resolved, and the API confirmed the status as `RESOLVED`.



\## 9. Current Implementation Scope



The current implementation demonstrates the core payment-to-settlement-to-reconciliation workflow through working API endpoints and PostgreSQL persistence.



The larger synthetic data generation requirements, all six specified anomaly scenarios, automated validation, and reproducibility checks remain future implementation work.



\## 10. Security Notes



\- Keep database credentials in `.env`.

\- Do not commit `.env` or other secrets to GitHub.

\- Use `.gitignore` to exclude virtual environments and generated temporary files.



\## 11. Future Enhancements



\- Large-scale synthetic transaction generation

\- Automated reconciliation rules

\- Additional anomaly detection scenarios

\- Automated test coverage

\- React-based frontend dashboard

\- CSV and JSON reporting

\- Settlement analytics and monitoring



