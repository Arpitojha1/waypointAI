# Ingestion module
from app.ingestion.github_issues import (
    fetch_good_first_issues,
    fetch_good_first_issues_global,
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
from app.ingestion.remoteok_jobs import (
    fetch_remoteok_jobs,
    normalize_job as normalize_remoteok_job,
    opportunity_to_dict as remoteok_opportunity_to_dict,
    ingest_remoteok_jobs,
)
from app.ingestion.remotive_jobs import (
    fetch_remotive_jobs,
    normalize_job as normalize_remotive_job,
    opportunity_to_dict as remotive_opportunity_to_dict,
    ingest_remotive_jobs,
)

__all__ = [
    "fetch_good_first_issues",
    "fetch_good_first_issues_global",
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
    "fetch_remoteok_jobs",
    "normalize_remoteok_job",
    "remoteok_opportunity_to_dict",
    "ingest_remoteok_jobs",
    "fetch_remotive_jobs",
    "normalize_remotive_job",
    "remotive_opportunity_to_dict",
    "ingest_remotive_jobs",
]
