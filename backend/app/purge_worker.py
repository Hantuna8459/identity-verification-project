from __future__ import annotations

import logging
import time

from sqlmodel import Session

from app.adapters.analyzer import OfflineModelAnalyzer
from app.adapters.security import TokenService
from app.adapters.storage import EncryptedLocalEvidenceStorage
from app.core.config import get_settings
from app.core.database import create_db_and_tables, engine
from app.services.ekyc import EkycService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vid-ekyc-purge")


def run_once() -> int:
    settings = get_settings()
    create_db_and_tables()
    with Session(engine) as db:
        service = EkycService(
            db=db,
            settings=settings,
            tokens=TokenService(settings.token_secret),
            storage=EncryptedLocalEvidenceStorage(settings.evidence_dir, settings.evidence_key),
            analyzer=OfflineModelAnalyzer(settings.model_dir, settings.require_models),
        )
        purged = service.purge_due("purge-worker")
    logger.info("Purge cycle completed: %s session(s)", len(purged))
    return len(purged)


def main() -> None:
    settings = get_settings()
    interval = max(1, settings.purge_interval_hours) * 3600
    while True:
        run_once()
        time.sleep(interval)


if __name__ == "__main__":
    main()
