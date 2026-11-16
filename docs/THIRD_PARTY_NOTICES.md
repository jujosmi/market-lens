# Third-party components and data notices

This file identifies externally sourced components and services present in the export. It is not a legal opinion or a substitute for reviewing current terms before public or commercial use.

## TradingView chart widget

Market Overview embeds TradingView's hosted Advanced Chart widget. The integration keeps the widget's attribution and outbound link intact and does not extract chart data into Jujosmi calculations. TradingView's [widget FAQ](https://www.tradingview.com/widget-docs/faq/general/) explains that its hosted widgets retain attribution/branding unless permission is obtained; its [Terms of Service](https://www.tradingview.com/policies/) describe restrictions on accessing and redistributing content and market data. Review current terms and obtain any authorization required for the intended commercial product before public activation. The widget embed is not a separate market-data redistribution license.

## Aceternity UI components

The UI includes local React adaptations of the free Aceternity background-gradient and hover-border components. The exported app does not include paid Pro blocks/templates. Review the component source pages and the current [Aceternity licensing information](https://ui.aceternity.com/licence) before redistributing component source or making commercial use. Components copied into this repository should remain within the product source and should not be repackaged as stock UI assets. Any third-party code bundled inside a component remains subject to its own notice/license.

## NPM dependencies

The exact frontend dependency graph is pinned by `frontend/package-lock.json`. The dependencies are installed from their package registries by `npm ci`; their package-specific licenses/notices are available in the installed packages. Review the dependency licenses before distributing binaries or a hosted commercial product. No `node_modules` directory is included in this source export.

## Logos and other assets

The included Jujosmi logo is a project asset. Confirm the owner has the rights to distribute it with any public release. No external screenshots or sample-company imagery are included.
