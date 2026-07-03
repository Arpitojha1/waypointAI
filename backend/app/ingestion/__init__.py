# Ingestion module
from app.ingestion.github_issues import (
    fetch_good_first_issues,
    normalize_issue,
    opportunity_to_dict as issue_opportunity_to_dict,
    ingest_github_issues,
    verify_github_issue_open,
)
from app.ingestion.devpost_hackathons import (
    fetch_devpost_hackathons,
    normalize_hackathon,
    opportunity_to_dict as hackathon_opportunity_to_dict,
    ingest_devpost_hackathons,
)
from app.ingestion.arbeitnow_jobs import (
    fetch_arbeitnow_jobs,
    normalize_job,
    opportunity_to_dict as job_opportunity_to_dict,
    ingest_arbeitnow_jobs,
)

__all__ = [
    "fetch_good_first_issues",
    "normalize_issue",
    "issue_opportunity_to_dict",
    "ingest_github_issues",
    "verify_github_issue_open",
    "fetch_devpost_hackathons",
    "normalize_hackathon",
    "hackathon_opportunity_to_dict",
    "ingest_devpost_hackathons",
    "fetch_arbeitnow_jobs",
    "normalize_job",
    "job_opportunity_to_dict",
    "ingest_arbeitnow_jobs",
]
