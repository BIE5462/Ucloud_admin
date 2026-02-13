# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

云电脑容器管理系统 - A cloud PC container management system using UCloud GPU services.

**Three-tier Architecture:**
- **Backend**: FastAPI + SQLAlchemy + SQLite (async/await)
- **Admin Frontend**: Vue 3 + Vite + Element Plus + Pinia
- **Client**: PySide6 (Qt for Python) - desktop GUI for end users

**Core Concept**: Users get 1:1 cloud PC instances with per-minute billing, managed by admins.

## Development Commands

### Quick Start
```bash
# Install dependencies (Linux/Mac)
./install.sh

# Start services (Linux/Mac)
./start.sh           # Start frontend + backend
./start.sh frontend  # Frontend only (http://localhost:5173)
./start.sh backend   # Backend only (http://localhost:8000)
./start.sh client    # Client only
```

### Backend
```bash
cd backend
pip install -r requirements.txt
python run.py                    # Start dev server
python init_db.py                # Reset database (creates default admin: admin/admin123)
python init_db.py --keep-data    # Init without data loss
```

**API Documentation**: http://localhost:8000/docs (Swagger)

### Frontend
```bash
cd admin-frontend
npm install
npm run dev      # Dev server on port 5173
npm run build    # Production build
```

### Client
```bash
cd client
pip install -r requirements.txt
python main.py
```

### Code Quality
```bash
# Python linting and formatting (backend)
cd backend
ruff check .            # Check code
ruff check --fix .      # Auto-fix issues
ruff format .            # Format code

# Run tests
pytest test_api.py -v                           # Run all tests
pytest test_api.py::test_login -v                # Run single test
pytest test_api.py -k "container" -v             # Filter by name
```

## Architecture

### Backend (`backend/app/`)

**Layered Architecture:**
```
api/          # Route endpoints (controllers)
├── auth.py              # JWT authentication
├── container.py         # Cloud PC lifecycle
├── billing.py           # Billing & statistics
├── admin_*.py          # Admin management endpoints
core/         # Configuration & utilities
├── config.py            # Pydantic settings (env vars)
├── security.py         # JWT + password hashing (bcrypt)
└── utils.py           # Common utilities
db/           # Database
├── database.py         # Session management, async engine
└── models/            # SQLAlchemy models (declarative base)
services/     # Business logic layer
├── crud_service.py     # CRUD operations
├── ucloud_service.py  # UCloud API integration
tasks/        # Background jobs
└── scheduler.py        # APScheduler for per-minute billing
```

**Key Patterns:**
- **Async/await**: SQLAlchemy 2.0 async sessions
- **Dependency Injection**: FastAPI `Depends` for auth
- **Service Layer**: Business logic in `services/`, not in routes
- **Middleware**: Request ID logging, global exception handlers

**Database Models** (`backend/app/db/models/`):
- `m_admin` - Admin accounts (proxy mode, no direct ORM)
- `m_user` - End users (owned by admins)
- `container_record` - Cloud PC instances
- `system_config` - System settings (price per minute, etc.)
- `billing_charge_record` - Per-minute charge records
- `container_log` - Container operation logs
- `admin_operation_log` - Admin audit logs
- `balance_log` - Balance change logs

**Authentication Flow:**
1. User posts phone+password to `/api/auth/login`
2. Backend verifies bcrypt password hash
3. Returns JWT token (valid 1 day)
4. Client includes `Authorization: Bearer <token>` header

**Billing System:**
- APScheduler runs `charge_all_running_containers()` every 60 seconds
- Deducts `DEFAULT_PRICE_PER_MINUTE` (default: ¥0.5/min) from user balance
- Records charge in `billing_charge_record` table
- Users with insufficient balance get containers stopped automatically

### Frontend (`admin-frontend/src/`)

**Structure:**
```
api/          # Axios API clients
├── index.js            # Base axios instance with interceptors
└── modules/           # API endpoints grouped by feature
router/       # Vue Router routes
stores/       # Pinia state management
├── admin.js           # Admin auth & profile
└── user.js            # User data state
views/        # Page components
├── Dashboard.vue      # Stats cards + charts
├── UserList.vue       # User management (CRUD)
├── ContainerList.vue   # Container management
└── logs/             # Container logs & balance logs
```

**Key Conventions:**
- Use `@/` path alias for `src/`
- Pinia stores for state (not Vuex)
- Element Plus for UI components
- API calls return `{ code, message, data }` format
- Routes protected by `requireAuth()` meta field (check admin token)

### Client (`client/`)

**Desktop Application (PySide6):**
```
main.py              # Entry point (LoginDialog → MainWindow)
config.py            # ConfigManager (env vars + JSON file)
api/client.py         # APIClient class with auto-retry
utils/rdp_helper.py  # Windows RDP automation (cmdkey, mstsc)
```

**Features:**
- Login dialog → Main window with container management
- Auto-refresh status every 60 seconds when container running
- Windows: Auto-connects RDP via `mstsc.exe` with saved credentials
- macOS/Linux: Shows connection instructions
- Configuration via environment variables or JSON config file

**Config File Paths:**
- Windows: `%APPDATA%\CloudPCClient\config.json`
- macOS/Linux: `~/.config/cloudpc-client/config.json`

## Important Configuration

### Backend Settings (`backend/app/core/config.py`)
Set via environment variables or `.env` file:

```bash
# Required in production
SECRET_KEY=<your-secret-key>
UCLOUD_PUBLIC_KEY=<ucloud-key>
UCLOUD_PRIVATE_KEY=<ucloud-secret>

# Optional (with defaults)
DATABASE_URL=sqlite+aiosqlite:///./cloud_pc.db
DEBUG=True
DEFAULT_PRICE_PER_MINUTE=0.5
DEFAULT_MIN_BALANCE_TO_START=2.5
```

### Frontend Proxy (`admin-frontend/vite.config.js`)
- Dev server proxies `/api` to `http://localhost:8000`
- Production: Serve `dist/` with nginx and configure reverse proxy

### Client Configuration
```bash
API_BASE_URL=http://localhost:8000/api  # Backend API address
API_TIMEOUT=30                          # Request timeout (seconds)
RDP_AUTO_CONNECT=true                    # Auto-click RDP connect (Windows only)
LOG_LEVEL=INFO                          # Logging level
```

## Code Style

### Python
- **Indent**: 4 spaces
- **Quotes**: Double quotes
- **Linter**: Ruff (not flake8/black)
- **Type hints**: Required for function signatures
- **Import order**: stdlib → third-party → local (`app.*`)
- **Async**: Use `async/await` for all DB operations

### Vue/JavaScript
- **Indent**: 2 spaces
- **Quotes**: Single quotes
- **Style**: Composition API with `<script setup>`
- **State**: Pinia stores (`useAdminStore()`)
- **Component names**: PascalCase (`UserList.vue`)

## Common Tasks

### Adding a New API Endpoint
1. Create route in `backend/app/api/`
2. Implement business logic in `backend/app/services/`
3. Register router in `backend/app/main.py`
4. Add client method in `admin-frontend/src/api/modules/` or `client/api/client.py`
5. Test with `pytest test_api.py`

### Database Migration
```bash
# Modify models in backend/app/db/models/
# Then re-initialize (WARNING: destroys data)
cd backend
python init_db.py

# Or manually run SQL in cloud_pc.db
```

### Debugging
- Backend logs: `backend/server.log` or console output
- Frontend: Browser DevTools Network tab
- Client: `client/logs/client.log` or console

## Testing

### Test Files
- `test_api.py` - Authentication and container APIs
- `test_container_api.py` - Container lifecycle tests
- `test_delete_user.py` - User deletion with container cleanup
- `test_rdp_connection.py` - RDP connection tests

### Running Tests
```bash
cd backend  # or project root
pytest test_api.py -v              # Verbose output
pytest test_api.py -k "login"      # Run matching tests
pytest --tb=short test_api.py      # Shorter tracebacks
```

## Known Constraints

1. **Database**: SQLite for development (not production-ready for high concurrency)
2. **UCloud Integration**: Hardcoded GPU type and image ID
3. **Client**: Windows-only for auto-RDP (macOS/Linux show instructions)
4. **Authentication**: JWT tokens expire after 1 day (configurable)
5. **Billing**: Runs every 60 seconds via APScheduler (not exactly per-minute)

## Default Accounts

- **Super Admin**: `admin` / `admin123` (change immediately in production)
- **Admins**: Created by super admin via admin panel
- **Users**: Created by admins via admin panel

## Documentation References

- `AGENTS.md` - Detailed coding standards and conventions
- `client/DESIGN_DOC.md` - Client architecture and API specs
- `backend/INIT_DB_README.md` - Database initialization guide
- `README.md` - Project overview and quick start
