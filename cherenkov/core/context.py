from contextvars import ContextVar

# This holds the organization_id for the current request context.
# Default is 'default' for single-tenant / local CLI usage.
current_org_id: ContextVar[str] = ContextVar("current_org_id", default="default")
