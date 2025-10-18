from datetime import datetime
from typing import List, Optional, Dict, Any
import asyncio
import json
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, BackgroundTasks, status, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from .database import get_engine, check_connection
from .migration_state import (
    get_migration_state_report,
    get_applied_migrations,
    get_pending_migrations,
    AppliedMigration,
    PendingMigration,
)
from .migration_executor import apply_pending_migrations, rollback_migrations
from .compliance_checker import check_compliance, ComplianceChecker, ComplianceViolationError
from .migration_loader import scan_migration_files, create_migration_file
from .schema_interceptor import enable_schema_interception, disable_schema_interception
from .ai_generator import generate_migration_with_ai, get_ai_generator


# ============================================================================
# Pydantic Models
# ============================================================================


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database_connected: bool
    message: Optional[str] = None


class MigrationStatusResponse(BaseModel):
    applied_count: int
    pending_count: int
    failed_count: int
    last_applied_version: Optional[str]
    last_applied_timestamp: Optional[datetime]
    is_compliant: bool


class AppliedMigrationResponse(BaseModel):
    version: str
    description: str
    applied_at: datetime
    checksum: str
    status: str
    execution_time: Optional[float]
    error_message: Optional[str]


class PendingMigrationResponse(BaseModel):
    version: str
    description: str
    file_path: str
    checksum: str
    file_type: str


class ComplianceViolationResponse(BaseModel):
    severity: str
    category: str
    message: str
    details: Dict[str, Any]


class ComplianceReportResponse(BaseModel):
    is_compliant: bool
    timestamp: datetime
    violation_count: int
    violations: List[ComplianceViolationResponse]
    recommendations: List[str]


class ApplyMigrationsRequest(BaseModel):
    dry_run: bool = False
    verbose: bool = False


class ApplyMigrationsResponse(BaseModel):
    successful: int
    failed: int
    errors: List[str]
    message: str


class RollbackRequest(BaseModel):
    count: int = Field(default=1, ge=1, description="Number of migrations to rollback")
    dry_run: bool = False
    verbose: bool = False


class CreateMigrationRequest(BaseModel):
    description: str = Field(..., min_length=1, description="Migration description")
    file_type: str = Field(default="sql", pattern="^(sql|py)$", description="Migration file type")


class CreateMigrationResponse(BaseModel):
    version: str
    filename: str
    file_path: str
    message: str


class AIGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Natural language description of migration")
    file_type: str = Field(default="sql", pattern="^(sql|py)$", description="Migration file type")
    include_context: bool = Field(default=True, description="Include database schema context")
    save_immediately: bool = Field(default=False, description="Save generated migration immediately")


class AIGenerateResponse(BaseModel):
    sql: str
    rollback_sql: Optional[str]
    confidence: float
    warnings: List[str]
    suggestions: List[str]
    description: str
    reasoning: Optional[str]
    saved: bool = False
    file_path: Optional[str] = None


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Database Migration Management API",
    description="Comprehensive API for managing database migrations with compliance enforcement",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


# ============================================================================
# Health & Status Endpoints
# ============================================================================


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Verifies database connectivity and system status.
    """
    try:
        check_connection()
        return HealthResponse(
            status="healthy", timestamp=datetime.utcnow(), database_connected=True, message="System operational"
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            database_connected=False,
            message=f"Database connection failed: {str(e)}",
        )


@app.get("/api/migrations/status", response_model=MigrationStatusResponse, tags=["Migrations"])
async def get_status():
    """
    Get current migration status.
    Returns summary of applied, pending, and failed migrations.
    """
    try:
        state_report = get_migration_state_report()

        return MigrationStatusResponse(
            applied_count=state_report.applied_count,
            pending_count=state_report.pending_count,
            failed_count=state_report.failed_count,
            last_applied_version=state_report.last_applied_version,
            last_applied_timestamp=state_report.last_applied_timestamp,
            is_compliant=state_report.is_compliant,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get migration status: {str(e)}"
        )


# ============================================================================
# Migration Query Endpoints
# ============================================================================


@app.get("/api/migrations/applied", response_model=List[AppliedMigrationResponse], tags=["Migrations"])
async def list_applied_migrations(limit: int = 100):
    """
    List all applied migrations.

    Args:
        limit: Maximum number of migrations to return (default: 100)
    """
    try:
        applied = get_applied_migrations()

        return [
            AppliedMigrationResponse(
                version=m.version,
                description=m.description,
                applied_at=m.applied_at,
                checksum=m.checksum,
                status=m.status,
                execution_time=m.execution_time,
                error_message=m.error_message,
            )
            for m in applied[:limit]
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get applied migrations: {str(e)}"
        )


@app.get("/api/migrations/pending", response_model=List[PendingMigrationResponse], tags=["Migrations"])
async def list_pending_migrations():
    """List all pending migrations."""
    try:
        pending = get_pending_migrations()

        return [
            PendingMigrationResponse(
                version=m.version,
                description=m.description,
                file_path=m.file_path,
                checksum=m.checksum,
                file_type=m.file_type,
            )
            for m in pending
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get pending migrations: {str(e)}"
        )


@app.get("/api/migrations/history", response_model=List[AppliedMigrationResponse], tags=["Migrations"])
async def get_migration_history(limit: int = 50):
    """
    Get migration history.

    Args:
        limit: Maximum number of migrations to return (default: 50)
    """
    return await list_applied_migrations(limit=limit)


# ============================================================================
# Migration Execution Endpoints
# ============================================================================


@app.post("/api/migrations/apply", response_model=ApplyMigrationsResponse, tags=["Migrations"])
async def apply_migrations(request: ApplyMigrationsRequest):
    """
    Apply all pending migrations sequentially.

    This endpoint executes migrations in order and stops on first failure.
    """
    try:
        successful, failed, errors = apply_pending_migrations(dry_run=request.dry_run, verbose=request.verbose)

        if failed > 0:
            return ApplyMigrationsResponse(
                successful=successful,
                failed=failed,
                errors=errors,
                message=f"Migration execution completed with {failed} failure(s)",
            )

        return ApplyMigrationsResponse(
            successful=successful,
            failed=failed,
            errors=errors,
            message=f"Successfully applied {successful} migration(s)",
        )

    except ComplianceViolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Compliance violation: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to apply migrations: {str(e)}"
        )


@app.post("/api/migrations/rollback", response_model=ApplyMigrationsResponse, tags=["Migrations"])
async def rollback_migration(request: RollbackRequest):
    """
    Rollback the last N migrations.

    Args:
        count: Number of migrations to rollback (default: 1)
    """
    try:
        successful, failed, errors = rollback_migrations(
            count=request.count, dry_run=request.dry_run, verbose=request.verbose
        )

        if failed > 0:
            return ApplyMigrationsResponse(
                successful=successful,
                failed=failed,
                errors=errors,
                message=f"Rollback completed with {failed} failure(s)",
            )

        return ApplyMigrationsResponse(
            successful=successful,
            failed=failed,
            errors=errors,
            message=f"Successfully rolled back {successful} migration(s)",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to rollback migrations: {str(e)}"
        )


@app.post("/api/migrations/create", response_model=CreateMigrationResponse, tags=["Migrations"])
async def create_migration(request: CreateMigrationRequest):
    """
    Create a new migration file.

    Args:
        description: Brief description of the migration
        file_type: Type of migration file (sql or py)
    """
    try:
        file_path = create_migration_file(description=request.description, file_type=request.file_type)

        # Extract version from filename
        import re

        match = re.match(r"^(\d{14})_", file_path.name)
        version = match.group(1) if match else "unknown"

        return CreateMigrationResponse(
            version=version,
            filename=file_path.name,
            file_path=str(file_path),
            message=f"Migration file created successfully",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create migration: {str(e)}"
        )


@app.post("/api/migrations/generate-ai", response_model=AIGenerateResponse, tags=["Migrations"])
async def generate_migration_ai(request: AIGenerateRequest):
    """
    Generate migration using AI from natural language description.

    Args:
        prompt: Natural language description (e.g., "Add email to users")
        file_type: 'sql' or 'py'
        include_context: Include current database schema for better suggestions
        save_immediately: If True, save the generated migration file

    Returns:
        Generated SQL/Python code with confidence score and suggestions
    """
    try:
        # Check if AI is available
        generator = get_ai_generator()
        if not generator.is_available():
            available_providers = generator.get_available_providers()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": "AI generation not available - no API keys configured",
                    "available_providers": available_providers,
                    "instructions": "Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable",
                },
            )

        # Generate migration
        result = generate_migration_with_ai(
            prompt=request.prompt, file_type=request.file_type, include_context=request.include_context
        )

        # Optionally save immediately
        file_path = None
        saved = False

        if request.save_immediately and result.confidence > 0.5:
            try:
                file_path_obj = create_migration_file(
                    description=result.description, content=result.sql, file_type=request.file_type
                )
                file_path = str(file_path_obj)
                saved = True
            except Exception as e:
                result.warnings.append(f"Could not save file: {str(e)}")

        return AIGenerateResponse(
            sql=result.sql,
            rollback_sql=result.rollback_sql,
            confidence=result.confidence,
            warnings=result.warnings,
            suggestions=result.suggestions,
            description=result.description,
            reasoning=result.reasoning,
            saved=saved,
            file_path=file_path,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate migration: {str(e)}"
        )


# ============================================================================
# Compliance Endpoints
# ============================================================================


@app.get("/api/compliance/report", response_model=ComplianceReportResponse, tags=["Compliance"])
async def get_compliance_report():
    """
    Get detailed compliance report.
    Shows all violations, recommendations, and compliance state.
    """
    try:
        report = check_compliance(verbose=False)

        violations = [
            ComplianceViolationResponse(severity=v.severity, category=v.category, message=v.message, details=v.details)
            for v in report.violations
        ]

        return ComplianceReportResponse(
            is_compliant=report.is_compliant,
            timestamp=report.timestamp,
            violation_count=report.violation_count,
            violations=violations,
            recommendations=report.recommendations,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to check compliance: {str(e)}"
        )


@app.get("/api/compliance/violations", response_model=List[ComplianceViolationResponse], tags=["Compliance"])
async def get_violations():
    """List all current compliance violations."""
    try:
        report = check_compliance(verbose=False)

        return [
            ComplianceViolationResponse(severity=v.severity, category=v.category, message=v.message, details=v.details)
            for v in report.violations
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get violations: {str(e)}"
        )


@app.post("/api/compliance/validate", response_model=ComplianceReportResponse, tags=["Compliance"])
async def validate_compliance():
    """
    Run compliance validation.
    Returns 403 Forbidden if violations detected, 200 OK if compliant.
    """
    try:
        checker = ComplianceChecker(verbose=False)
        report = checker.check_compliance()

        violations = [
            ComplianceViolationResponse(severity=v.severity, category=v.category, message=v.message, details=v.details)
            for v in report.violations
        ]

        response = ComplianceReportResponse(
            is_compliant=report.is_compliant,
            timestamp=report.timestamp,
            violation_count=report.violation_count,
            violations=violations,
            recommendations=report.recommendations,
        )

        if not report.is_compliant:
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=response.dict())

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to validate compliance: {str(e)}"
        )


@app.post("/api/compliance/enforce", tags=["Compliance"])
async def enforce_compliance():
    """
    Enforce compliance check.
    Blocks with 403 Forbidden if violations detected.
    """
    try:
        from .compliance_checker import enforce_migration_compliance

        enforce_migration_compliance(operation="API compliance check")

        return {"status": "compliant", "message": "No compliance violations detected"}

    except ComplianceViolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to enforce compliance: {str(e)}"
        )


# ============================================================================
# Schema Interceptor Endpoints
# ============================================================================


@app.post("/api/interceptor/enable", tags=["Interceptor"])
async def enable_interceptor():
    """Enable the schema modification interceptor."""
    try:
        enable_schema_interception(strict_mode=True)
        return {"status": "enabled", "message": "Schema interceptor enabled - DDL statements will be validated"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to enable interceptor: {str(e)}"
        )


@app.post("/api/interceptor/disable", tags=["Interceptor"])
async def disable_interceptor():
    """Disable the schema modification interceptor."""
    try:
        disable_schema_interception()
        return {"status": "disabled", "message": "Schema interceptor disabled - DDL statements will not be validated"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to disable interceptor: {str(e)}"
        )


# ============================================================================
# Real-time & Streaming Endpoints
# ============================================================================


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.

    Broadcasts:
    - Migration status changes
    - Compliance violations
    - Execution progress
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and send periodic updates
            state_report = get_migration_state_report()

            await websocket.send_json(
                {
                    "type": "status_update",
                    "data": {
                        "applied_count": state_report.applied_count,
                        "pending_count": state_report.pending_count,
                        "failed_count": state_report.failed_count,
                        "is_compliant": state_report.is_compliant,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }
            )

            await asyncio.sleep(5)  # Update every 5 seconds

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/stream/logs", tags=["Streaming"])
async def stream_migration_logs():
    """
    Server-Sent Events endpoint for streaming migration logs.
    """

    async def event_generator():
        while True:
            try:
                # Get latest migration status
                state_report = get_migration_state_report()

                event_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "applied_count": state_report.applied_count,
                    "pending_count": state_report.pending_count,
                    "is_compliant": state_report.is_compliant,
                }

                yield {"event": "status_update", "data": json.dumps(event_data)}

                await asyncio.sleep(2)

            except asyncio.CancelledError:
                break

    return EventSourceResponse(event_generator())


@app.post("/api/migrations/upload", tags=["Migrations"])
async def upload_migration_file(file: UploadFile = File(...), description: Optional[str] = None):
    """
    Upload a migration file directly.

    Args:
        file: SQL or Python migration file
        description: Optional description (will use filename if not provided)
    """
    try:
        from pathlib import Path
        import re

        # Validate file type
        if not file.filename.endswith((".sql", ".py")):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .sql and .py files are allowed")

        # Read file content
        content = await file.read()
        content_str = content.decode("utf-8")

        # Extract description from filename or use provided
        if not description:
            # Remove extension and timestamp if present
            desc_match = re.search(r"\d{14}_(.+)\.(sql|py)$", file.filename)
            if desc_match:
                description = desc_match.group(1)
            else:
                description = Path(file.filename).stem

        # Determine file type
        file_type = "py" if file.filename.endswith(".py") else "sql"

        # Create migration file
        file_path = create_migration_file(description=description, content=content_str, file_type=file_type)

        # Extract version from filename
        match = re.match(r"^(\d{14})_", file_path.name)
        version = match.group(1) if match else "unknown"

        return CreateMigrationResponse(
            version=version,
            filename=file_path.name,
            file_path=str(file_path),
            message="Migration file uploaded successfully",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to upload migration: {str(e)}"
        )


# ============================================================================
# Root Endpoint
# ============================================================================


@app.get("/", tags=["Root"])
async def root():
    """API root endpoint with information."""
    return {
        "name": "Database Migration Management API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/api/health",
            "migrations": "/api/migrations/*",
            "compliance": "/api/compliance/*",
            "websocket": "/ws",
            "streaming": "/api/stream/*",
        },
    }


# ============================================================================
# Application Startup
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    print("=" * 70)
    print("Database Migration Management API")
    print("=" * 70)
    print("Starting up...")

    try:
        check_connection()
        print("✓ Database connection established")
    except Exception as e:
        print(f"✗ Warning: Database connection failed: {e}")

    print("✓ API ready")
    print("=" * 70)


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    print("Shutting down...")


# ============================================================================
# Run API Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
