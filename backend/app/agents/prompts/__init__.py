# Agent prompts module
from app.agents.prompts.ingestion import INGESTION_SYSTEM_PROMPT
from app.agents.prompts.devpost import DEVPOST_SYSTEM_PROMPT
from app.agents.prompts.arbeitnow import ARBEITNOW_SYSTEM_PROMPT
from app.agents.prompts.remoteok import REMOTEOK_SYSTEM_PROMPT
from app.agents.prompts.remotive import REMOTIVE_SYSTEM_PROMPT
from app.agents.prompts.roadmap_job import ROADMAP_JOB_SYSTEM_PROMPT
from app.agents.prompts.roadmap_hackathon import ROADMAP_HACKATHON_SYSTEM_PROMPT
from app.agents.prompts.roadmap_issue import ROADMAP_ISSUE_SYSTEM_PROMPT

__all__ = [
    "INGESTION_SYSTEM_PROMPT",
    "DEVPOST_SYSTEM_PROMPT",
    "ARBEITNOW_SYSTEM_PROMPT",
    "REMOTEOK_SYSTEM_PROMPT",
    "REMOTIVE_SYSTEM_PROMPT",
    "ROADMAP_JOB_SYSTEM_PROMPT",
    "ROADMAP_HACKATHON_SYSTEM_PROMPT",
    "ROADMAP_ISSUE_SYSTEM_PROMPT",
]
