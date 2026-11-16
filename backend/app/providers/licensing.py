"""Default-deny public-use gate; provenance labels are descriptive, not licenses."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import Field, field_validator

from .contracts import ProviderModel, ProviderResult

PublicUseAction = Literal["public_display", "commercial_display", "redistribute", "derived_public"]


class LicenseApproval(ProviderModel):
    """An independently reviewed grant recorded from an executed agreement."""

    provider_id: str = Field(min_length=1, max_length=80)
    product: str = Field(min_length=1, max_length=120)
    agreement_id: str = Field(min_length=1, max_length=120)
    approved: bool = False
    valid_from: datetime
    expires_at: datetime | None = None
    allowed_actions: list[PublicUseAction] = Field(default_factory=list)
    attribution_required: bool = True
    attribution_text: str | None = None
    max_cache_age_seconds: int | None = Field(default=None, ge=0)

    @field_validator("valid_from", "expires_at")
    @classmethod
    def agreement_dates_must_be_aware(cls, value: datetime | None):
        if value is not None and value.utcoffset() is None:
            raise ValueError("Agreement dates must include a timezone.")
        return value


class PublicUseDecision(ProviderModel):
    allowed: bool
    reason: str
    attribution: str | None = None


def evaluate_public_use(
    result: ProviderResult,
    approval: LicenseApproval | None,
    action: PublicUseAction,
    *,
    now: datetime | None = None,
    cache_age_seconds: int | None = None,
) -> PublicUseDecision:
    """Authorize public output only when an active, scoped agreement says so.

    ProviderResult.provenance.permitted_use is a provider-supplied descriptive
    label. It is necessary but never sufficient evidence of legal approval.
    """
    if result.data is None or result.status not in {"ok", "partial"}:
        return PublicUseDecision(allowed=False, reason="No usable provider result is available.")
    if result.provenance.permitted_use not in {"public_display", "commercial_display"}:
        return PublicUseDecision(allowed=False, reason="Provider metadata does not identify public display as permitted.")
    if action == "commercial_display" and result.provenance.permitted_use != "commercial_display":
        return PublicUseDecision(allowed=False, reason="Provider metadata does not identify commercial display as permitted.")
    if approval is None or not approval.approved:
        return PublicUseDecision(allowed=False, reason="No approved provider agreement is configured.")
    if (approval.provider_id, approval.product) != (result.provenance.provider_id, result.provenance.product):
        return PublicUseDecision(allowed=False, reason="The approved agreement does not cover this provider product.")
    now = now or datetime.now(timezone.utc)
    if now.utcoffset() is None or approval.valid_from.utcoffset() is None:
        return PublicUseDecision(allowed=False, reason="Agreement dates must include a timezone.")
    if now < approval.valid_from or (approval.expires_at is not None and now >= approval.expires_at):
        return PublicUseDecision(allowed=False, reason="The provider agreement is not currently active.")
    if action not in approval.allowed_actions:
        return PublicUseDecision(allowed=False, reason="The agreement does not authorize this public use.")
    if approval.attribution_required and not (approval.attribution_text and approval.attribution_text.strip()):
        return PublicUseDecision(allowed=False, reason="Required provider attribution is not configured.")
    if result.stale and cache_age_seconds is None:
        return PublicUseDecision(allowed=False, reason="Stale data cannot be displayed without checking its retention age.")
    if cache_age_seconds is not None:
        if cache_age_seconds < 0:
            return PublicUseDecision(allowed=False, reason="Cache age cannot be negative.")
        if approval.max_cache_age_seconds is None or cache_age_seconds > approval.max_cache_age_seconds:
            return PublicUseDecision(allowed=False, reason="The requested cache retention exceeds the approved limit.")
    return PublicUseDecision(allowed=True, reason="Use is covered by the configured agreement.",
                             attribution=approval.attribution_text if approval.attribution_required else None)
