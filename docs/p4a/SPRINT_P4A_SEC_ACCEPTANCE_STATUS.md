# Sprint P4A — SEC Acceptance Status

## Status: blocked before outbound SEC request

The backend's identifying `SEC_EDGAR_USER_AGENT` was absent from the current process, user, and machine environment. The earlier local `/api/v1/companies/AAPL/sec-research` check returned the application's explicit configuration-required response before an upstream SEC request. No live SEC endpoint was contacted during this sprint.

Consequently this sprint did not independently verify live AAPL or NVDA ticker/CIK identity, reported facts, original units, periods, accession numbers, or filing URLs. It did not render populated live SEC financials at 390×844, 768×1024, or 1280×900, and no live-data screenshots were captured. This is not evidence that SEC is empty or that the integration works against current SEC responses.

## To complete acceptance

1. Set `SEC_EDGAR_USER_AGENT` in the PowerShell process that launches the local backend. Use the application name/version and a real owner-configured contact address; do not send that address in chat or commit it.
2. Restart the backend and verify only that the process has a non-empty identifying value, without printing the value.
3. Make the bounded AAPL request first under the existing limiter. Stop immediately on 403, 429/access-policy rejection, or non-JSON response; do not retry around SEC limits.
4. If AAPL succeeds, inspect returned identity, facts, original units/periods, accession and filing links, then repeat to confirm cache behavior. Continue with NVDA only after AAPL succeeds and within the same bounded request policy.
5. Open the actual Company Research financial view at 390×844, 768×1024, and 1280×900. Capture labeled screenshots and check tables, disclosures, source links, scrolling, and keyboard controls.

Public activation should continue to treat actual SEC research acceptance as pending until these steps are observed.
