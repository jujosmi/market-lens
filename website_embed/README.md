# Add Jujosmi Trade to the Cloudflare website

Jujosmi Trade is a Streamlit/Python application. Cloudflare Pages serves the public site at trade.jujosmi.com; the embedded Streamlit experience remains guest-only with session-isolated watchlists. Authenticated users will open the Streamlit application at its top-level URL rather than sign in inside the iframe. The live Cloudflare configuration and authenticated app URL are not stored in this repository.

## 1. Preserve the existing Streamlit host

This branding update does not create a new Streamlit app or change its hosting origin. The checked-in index.html contains the current local embed target; it is not proof of the live Cloudflare iframe URL. Keep the deployed guest iframe pointed at its existing origin. The market-lens-iframe.html template is for coordinated local edits; copy its branding to Cloudflare only during a separately approved deployment update.

The authenticated experience is planned for a direct, top-level Streamlit visit. Its URL and callback settings are controlled by hosting/auth configuration outside this repository. Do not place sign-in inside the guest iframe.

## 2. Protect per-visitor watchlists

Set this value in the Streamlit app's Secrets settings before sharing a hosted deployment:

```toml
MARKET_LENS_HOSTED = "true"
```

Hosted mode keeps each visitor's watchlist in that visitor's Streamlit session. The local development mode continues to save `.market_lens_watchlist.json` on the local computer. Hosted session watchlists last for the active browser session and are not shared with other site visitors.

## 3. Configure the AI terminology assistant (optional)

To enable open-ended AI explanations, add the key to Streamlit's server-side Secrets settings:

```toml
OPENAI_API_KEY = "your-api-key"
```

Do not put the API key in the Cloudflare website, an iframe URL, browser JavaScript, or a GitHub commit. Without a key, the draggable helper still answers common market terms using its built-in offline glossary. When AI is enabled, questions and recent chat are sent to OpenAI for processing and may incur API charges; the watchlist and market data are not attached automatically. Chat history stays in the active Streamlit session.

## 4. Embed it in Cloudflare Pages

Copy the contents of `market-lens-iframe.html` into the page or layout where the dashboard should appear. Replace:

```text
https://YOUR-MARKET-LENS-APP.streamlit.app/?embed=true
```

with the public URL Streamlit gives the deployed app. The `?embed=true` parameter removes Streamlit's toolbar, top/bottom padding and footer. For example, if the deployed URL is `https://market-lens.streamlit.app/`, use:

```text
https://market-lens.streamlit.app/?embed=true
```

The hover explanations and draggable assistant operate inside the Jujosmi Trade iframe. The assistant does not float over other Cloudflare page elements outside that iframe.

## 5. Local check

Run the app locally before publishing:

```powershell
.venv\Scripts\python.exe -m streamlit run app.py
```

The website itself cannot display the iframe until the Streamlit app has a reachable HTTPS host URL. This folder is prepared for that integration, but it has not been deployed to GitHub, Cloudflare Pages, or Streamlit Community Cloud.
