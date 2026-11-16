"""Validated industry keys and company-list fallbacks for Discovery."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable, Mapping, Sequence

import pandas as pd


LOGGER = logging.getLogger("market_lens.discovery")


def provider_text(value: object) -> str:
    """Return text for a scalar provider field, treating pandas nulls as absent."""
    if value is None or not pd.api.types.is_scalar(value):
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        return ""
    return str(value).strip()


def industry_identity(value: object) -> str:
    """Normalize punctuation for display-name comparisons, not for API keys."""
    return re.sub(r"[\W_]+", " ", provider_text(value).casefold(), flags=re.UNICODE).strip()


def canonical_key_for_industry_name(name: str, valid_keys: Sequence[str]) -> str | None:
    """Match a display name to yfinance's known canonical key list.

    This mirrors yfinance's published name-to-key normalization, but only
    returns a candidate that exists in the provider-maintained key list.
    Unicode punctuation such as Yahoo's em dash is deliberately preserved.
    """
    normalized_name = provider_text(name)
    if not normalized_name:
        return None
    candidate = (normalized_name.casefold().replace("& ", "").replace("- ", "")
                 .replace(", ", " ").replace(" ", "-"))
    return candidate if candidate in set(valid_keys) else None


def canonical_local_industry_rows(
    industry_mapping: Mapping[str, Iterable[str]],
    canonical_key_mapping: Mapping[str, Sequence[str]],
    sector_labels: Mapping[str, str],
) -> list[dict[str, str]]:
    """Build offline categories only where a package-listed key matches."""
    sector_names = {name.casefold(): key for key, name in sector_labels.items()}
    rows = []
    for sector_name, industry_names in industry_mapping.items():
        sector_key = sector_names.get(str(sector_name).casefold())
        if not sector_key:
            continue
        valid_keys = canonical_key_mapping.get(sector_key, ())
        for industry_name in industry_names:
            name = str(industry_name).strip()
            key = canonical_key_for_industry_name(name, valid_keys)
            if key:
                rows.append({
                    "industry_key":key, "industry":name,
                    "sector_key":sector_key, "sector":str(sector_name),
                    "source":"Built-in yfinance directory",
                })
    return rows


def _log_provider_error(endpoint: str, key: str, exc: Exception) -> str:
    LOGGER.warning("Yahoo Finance %s request failed for industry key %r (%s): %s",
                   endpoint, key, type(exc).__name__, str(exc)[:240])
    return f"{endpoint}: {type(exc).__name__}"


def _combine_company_frames(frames: list[tuple[str, pd.DataFrame]]) -> pd.DataFrame:
    usable = []
    for label, companies in frames:
        if not isinstance(companies, pd.DataFrame) or companies.empty:
            continue
        frame = companies.copy()
        if "symbol" in frame.columns:
            frame = frame.set_index("symbol")
        frame.index = frame.index.map(lambda value: str(value).strip().upper())
        frame = frame.loc[frame.index != ""]
        frame["Company list"] = label
        if not frame.empty:
            usable.append(frame)
    if not usable:
        return pd.DataFrame()
    combined = pd.concat(usable, axis=0, sort=False)
    combined["Company list"] = combined.groupby(level=0, sort=False)["Company list"].transform(
        lambda labels: " · ".join(dict.fromkeys(labels))
    )
    return combined.groupby(level=0, sort=False).first()


def _sector_company_fallback(
    industry_key: str,
    sector_key: str,
    industry_name: str,
    sector_name: str,
    key_verified: bool,
    sector_factory: Callable,
    ticker_factory: Callable,
) -> tuple[pd.DataFrame, list[str]]:
    errors = []
    try:
        sector_companies = sector_factory(sector_key).top_companies
    except Exception as exc:
        errors.append(_log_provider_error(f"sector {sector_key!r} top-companies fallback", industry_key, exc))
        return pd.DataFrame(), errors
    if not isinstance(sector_companies, pd.DataFrame) or sector_companies.empty:
        LOGGER.info("Yahoo Finance returned no top companies for fallback sector %r", sector_key)
        return pd.DataFrame(), errors

    verification_by_symbol = {}
    for symbol in sector_companies.index:
        ticker_symbol = str(symbol).strip().upper()
        if not ticker_symbol:
            continue
        try:
            profile = ticker_factory(ticker_symbol).get_info()
        except Exception as exc:
            errors.append(_log_provider_error(f"ticker profile {ticker_symbol!r} industryKey check", industry_key, exc))
            continue
        if not isinstance(profile, Mapping):
            profile = {}
        provider_key = provider_text(profile.get("industryKey"))
        key_match = key_verified and provider_key.casefold() == industry_key.casefold()
        profile_name_match = (
            industry_identity(profile.get("industry")) == industry_identity(industry_name)
            and industry_identity(profile.get("sector")) == industry_identity(sector_name)
        )
        if key_match or profile_name_match:
            verification_by_symbol[ticker_symbol] = (
                "Yahoo industryKey verified" if key_match
                else "Yahoo profile industry and sector verified"
            )
    if not verification_by_symbol:
        return pd.DataFrame(), errors
    fallback = sector_companies.copy()
    fallback.index = fallback.index.map(lambda value: str(value).strip().upper())
    fallback = fallback.loc[fallback.index.isin(verification_by_symbol)].copy()
    fallback["Company list"] = [
        f"Sector top companies · {verification_by_symbol[symbol]}" for symbol in fallback.index
    ]
    return fallback, errors


def fetch_industry_companies(
    industry_key: str,
    industry_source: str,
    sector_key: str,
    industry_name: str,
    sector_name: str,
    industry_factory: Callable,
    sector_factory: Callable,
    ticker_factory: Callable,
    canonical_keys: Sequence[str],
    valid_sector_keys: Sequence[str],
) -> tuple[pd.DataFrame, str | None]:
    """Fetch Yahoo industry listings, with a validated sector/profile fallback."""
    key = provider_text(industry_key)
    if not key:
        return pd.DataFrame(), "The selected industry has no provider key. Choose another industry."
    if sector_key not in set(valid_sector_keys):
        return pd.DataFrame(), f"The selected sector key {sector_key!r} is not recognized by yfinance."

    errors = []
    key_issue = None
    industry = None
    # A key from the live sector directory is provider-sourced, but still check
    # its Industry object identity before trusting any company listings. Local
    # keys also need to exist in yfinance's bundled canonical allowlist.
    key_verified = False
    if industry_source != "Yahoo Finance" and key not in set(canonical_keys):
        key_issue = f"Built-in key {key!r} is not in yfinance's canonical industry-key list"
        LOGGER.warning("Rejected unlisted local Yahoo Finance industry key %r for %s", key, industry_name)
    else:
        try:
            industry = industry_factory(key)
        except Exception as exc:
            errors.append(_log_provider_error("industry object", key, exc))

    if industry is not None:
        try:
            provider_name = provider_text(industry.name)
            provider_sector = provider_text(industry.sector_key)
            identity_matches = (
                industry_identity(provider_name) == industry_identity(industry_name)
                and provider_sector.casefold() == sector_key.casefold()
            )
            if not identity_matches:
                key_issue = (
                    f"Yahoo Finance returned industry {provider_name or '<missing>'!r} and sector key "
                    f"{provider_sector or '<missing>'!r} for {key!r}; expected industry "
                    f"{industry_name!r} and sector key {sector_key!r}. No unverified industry listings were used."
                )
                LOGGER.warning(
                    "Rejected Yahoo Finance industry identity for key %r: returned name=%r sector=%r; "
                    "expected name=%r sector=%r",
                    key, provider_name, provider_sector, industry_name, sector_key,
                )
                industry = None
            else:
                key_verified = True
        except Exception as exc:
            key_issue = f"Yahoo Finance industry identity for key {key!r} could not be verified ({type(exc).__name__})."
            errors.append(_log_provider_error("industry identity metadata", key, exc))
            industry = None

    frames = []
    if industry is not None:
        for label, attribute in (
            ("Top companies", "top_companies"),
            ("Top performing", "top_performing_companies"),
            ("Top growth", "top_growth_companies"),
        ):
            try:
                frames.append((label, getattr(industry, attribute)))
            except Exception as exc:
                errors.append(_log_provider_error(f"industry {attribute}", key, exc))

        combined = _combine_company_frames(frames)
        if not combined.empty:
            warning = ("Some industry listing requests failed; the returned company lists are shown."
                       if errors else None)
            return combined, warning

        # yfinance can suppress its internal fetch error and expose empty None
        # attributes. A missing domain name distinguishes that from an actual
        # industry response whose company arrays are genuinely empty.
        try:
            if not provider_text(industry.name):
                errors.append("Industry response did not contain Yahoo Finance domain metadata")
                LOGGER.warning("Yahoo Finance industry response had no domain metadata for key %r", key)
            else:
                LOGGER.info("Yahoo Finance returned empty company lists for valid industry key %r", key)
        except Exception as exc:
            errors.append(_log_provider_error("industry metadata", key, exc))

    fallback, fallback_errors = _sector_company_fallback(
        key, sector_key, industry_name, sector_name, key_verified,
        sector_factory, ticker_factory,
    )
    errors.extend(fallback_errors)
    if not fallback.empty:
        warning = ("Industry listing was unavailable or did not match its selected identity; showing "
                   "sector companies with Yahoo profile industry/sector confirmation."
                   if errors or key_issue else None)
        return fallback, warning
    if errors:
        return pd.DataFrame(), ("Yahoo Finance company-list requests failed or returned incomplete provider "
                                "metadata. Try again later; technical details were logged.")
    if key_issue:
        return pd.DataFrame(), (f"{key_issue}; no sector companies with a matching Yahoo profile were returned.")
    return pd.DataFrame(), None
