"""Transparent broad groupings for official SEC Standard Industrial Classification codes.

The broad groups follow the U.S. SIC major divisions. They are not GICS,
I​​CB, or investment-sector classifications. Industry remains the SEC issuer's
verbatim SIC description.
"""
from __future__ import annotations


SIC_DIVISIONS: tuple[tuple[int, int, str], ...] = (
    (100, 999, "Agriculture, Forestry & Fishing"),
    (1000, 1499, "Mining"),
    (1500, 1799, "Construction"),
    (2000, 3999, "Manufacturing"),
    (4000, 4999, "Transportation, Communications & Utilities"),
    (5000, 5199, "Wholesale Trade"),
    (5200, 5999, "Retail Trade"),
    (6000, 6799, "Finance, Insurance & Real Estate"),
    (7000, 8999, "Services"),
    (9100, 9729, "Public Administration"),
)


def sic_sector(sic: str | None) -> str | None:
    """Return an SIC-division browse label only for a valid, mapped SIC code."""
    if not isinstance(sic, str) or len(sic) != 4 or not sic.isdigit():
        return None
    value = int(sic)
    return next((label for low, high, label in SIC_DIVISIONS if low <= value <= high), None)

