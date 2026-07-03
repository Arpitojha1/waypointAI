"""
Waypoint API — OpenAI SDK Tool Definitions for OpenRouter

Defines tools used by the OpenAI tool-use loop in the Roadmap Generation Orchestrator:
- create_roadmap
- create_step
- append_resources
- draft_outreach
"""

from typing import List, Dict, Any

CREATE_ROADMAP_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "create_roadmap",
        "description": "Create the overall roadmap strategic plan for pursuing this opportunity. Must be called exactly once per roadmap generation.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Clear, engaging title for the roadmap plan."
                },
                "summary": {
                    "type": "string",
                    "description": "Strategic executive summary explaining the game plan to achieve this opportunity."
                }
            },
            "required": ["title", "summary"]
        }
    }
}

CREATE_STEP_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "create_step",
        "description": "Create a single actionable milestone or step within the roadmap. Call this tool multiple times (typically 4 to 7 times) in sequential order to build out the checklist.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Actionable milestone title (e.g. 'Setup Environment & Verify Reproduction')."
                },
                "description": {
                    "type": "string",
                    "description": "Detailed instructions on how to accomplish this step, specifically addressing any skill gaps or highlighting existing strengths from the user's profile."
                },
                "order_index": {
                    "type": "integer",
                    "description": "Sequential order index starting at 1 for the first step, 2 for the second, etc."
                },
                "resource_links": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"}
                        },
                        "required": ["title", "url"]
                    },
                    "description": "Optional helpful documentation links or tutorials relevant to this step."
                }
            },
            "required": ["title", "description", "order_index"]
        }
    }
}

APPEND_RESOURCES_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "append_resources",
        "description": "Curate and attach helpful resource links (docs, tutorials, reference repos) to a step.",
        "parameters": {
            "type": "object",
            "properties": {
                "step_order_index": {
                    "type": "integer",
                    "description": "The order_index of the step to attach resources to."
                },
                "resources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Title of the resource"},
                            "url": {"type": "string", "description": "URL of the resource"}
                        },
                        "required": ["title", "url"]
                    }
                }
            },
            "required": ["step_order_index", "resources"]
        }
    }
}

DRAFT_OUTREACH_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "draft_outreach",
        "description": "Draft personalized networking outreach message, cover letter excerpt, or maintainer PR communication tailored to this opportunity.",
        "parameters": {
            "type": "object",
            "properties": {
                "recipient": {
                    "type": "string",
                    "description": "Target recipient (e.g. Hiring Manager, Maintainer, Hackathon Team/Mentor)"
                },
                "subject": {
                    "type": "string",
                    "description": "Subject line or topic"
                },
                "message_body": {
                    "type": "string",
                    "description": "Drafted message text highlighting user's strengths and relevance to the target."
                }
            },
            "required": ["recipient", "subject", "message_body"]
        }
    }
}

ROADMAP_TOOLS: List[Dict[str, Any]] = [
    CREATE_ROADMAP_TOOL,
    CREATE_STEP_TOOL,
    APPEND_RESOURCES_TOOL,
    DRAFT_OUTREACH_TOOL,
]
