# Phase 6: Production Readiness

## Objective

Prepare the system for production deployment with security hardening, HIPAA compliance measures, audit logging, performance optimization, and deployment infrastructure.

## Prerequisites

- Phases 1-5 completed
- Understanding of HIPAA requirements
- Cloud infrastructure access (when ready for deployment)

## HIPAA Compliance Overview

### HIPAA Requirements for Software

| Requirement | Description | Our Implementation |
|-------------|-------------|-------------------|
| Access Controls | Limit access to PHI | Role-based access, JWT auth |
| Audit Controls | Track access to PHI | Comprehensive audit logging |
| Integrity Controls | Protect PHI from alteration | Data validation, checksums |
| Transmission Security | Encrypt data in transit | TLS 1.3 everywhere |
| Encryption | Encrypt data at rest | Database encryption, encrypted backups |
| Authentication | Verify user identity | MFA, session management |
| Automatic Logoff | Session timeout | Configurable session expiry |

### Business Associate Agreement (BAA)

You will need BAAs with:
- Cloud provider (AWS, GCP, Azure)
- VAPI (voice platform)
- OpenRouter (LLM provider)
- Any other third-party services touching PHI

## Deliverables

### 6.1 Extended Project Structure

```
src/
├── security/                    # Security infrastructure
│   ├── __init__.py
│   ├── encryption.py            # Field-level encryption
│   ├── audit.py                 # Audit logging
│   ├── rbac.py                  # Role-based access control
│   └── compliance.py            # Compliance checks
│
├── middleware/                  # Security middleware
│   ├── __init__.py
│   ├── rate_limit.py            # Rate limiting
│   ├── audit_middleware.py      # Request audit logging
│   └── security_headers.py      # Security headers
│
└── monitoring/                  # Production monitoring
    ├── __init__.py
    ├── health.py                # Health checks
    ├── metrics.py               # Prometheus metrics
    └── alerts.py                # Alert triggers

# Infrastructure
infra/
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.prod.yml
│
├── kubernetes/                  # K8s manifests (if using)
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── secrets.yaml
│
└── terraform/                   # Infrastructure as Code
    ├── main.tf
    ├── variables.tf
    ├── rds.tf
    ├── ecs.tf
    └── secrets.tf
```

### 6.2 Database Schema Extensions

```sql
-- Audit log table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Who
    user_id UUID,
    user_type VARCHAR(20),  -- 'clinician', 'system', 'admin'
    user_email VARCHAR(255),
    ip_address INET,
    user_agent TEXT,

    -- What
    action VARCHAR(100) NOT NULL,
    -- Actions: 'read', 'create', 'update', 'delete', 'export', 'login', 'logout'

    resource_type VARCHAR(50) NOT NULL,
    -- Types: 'patient', 'session', 'transcript', 'note', 'hypothesis'

    resource_id UUID,
    resource_details JSONB,  -- Relevant resource info at time of action

    -- Changes (for update actions)
    previous_values JSONB,
    new_values JSONB,

    -- Context
    request_id UUID,  -- Correlation ID
    session_id VARCHAR(255),  -- Login session
    endpoint VARCHAR(255),

    -- Result
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,

    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Access tokens (for session management)
CREATE TABLE access_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinician_id UUID REFERENCES clinicians(id) ON DELETE CASCADE,

    -- Token info
    token_hash VARCHAR(255) NOT NULL,  -- Hashed token
    token_type VARCHAR(20) DEFAULT 'access',  -- 'access', 'refresh'

    -- Metadata
    device_info JSONB,
    ip_address INET,

    -- Validity
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoke_reason VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE
);

-- Data export logs (for compliance)
CREATE TABLE data_exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinician_id UUID REFERENCES clinicians(id),

    -- What was exported
    export_type VARCHAR(50) NOT NULL,  -- 'patient_data', 'notes', 'transcripts'
    patient_id UUID REFERENCES patients(id),
    date_range_start DATE,
    date_range_end DATE,

    -- Export details
    format VARCHAR(20),  -- 'json', 'csv', 'pdf', 'hl7'
    record_count INTEGER,
    file_hash VARCHAR(64),

    -- Purpose (for compliance)
    purpose VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for audit queries
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_time ON audit_logs(created_at);
CREATE INDEX idx_tokens_clinician ON access_tokens(clinician_id);
CREATE INDEX idx_tokens_expires ON access_tokens(expires_at);
```

### 6.3 Field-Level Encryption

```python
# src/security/encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from src.config import get_settings

class FieldEncryption:
    """
    Field-level encryption for sensitive PHI fields.

    Encrypted fields:
    - Patient names
    - Contact information
    - Transcript content
    - Clinical notes
    """

    def __init__(self):
        settings = get_settings()
        self.key = self._derive_key(settings.encryption_key)
        self.fernet = Fernet(self.key)

    def _derive_key(self, master_key: str) -> bytes:
        """Derive encryption key from master key."""
        salt = os.environ.get("ENCRYPTION_SALT", "default-salt").encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return key

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string value."""
        if not plaintext:
            return plaintext
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string value."""
        if not ciphertext:
            return ciphertext
        return self.fernet.decrypt(ciphertext.encode()).decode()

    def encrypt_dict(self, data: dict, fields: list[str]) -> dict:
        """Encrypt specified fields in a dictionary."""
        result = data.copy()
        for field in fields:
            if field in result and result[field]:
                result[field] = self.encrypt(str(result[field]))
        return result

    def decrypt_dict(self, data: dict, fields: list[str]) -> dict:
        """Decrypt specified fields in a dictionary."""
        result = data.copy()
        for field in fields:
            if field in result and result[field]:
                result[field] = self.decrypt(result[field])
        return result


# SQLAlchemy type for encrypted fields
from sqlalchemy import TypeDecorator, String

class EncryptedString(TypeDecorator):
    """SQLAlchemy type that automatically encrypts/decrypts."""

    impl = String
    cache_ok = True

    def __init__(self, length=None):
        super().__init__(length=length)
        self.encryption = FieldEncryption()

    def process_bind_param(self, value, dialect):
        if value is not None:
            return self.encryption.encrypt(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return self.encryption.decrypt(value)
        return value


# Usage in models:
# class Patient(Base):
#     first_name = Column(EncryptedString(100))
#     last_name = Column(EncryptedString(100))
#     email = Column(EncryptedString(255))
```

### 6.4 Audit Logging

```python
# src/security/audit.py
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.audit import AuditLog
from contextvars import ContextVar

# Context variable for request tracking
request_context: ContextVar[dict] = ContextVar("request_context", default={})

class AuditLogger:
    """
    Comprehensive audit logging for HIPAA compliance.

    Logs:
    - All access to PHI
    - All modifications
    - Authentication events
    - Data exports
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        resource_details: Optional[dict] = None,
        previous_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """Log an auditable event."""
        ctx = request_context.get()

        log_entry = AuditLog(
            user_id=user_id or ctx.get("user_id"),
            user_type=ctx.get("user_type", "system"),
            user_email=ctx.get("user_email"),
            ip_address=ctx.get("ip_address"),
            user_agent=ctx.get("user_agent"),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_details=self._sanitize_for_log(resource_details),
            previous_values=self._sanitize_for_log(previous_values),
            new_values=self._sanitize_for_log(new_values),
            request_id=ctx.get("request_id"),
            session_id=ctx.get("session_id"),
            endpoint=ctx.get("endpoint"),
            success=success,
            error_message=error_message
        )

        self.db.add(log_entry)
        await self.db.commit()

    def _sanitize_for_log(self, data: Optional[dict]) -> Optional[dict]:
        """Remove sensitive fields before logging."""
        if not data:
            return None

        sensitive_fields = {
            "password", "password_hash", "token", "secret",
            "credit_card", "ssn", "social_security"
        }

        sanitized = {}
        for key, value in data.items():
            if key.lower() in sensitive_fields:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_for_log(value)
            else:
                sanitized[key] = value

        return sanitized

    async def log_read(
        self,
        resource_type: str,
        resource_id: UUID,
        details: dict = None
    ):
        """Log a read access event."""
        await self.log(
            action="read",
            resource_type=resource_type,
            resource_id=resource_id,
            resource_details=details
        )

    async def log_create(
        self,
        resource_type: str,
        resource_id: UUID,
        new_values: dict
    ):
        """Log a create event."""
        await self.log(
            action="create",
            resource_type=resource_type,
            resource_id=resource_id,
            new_values=new_values
        )

    async def log_update(
        self,
        resource_type: str,
        resource_id: UUID,
        previous_values: dict,
        new_values: dict
    ):
        """Log an update event."""
        await self.log(
            action="update",
            resource_type=resource_type,
            resource_id=resource_id,
            previous_values=previous_values,
            new_values=new_values
        )

    async def log_delete(
        self,
        resource_type: str,
        resource_id: UUID,
        previous_values: dict = None
    ):
        """Log a delete event."""
        await self.log(
            action="delete",
            resource_type=resource_type,
            resource_id=resource_id,
            previous_values=previous_values
        )

    async def log_export(
        self,
        resource_type: str,
        patient_id: UUID,
        format: str,
        record_count: int,
        purpose: str = None
    ):
        """Log a data export event."""
        await self.log(
            action="export",
            resource_type=resource_type,
            resource_id=patient_id,
            resource_details={
                "format": format,
                "record_count": record_count,
                "purpose": purpose
            }
        )

    async def log_auth(
        self,
        action: str,  # 'login', 'logout', 'login_failed', 'password_reset'
        user_id: UUID = None,
        user_email: str = None,
        success: bool = True,
        error_message: str = None
    ):
        """Log authentication events."""
        await self.log(
            action=action,
            resource_type="authentication",
            resource_id=user_id,
            resource_details={"email": user_email},
            success=success,
            error_message=error_message
        )
```

### 6.5 Audit Middleware

```python
# src/middleware/audit_middleware.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from uuid import uuid4
from src.security.audit import request_context

class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to set up audit context for each request.
    """

    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid4())

        # Extract user info from token (if authenticated)
        user_info = await self._extract_user_info(request)

        # Set context
        ctx = {
            "request_id": request_id,
            "user_id": user_info.get("user_id"),
            "user_type": user_info.get("user_type"),
            "user_email": user_info.get("email"),
            "ip_address": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "endpoint": f"{request.method} {request.url.path}",
            "session_id": request.cookies.get("session_id")
        }
        request_context.set(ctx)

        # Add request ID to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response

    async def _extract_user_info(self, request: Request) -> dict:
        """Extract user info from JWT token."""
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return {}

        try:
            from jose import jwt
            from src.config import get_settings
            settings = get_settings()

            token = auth_header.split(" ")[1]
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm]
            )
            return {
                "user_id": payload.get("sub"),
                "user_type": payload.get("type", "clinician"),
                "email": payload.get("email")
            }
        except:
            return {}

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP, accounting for proxies."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else None
```

### 6.6 Role-Based Access Control

```python
# src/security/rbac.py
from enum import Enum
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status

class Role(str, Enum):
    ADMIN = "admin"
    CLINICIAN = "clinician"
    SUPERVISOR = "supervisor"
    READONLY = "readonly"

class Permission(str, Enum):
    # Patient permissions
    PATIENT_READ = "patient:read"
    PATIENT_CREATE = "patient:create"
    PATIENT_UPDATE = "patient:update"
    PATIENT_DELETE = "patient:delete"

    # Session permissions
    SESSION_READ = "session:read"
    SESSION_CREATE = "session:create"

    # Note permissions
    NOTE_READ = "note:read"
    NOTE_CREATE = "note:create"
    NOTE_UPDATE = "note:update"
    NOTE_FINALIZE = "note:finalize"

    # Export permissions
    EXPORT_DATA = "export:data"

    # Admin permissions
    ADMIN_USERS = "admin:users"
    ADMIN_AUDIT = "admin:audit"
    ADMIN_SETTINGS = "admin:settings"

# Role-permission mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: [p for p in Permission],  # All permissions
    Role.SUPERVISOR: [
        Permission.PATIENT_READ,
        Permission.PATIENT_CREATE,
        Permission.PATIENT_UPDATE,
        Permission.SESSION_READ,
        Permission.SESSION_CREATE,
        Permission.NOTE_READ,
        Permission.NOTE_CREATE,
        Permission.NOTE_UPDATE,
        Permission.NOTE_FINALIZE,
        Permission.EXPORT_DATA,
        Permission.ADMIN_AUDIT,  # Can view audit logs
    ],
    Role.CLINICIAN: [
        Permission.PATIENT_READ,
        Permission.PATIENT_CREATE,
        Permission.PATIENT_UPDATE,
        Permission.SESSION_READ,
        Permission.SESSION_CREATE,
        Permission.NOTE_READ,
        Permission.NOTE_CREATE,
        Permission.NOTE_UPDATE,
        Permission.NOTE_FINALIZE,
    ],
    Role.READONLY: [
        Permission.PATIENT_READ,
        Permission.SESSION_READ,
        Permission.NOTE_READ,
    ],
}

class RBACService:
    """Role-based access control service."""

    def check_permission(
        self,
        user_role: Role,
        required_permission: Permission
    ) -> bool:
        """Check if a role has a permission."""
        role_perms = ROLE_PERMISSIONS.get(user_role, [])
        return required_permission in role_perms

    def require_permission(
        self,
        user_role: Role,
        required_permission: Permission
    ):
        """Raise exception if permission not granted."""
        if not self.check_permission(user_role, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {required_permission.value}"
            )

    async def check_patient_access(
        self,
        clinician_id: UUID,
        patient_id: UUID,
        db
    ) -> bool:
        """
        Check if clinician has access to a specific patient.

        Clinicians can only access their own patients unless supervisor.
        """
        from src.models.patient import Patient
        patient = await db.get(Patient, patient_id)

        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found"
            )

        # Check ownership
        if patient.clinician_id == clinician_id:
            return True

        # Check if supervisor (can access team patients)
        # Implementation depends on team structure
        return False


# FastAPI dependency for permission checking
from fastapi import Depends

def require_permission(permission: Permission):
    """Dependency to require a specific permission."""
    async def _require(
        current_user = Depends(get_current_clinician)
    ):
        rbac = RBACService()
        rbac.require_permission(current_user.role, permission)
        return current_user
    return _require

# Usage:
# @router.post("/patients")
# async def create_patient(
#     data: PatientCreate,
#     user = Depends(require_permission(Permission.PATIENT_CREATE))
# ):
```

### 6.7 Rate Limiting

```python
# src/middleware/rate_limit.py
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import time
from collections import defaultdict
import asyncio

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.

    Limits:
    - General API: 100 requests/minute per user
    - Authentication: 5 attempts/minute per IP
    - Voice sessions: 10/hour per patient
    - Data exports: 10/hour per clinician
    """

    def __init__(self, app):
        super().__init__(app)
        self.requests = defaultdict(list)
        self.limits = {
            "default": (100, 60),      # 100 per 60 seconds
            "auth": (5, 60),           # 5 per 60 seconds
            "session": (10, 3600),     # 10 per hour
            "export": (10, 3600),      # 10 per hour
        }

    async def dispatch(self, request: Request, call_next):
        # Determine rate limit category
        category = self._get_category(request.url.path)
        limit, window = self.limits.get(category, self.limits["default"])

        # Get identifier (user_id for authenticated, IP for auth endpoints)
        identifier = await self._get_identifier(request, category)
        key = f"{category}:{identifier}"

        # Check rate limit
        now = time.time()
        self._clean_old_requests(key, now - window)

        if len(self.requests[key]) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {window} seconds.",
                headers={"Retry-After": str(window)}
            )

        # Record request
        self.requests[key].append(now)

        return await call_next(request)

    def _get_category(self, path: str) -> str:
        """Determine rate limit category from path."""
        if "/auth/" in path:
            return "auth"
        if "/sessions" in path and "POST" in path:
            return "session"
        if "/export" in path:
            return "export"
        return "default"

    async def _get_identifier(self, request: Request, category: str) -> str:
        """Get identifier for rate limiting."""
        if category == "auth":
            # Use IP for auth endpoints
            return request.client.host if request.client else "unknown"

        # Try to get user ID from token
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from jose import jwt
                from src.config import get_settings
                settings = get_settings()
                token = auth_header.split(" ")[1]
                payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
                return payload.get("sub", request.client.host)
            except:
                pass

        return request.client.host if request.client else "unknown"

    def _clean_old_requests(self, key: str, cutoff: float):
        """Remove requests older than cutoff."""
        self.requests[key] = [
            ts for ts in self.requests[key] if ts > cutoff
        ]
```

### 6.8 Health Checks & Monitoring

```python
# src/monitoring/health.py
from fastapi import APIRouter
from datetime import datetime
import asyncio
from src.database import get_db
from src.config import get_settings

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check for monitoring.

    Checks:
    - Database connectivity
    - Redis connectivity (if used)
    - External service connectivity
    """
    checks = {}

    # Database check
    checks["database"] = await _check_database()

    # VAPI connectivity
    checks["vapi"] = await _check_vapi()

    # OpenRouter connectivity
    checks["openrouter"] = await _check_openrouter()

    # Overall status
    all_healthy = all(c["healthy"] for c in checks.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }

async def _check_database() -> dict:
    """Check database connectivity."""
    try:
        from sqlalchemy import text
        async for db in get_db():
            await db.execute(text("SELECT 1"))
            return {"healthy": True, "latency_ms": 0}
    except Exception as e:
        return {"healthy": False, "error": str(e)}

async def _check_vapi() -> dict:
    """Check VAPI connectivity."""
    try:
        import httpx
        settings = get_settings()
        async with httpx.AsyncClient() as client:
            start = datetime.now()
            response = await client.get(
                "https://api.vapi.ai/health",
                headers={"Authorization": f"Bearer {settings.vapi_api_key}"},
                timeout=5.0
            )
            latency = (datetime.now() - start).total_seconds() * 1000
            return {
                "healthy": response.status_code == 200,
                "latency_ms": round(latency)
            }
    except Exception as e:
        return {"healthy": False, "error": str(e)}

async def _check_openrouter() -> dict:
    """Check OpenRouter connectivity."""
    try:
        import httpx
        settings = get_settings()
        async with httpx.AsyncClient() as client:
            start = datetime.now()
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                timeout=5.0
            )
            latency = (datetime.now() - start).total_seconds() * 1000
            return {
                "healthy": response.status_code == 200,
                "latency_ms": round(latency)
            }
    except Exception as e:
        return {"healthy": False, "error": str(e)}


# Prometheus metrics
# src/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response

# Metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"]
)

ACTIVE_SESSIONS = Gauge(
    "active_voice_sessions",
    "Number of active voice sessions"
)

LLM_REQUESTS = Counter(
    "llm_requests_total",
    "Total LLM API requests",
    ["model", "status"]
)

LLM_LATENCY = Histogram(
    "llm_request_duration_seconds",
    "LLM request latency",
    ["model"]
)

@router.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

### 6.9 Docker Configuration

```dockerfile
# infra/docker/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# Copy application
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# infra/docker/docker-compose.yml
version: '3.8'

services:
  api:
    build:
      context: ../..
      dockerfile: infra/docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/clinical_copilot
      - SECRET_KEY=${SECRET_KEY}
      - VAPI_API_KEY=${VAPI_API_KEY}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=clinical_copilot
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
```

### 6.10 Security Headers

```python
# src/middleware/security_headers.py
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response


def configure_security(app: FastAPI):
    """Configure all security middleware."""
    from src.middleware.rate_limit import RateLimitMiddleware
    from src.middleware.audit_middleware import AuditMiddleware

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # CORS configuration
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://your-frontend-domain.com"],  # Configure appropriately
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
```

### 6.11 Configuration for Production

```python
# src/config.py (extended for production)
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Application
    app_name: str = "Longitudinal Clinical Copilot"
    environment: str = "development"  # development, staging, production
    debug: bool = False

    # Database
    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Security
    secret_key: str
    encryption_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # VAPI
    vapi_api_key: str
    vapi_phone_number_id: str
    vapi_webhook_secret: str

    # OpenRouter
    openrouter_api_key: str
    openrouter_model: str = "google/gemini-2.5-flash"

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 100

    # Audit
    audit_log_retention_days: int = 2555  # 7 years for HIPAA

    # Monitoring
    sentry_dsn: Optional[str] = None
    prometheus_enabled: bool = True

    # Session
    session_timeout_minutes: int = 30  # Auto-logout after inactivity

    class Config:
        env_file = ".env"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"
```

### 6.12 Deployment Checklist

```markdown
## Pre-Deployment Checklist

### Security
- [ ] All secrets in secure secret manager (not in code/env files)
- [ ] Database encryption at rest enabled
- [ ] TLS 1.3 configured for all connections
- [ ] Field-level encryption for PHI fields
- [ ] Rate limiting configured
- [ ] Security headers configured
- [ ] CORS properly restricted

### Compliance
- [ ] Audit logging enabled and tested
- [ ] Data retention policies configured
- [ ] BAAs signed with all vendors
- [ ] Privacy policy and ToS updated
- [ ] Consent flows implemented
- [ ] Data export functionality tested

### Infrastructure
- [ ] Database backups configured (daily + point-in-time)
- [ ] Database failover tested
- [ ] Load balancer health checks configured
- [ ] Auto-scaling configured
- [ ] Monitoring and alerting set up

### Testing
- [ ] Security penetration test completed
- [ ] Load testing completed
- [ ] Disaster recovery tested
- [ ] Rollback procedure documented and tested

### Documentation
- [ ] API documentation complete
- [ ] Runbook for common issues
- [ ] Incident response procedure documented
- [ ] On-call schedule established
```

## Acceptance Criteria

- [ ] Field-level encryption working for PHI
- [ ] Comprehensive audit logging in place
- [ ] Role-based access control implemented
- [ ] Rate limiting protecting all endpoints
- [ ] Security headers on all responses
- [ ] Health check endpoints working
- [ ] Prometheus metrics exposed
- [ ] Docker configuration tested
- [ ] All security middleware integrated
- [ ] Production configuration documented

## Post-Launch Monitoring

1. **Daily**: Review audit logs for anomalies
2. **Weekly**: Check error rates and latency metrics
3. **Monthly**: Review access patterns, rotate secrets
4. **Quarterly**: Security audit, penetration testing
5. **Annually**: Full compliance audit, BAA renewals

## Conclusion

Phase 6 completes the production-ready system. After this phase:

1. Deploy to staging environment
2. Conduct security audit
3. Beta test with select clinicians
4. Gradual rollout to production
5. Continuous monitoring and improvement
