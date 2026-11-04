# MIS Master

MIS Master is a workforce reporting and analytics application for call-center operations. It uploads and validates Excel or CSV reports, imports the data into PostgreSQL, and presents dashboards, employee records, upload history, and role-based team views.

## Tech Stack

| Area | Technology |
| --- | --- |
| Backend | FastAPI, SQLAlchemy, Alembic, PostgreSQL |
| Authentication | JWT access and refresh tokens, bcrypt |
| Report processing | Pandas, OpenPyXL, xlrd |
| Frontend | React 19, TanStack Start and Router, Tailwind CSS |
| Charts and UI | Recharts, Radix UI, Lucide icons |

## Features

- Upload Excel and CSV workforce reports with validation and row-level error reporting
- Detect and process APR, shift adherence, shrinkage, and master database reports
- Monitor agent KPIs, attendance, call activity, adherence, and shrinkage
- Manage employees and user accounts
- Review upload history and import status
- Generate daily, weekly, and monthly MIS workbooks
- Restrict MANAGER and TL dashboards to their own teams
- Renew login sessions with access and refresh tokens

## Supported Report Types

| Report type | Data usage |
| --- | --- |
| `APR` | Daily agent performance and call breakdown |
| `SHIFT_ADHERENCE` | Shift attendance and adherence records |
| `SHRINKAGE` | Agent shrinkage records |
| `MASTER_DATABASE` | Employee master and manager/TL team relationships |

Report column definitions live in `backend/app/reports/registry.py`. Parser implementations live in `backend/app/parsers/` and must stay aligned with that registry.

## User Roles

| Role | Access |
| --- | --- |
| `ADMIN` | Full administrative access, user management, and all dashboard data |
| `MIS` | Report uploads, employee management, upload history, and all dashboard data |
| `MANAGER` | Dashboard data for employees assigned to the manager's team |
| `TL` | Dashboard data for employees assigned to the TL's team |

MANAGER and TL users must be linked to an employee record through the Employee ID field. The application matches that employee's name with the `manager_name` or `tl_name` fields in the employee master. Import the master database before creating or using team-scoped accounts.

If a MANAGER or TL user has no Employee ID or the ID cannot be found, the dashboard scope is intentionally empty. Dashboard scoping is implemented in `backend/app/services/dashboard.py` and is applied across dashboard endpoints.

## Project Structure

```text
MIS Master/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # FastAPI route handlers
│   │   ├── auth/             # Authentication, authorization, and rate limiting
│   │   ├── database/         # SQLAlchemy setup
│   │   ├── imports/          # Report import services
│   │   ├── models/           # Database models
│   │   ├── parsers/          # Workbook and CSV parsers
│   │   ├── reports/          # Report registry and workbook generation
│   │   ├── services/         # Dashboard and business logic
│   │   └── uploads/          # Upload processing
│   ├── alembic/              # Database migrations
│   ├── storage/              # Uploaded and generated files
│   └── tests/                # Backend pytest suite
├── frontend/
│   └── src/
│       ├── app/              # Application modules
│       ├── components/       # Shared UI components
│       ├── routes/           # TanStack routes and pages
│       ├── services/         # API client and services
│       └── shared/           # Shared frontend utilities
└── README.md
```

## Prerequisites

- Python 3.10 or newer
- PostgreSQL 14 or newer
- Bun 1.x or newer
- Windows PowerShell commands are shown below

## Backend Setup

1. Create the database:

   ```sql
   CREATE DATABASE mis_master;
   ```

2. Configure and start the backend:

   ```powershell
   cd backend
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install -r requirements-dev.txt
   Copy-Item .env.example .env
   ```

3. Edit `backend/.env` with your PostgreSQL credentials and a long random `APP_SECRET_KEY`. Then apply migrations:

   ```powershell
   alembic upgrade head
   ```

4. Create the first administrator:

   ```powershell
   python create_first_admin.py
   ```

5. Start the API server:

   ```powershell
   uvicorn app.main:app --reload
   ```

The API runs at `http://localhost:8000`. Interactive documentation is available at `http://localhost:8000/docs`.

### Database Migrations

Run migrations after pulling database changes:

```powershell
cd backend
alembic upgrade head
```

Migration files are stored in `backend/alembic/versions/`. Migration `0016` uses PostgreSQL's `pg_trgm` extension and requires the database role to have permission to create extensions.

## Frontend Setup

1. Install dependencies and start the development server:

   ```powershell
   cd frontend
   bun install
   bun run dev
   ```

2. Open the URL printed by Vite, normally `http://localhost:5173`.

Set `VITE_API_BASE_URL` when the backend is not available at `http://localhost:8000`, for example:

```powershell
$env:VITE_API_BASE_URL="http://localhost:8000"
```

## Configuration

The backend reads settings from `backend/.env`. Important settings include:

| Setting | Purpose | Default |
| --- | --- | --- |
| `APP_ENVIRONMENT` | Runtime environment | `development` |
| `APP_DEBUG` | Enables debug behavior | `true` |
| `APP_SECRET_KEY` | JWT signing secret | Change in every environment |
| `APP_DB_HOST` or `POSTGRES_SERVER` | PostgreSQL host | `localhost` |
| `APP_DB_PORT` or `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `APP_DB_USER` or `POSTGRES_USER` | PostgreSQL user | `postgres` |
| `APP_DB_PASSWORD` or `POSTGRES_PASSWORD` | PostgreSQL password | `postgres` |
| `APP_DB_NAME` or `POSTGRES_DB` | Database name | `mis_master` |
| `APP_CORS_ORIGINS` | Allowed frontend origins | Local Vite/Lovable origins |
| `APP_MAX_UPLOAD_SIZE_MB` | Maximum upload size | `25` |
| `APP_AUTO_PROCESS_UPLOADS` | Imports validated admin/MIS uploads automatically | `true` |
| `APP_AUTO_REPORTS_ENABLED` | Generates scheduled MIS workbooks | `true` |

Outside local/development environments, the backend rejects the placeholder secret, default database password, and debug mode. Do not use development defaults in production.

## Report Workflow

1. Upload a report from the Upload Reports page.
2. The backend stores the file, detects its type, and validates the required headers.
3. For auto-processing environments, valid ADMIN/MIS uploads are imported immediately.
4. Otherwise, use the Process action to call `POST /imports/{report_type}/{upload_id}`.
5. Review imported rows and validation errors in Upload History.
6. View the imported data through the dashboard endpoints and dashboard pages.

Dashboard periods use `YYYY-MM-DD` values through the `date_from` and `date_to` query parameters. Without dates, the dashboard uses the latest reporting day that contains data.

## Tests and Validation

Run backend tests:

```powershell
cd backend
python -m pytest
```

Run frontend lint and production build:

```powershell
cd frontend
bun run lint
bun run build
```

## Known Limitations

- Refresh tokens are stateless; logging out or changing a password does not revoke an already-issued refresh token before its configured expiry.
- Failed-login counts are stored in application memory and should use Redis when multiple backend workers are deployed.
- Uploaded and generated files are stored on local disk under `backend/storage/`; production deployments need a backup or object-storage strategy.
- There is currently no Docker setup, CI workflow, or frontend test suite.

## Lovable Development

The frontend is connected to Lovable. Keep pushed history intact: do not force push, amend published commits, squash shared history, or rewrite the connected branch. See `frontend/AGENTS.md` for repository-specific guidance.
