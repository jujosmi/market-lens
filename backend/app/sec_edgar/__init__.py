"""Server-side SEC EDGAR client and explicit Company Facts normalization boundary."""

from .client import SecAccessBlocked, SecClientError, SecConfigurationError, SecEdgarHttpClient, SecEdgarSettings, SecRateLimited
from .mapping import SecCompanyReport, SecIdentity, SecMappingError, map_company_facts
from .service import SecCompanyResearchService, SecEdgarGateway

__all__ = ["SecAccessBlocked", "SecClientError", "SecConfigurationError", "SecEdgarHttpClient", "SecEdgarSettings",
           "SecRateLimited", "SecCompanyReport", "SecIdentity", "SecMappingError", "SecCompanyResearchService",
           "SecEdgarGateway", "map_company_facts"]
