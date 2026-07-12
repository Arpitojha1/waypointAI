"""
Waypoint API — Batch Ingestion Script

Runs all four source ingestion functions concurrently via asyncio.gather.
Each source is wrapped in its own try/except so one failing never blocks the others.

Usage:
    cd backend
    python scripts/ingest_all_sources.py
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("ingest_all")


async def _run_arbeitnow():
    from app.ingestion.arbeitnow_jobs import ingest_arbeitnow_jobs
    t0 = time.perf_counter()
    try:
        opps = await ingest_arbeitnow_jobs(max_jobs=30, remember_in_cognee=False)
        elapsed = time.perf_counter() - t0
        logger.info("Arbeitnow: %d jobs fetched in %.1fs", len(opps), elapsed)
        return len(opps)
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.error("Arbeitnow FAILED after %.1fs: %s", elapsed, exc)
        return 0


async def _run_remoteok():
    from app.ingestion.remoteok_jobs import ingest_remoteok_jobs
    t0 = time.perf_counter()
    try:
        opps = await ingest_remoteok_jobs(max_jobs=30, remember_in_cognee=False)
        elapsed = time.perf_counter() - t0
        logger.info("RemoteOK: %d jobs fetched in %.1fs", len(opps), elapsed)
        return len(opps)
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.error("RemoteOK FAILED after %.1fs: %s", elapsed, exc)
        return 0


async def _run_remotive():
    from app.ingestion.remotive_jobs import ingest_remotive_jobs
    t0 = time.perf_counter()
    try:
        opps = await ingest_remotive_jobs(max_jobs=30, remember_in_cognee=False)
        elapsed = time.perf_counter() - t0
        logger.info("Remotive: %d jobs fetched in %.1fs", len(opps), elapsed)
        return len(opps)
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.error("Remotive FAILED after %.1fs: %s", elapsed, exc)
        return 0


async def _run_github():
    from app.ingestion.github_issues import ingest_github_issues
    t0 = time.perf_counter()
    try:
        opps = await ingest_github_issues(max_issues=30, remember_in_cognee=False)
        elapsed = time.perf_counter() - t0
        logger.info("GitHub Issues: %d issues fetched in %.1fs", len(opps), elapsed)
        return len(opps)
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.error("GitHub Issues FAILED after %.1fs: %s", elapsed, exc)
        return 0


async def main():
    logger.info("Starting batch ingestion of all 4 sources...")
    t0 = time.perf_counter()
    arbeitnow_count, remoteok_count, remotive_count, github_count = await asyncio.gather(
        _run_arbeitnow(),
        _run_remoteok(),
        _run_remotive(),
        _run_github(),
    )
    total_elapsed = time.perf_counter() - t0
    logger.info(
        "=== BATCH INGESTION COMPLETE ===\n"
        "  Arbeitnow:  %d jobs\n"
        "  RemoteOK:   %d jobs\n"
        "  Remotive:   %d jobs\n"
        "  GitHub:     %d issues\n"
        "  Total:      %d items in %.1fs",
        arbeitnow_count, remoteok_count, remotive_count, github_count,
        arbeitnow_count + remoteok_count + remotive_count + github_count,
        total_elapsed,
    )


if __name__ == "__main__":
    asyncio.run(main())
