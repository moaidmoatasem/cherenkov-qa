"""Pydantic data models for Sync-Driven Development (SDD) Cockpit API."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SddSession(BaseModel):
    """SDD session state model."""
    id: str
    status: str
    task: str | None = None
    task_type: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    findings_count: int = 0
    token_total: int = 0
    summary: str | None = None
    compacted: bool = False


class SddSessionCreate(BaseModel):
    """Payload for creating a new SDD session."""
    task_type: str
    budget: int | None = None


class SddSessionClose(BaseModel):
    """Payload for closing an active SDD session."""
    summary: str


class SddFinding(BaseModel):
    """Finding log entry recorded during an SDD session."""
    timestamp: str
    type: str
    message: str


class SddSessionDetail(BaseModel):
    """Detailed view of an SDD session including recorded findings."""
    session: SddSession
    findings: list[SddFinding] = []


class SddExperience(BaseModel):
    """Stored SDD experience record."""
    id: str
    timestamp: str
    task: str | None = None
    action: str
    rationale: str = ""
    outcome: str = "success"
    token_cost: int = 0
    patterns: list[str] = []
    session_id: str = ""
    applicable_tasks: list[str] = []


class SddExperienceUpdate(BaseModel):
    """Payload for updating an SDD experience record."""
    outcome: str | None = None
    rationale: str | None = None
    patterns: list[str] | None = None


class SddExperienceCreate(BaseModel):
    """Payload for creating an SDD experience record."""
    task: str | None = None
    action: str
    rationale: str = ""
    outcome: str = "success"
    token_cost: int = 0
    patterns: list[str] = []


class TokenSnapshot(BaseModel):
    """Snapshot of token usage by action category."""
    session_id: str | None = None
    prompt: int = 0
    generate: int = 0
    read: int = 0
    search: int = 0
    total: int = 0


class TaskTypeStats(BaseModel):
    """Aggregate token and session metrics for a task type."""
    sessions: int = 0
    total_tokens: int = 0


class TokenHistory(BaseModel):
    """Historical aggregate token metrics."""
    total_all_time: int = 0
    sessions_completed: int = 0
    avg_per_session: float = 0.0
    by_task_type: dict[str, TaskTypeStats] = {}


class SddTokenData(BaseModel):
    """Complete token usage overview data."""
    current_session: TokenSnapshot = TokenSnapshot()
    budget: dict[str, Any] = {}
    historical: TokenHistory = TokenHistory()
    top_consumers: list[dict[str, Any]] = []


class ContextSnippet(BaseModel):
    """Context snippet payload entry."""
    key: str
    task_types: list[str] = []
    tokens_estimate: int = 0
    content: str = ""


class SddContextData(BaseModel):
    """Complete SDD context payload and task map."""
    version: int = 1
    last_refreshed: str = ""
    snippets: list[ContextSnippet] = []
    task_type_map: dict[str, list[str]] = {}


class SddContextUpdate(BaseModel):
    """Payload for updating context snippets and task map."""
    snippets: list[ContextSnippet] | None = None
    task_type_map: dict[str, list[str]] | None = None


class GraphStatus(BaseModel):
    """Knowledge graph status metrics."""
    node_count: int = 0
    edge_count: int = 0
    last_built: str | None = None
    session_count: int = 0
    experience_count: int = 0


class GraphNode(BaseModel):
    """Knowledge graph node model."""
    id: str
    type: str
    label: str
    properties: dict[str, Any] = {}
    size: float = 1.0
    color: str = "#22d3ee"


class GraphEdge(BaseModel):
    """Knowledge graph edge model."""
    source: str
    target: str
    type: str
    weight: float = 1.0
    label: str = ""


class GraphData(BaseModel):
    """Complete knowledge graph nodes and edges payload."""
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []


class WikiEntry(BaseModel):
    """Agent memory wiki entry metadata."""
    path: str
    title: str
    size: int = 0
    last_updated: str = ""
    cross_refs: list[str] = []


class WikiSearchResult(BaseModel):
    """Wiki search result entry."""
    path: str
    title: str
    snippet: str = ""
    score: float = 0.0


class GitCommit(BaseModel):
    """Correlated Git commit metadata."""
    hash: str
    author: str
    date: str
    message: str
    files: list[str] = []


class GitCorrelation(BaseModel):
    """Git commit correlation matching an SDD session."""
    session_id: str
    session_task: str | None = None
    commits: list[GitCommit] = []
    overlap_seconds: int = 0


class PatternInsight(BaseModel):
    """Extracted pattern performance insight."""
    name: str
    frequency: int = 0
    success_rate: float = 0.0
    avg_token_cost: float = 0.0
    experience_ids: list[str] = []


class CompactResult(BaseModel):
    """Summary of memory compaction operation."""
    sessions_since: int = 0
    snippets_before: int = 0
    snippets_after: int = 0
    promoted: int = 0
    archived: int = 0
