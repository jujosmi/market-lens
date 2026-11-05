# Add Market Lens to the Cloudflare website

Market Lens is a Streamlit/Python application. Cloudflare Pages serves the website files, but it does not run this Streamlit app as a static page. Host the Streamlit app separately, then place the iframe from [`market-lens-iframe.html`](market-lens-iframe.html) in the Cloudflare Pages site. The iframe stays responsive and shows the compact Streamlit embed view.

## 1. Publish the app from GitHub

Put this project folder in a GitHub repository. In Streamlit Community Cloud, create an app that uses `app.py` as its entrypoint and the repository's `requirements.txt`. Streamlit's official guide describes this GitHub-based deployment flow and the dependency file requirements: [deploy an app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [app dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).

Community Cloud supports embedding **public** apps; private app embeds are not officially supported. If the dashboard must be private, deploy Streamlit on an authenticated host you control instead of making the Community Cloud app public. See Streamlit's [embed guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app/embed-your-app).

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

The hover explanations and draggable assistant operate inside the Market Lens iframe. The assistant does not float over other Cloudflare page elements outside that iframe.

## 5. Local check

Run the app locally before publishing:

```powershell
.venv\Scripts\python.exe -m streamlit run app.py
```

The website itself cannot display the iframe until the Streamlit app has a reachable HTTPS host URL. This folder is prepared for that integration, but it has not been deployed to GitHub, Cloudflare Pages, or Streamlit Community Cloud.
