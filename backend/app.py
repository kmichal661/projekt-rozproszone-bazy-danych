import os
import sys
import logging
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, JSONResponse
from starlette_graphene3 import GraphQLApp

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = Path(os.getenv("TEST_REPORT_PATH", PROJECT_ROOT / "Tests" / "results" / "report.html"))

try:
    from .catalog_transaction import enabled as two_phase_commit_enabled
    from .catalog_transaction import recover_prepared_transactions
    from .helpers import graphiql
    from .schema import schema
except ImportError:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from backend.catalog_transaction import enabled as two_phase_commit_enabled
    from backend.catalog_transaction import recover_prepared_transactions
    from backend.helpers import graphiql
    from backend.schema import schema


logger = logging.getLogger(__name__)


async def recover_catalog_transactions():
    """Dokończ zatwierdzone transakcje 2PC po restarcie API."""
    if not two_phase_commit_enabled():
        return
    try:
        recover_prepared_transactions()
    except Exception:
        # API nadal może obsługiwać odczyty lokalne podczas awarii węzła.
        # Recovery zostanie ponowione przed następną zmianą katalogu.
        logger.exception("Nie udało się odzyskać przygotowanych transakcji katalogu")




async def health(request):
    return JSONResponse({"status": "ok", "service": "distributed-store"})


async def test_report(request):
    if not REPORT_PATH.is_file():
        return JSONResponse(
            {"detail": "Raport nie został jeszcze wygenerowany."}, status_code=404
        )
    return FileResponse(REPORT_PATH, media_type="text/html; charset=utf-8")


app = Starlette(
    debug=os.getenv("DEBUG", "false").lower() == "true",
    on_startup=[recover_catalog_transactions],
)

app.mount(
    "/graphql",
    GraphQLApp(schema, on_get=graphiql),
)

app.add_route("/health", health, methods=["GET"])
app.add_route("/reports/tests", test_report, methods=["GET"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
