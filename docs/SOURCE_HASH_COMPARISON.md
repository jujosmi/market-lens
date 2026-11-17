# Source Hash Comparison

The CSV manifest records SHA-256 for each included export file with a corresponding source and marks each as `MATCH`, `ADAPTED`, or `NEW`. Generated manifests are excluded from their own hash list.

- Exact source matches: 84
- Adapted source files: 4
- New export files: 8

The backend parity test is self-contained by default: it verifies the pinned engine snapshot against the included SHA-256 manifest. `JUJOSMI_TRADE_SOURCE_ROOT` is optional and only enables comparison with an external source checkout. Normal builds and tests do not depend on the original Streamlit repository.
