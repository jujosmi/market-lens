"""Finance-specific headline classification rules.

This is an inspectable heuristic, not a trained model. The score is not a
calibrated probability and must not be read as a forecast of stock returns.
"""

import re


BULL_WORDS = {
    "beat":1.1, "beats":1.1, "exceeds":1.2, "surge":1.8, "surges":1.8, "soars":1.8,
    "upgrade":1.7, "upgraded":1.7, "outperform":1.7, "outperforms":1.7, "bullish":1.7,
    "growth":0.8, "grows":0.9, "growing":0.8, "record":0.8, "profit":0.8, "profits":0.9,
    "profitable":1.0, "strong":0.5, "approval":1.4, "approved":1.4, "wins":1.3, "awarded":1.2,
    "rally":1.5, "rallies":1.5, "rebound":1.3, "rebounds":1.3, "expands":0.8, "accelerates":0.8,
    "optimistic":0.8, "buyback":1.1, "dividend":0.5, "raises":0.5, "raised":0.5, "positive":0.9,
    "record-high":1.2, "milestone":0.6, "backlog":0.4, "partnership":0.3,
}
BEAR_WORDS = {
    "miss":1.1, "misses":1.1, "missed":1.1, "plunge":1.9, "plunges":1.9, "plunged":1.9,
    "crash":1.9, "crashes":1.9, "drop":1.3, "drops":1.3, "fell":1.2, "falls":1.2,
    "downgrade":1.7, "downgraded":1.7, "underperform":1.7, "bearish":1.7, "loss":0.9, "losses":1.0,
    "weak":0.6, "lawsuit":1.1, "probe":1.1, "investigation":1.0, "recall":1.1, "warning":0.8,
    "warns":0.8, "warned":0.8, "decline":1.1, "declines":1.1, "negative":0.9, "layoffs":0.9,
    "slump":1.4, "slumps":1.4, "overhang":0.8, "dilution":1.1, "dilutive":1.1, "bankruptcy":2.0,
    "default":1.7, "resigns":0.7, "resignation":0.7, "restatement":1.6, "impairment":1.1,
    "shortfall":1.2, "downturn":1.1, "suspends":1.2, "suspension":1.2, "antitrust":0.8,
    "fraud":1.7, "breach":1.1, "cuts":0.6, "cut":0.6, "refuses":0.9, "rejects":0.9,
    "rejected":0.9, "fails":1.0, "failed":1.0,
}
BULL_PHRASES = {
    "beats estimates":2.4, "beats expectations":2.4, "tops estimates":2.2, "raises guidance":2.6,
    "raises full-year outlook":2.6, "raises forecast":2.1, "raises price target":2.0, "price target raised":2.0,
    "upgraded to buy":2.4, "receives fda approval":2.5, "wins contract":2.0,
    "revenue grows":1.6, "sales growth":1.5, "earnings growth":1.5, "record revenue":1.8,
    "strong demand":1.5, "demand surges":1.8, "shares rise":2.0, "shares jump":2.2,
    "shares surge":2.4, "shares gain":1.7, "stock rises":1.9, "stock jumps":2.1,
    "win contract":2.0, "profit jumps":1.8, "margin expansion":1.7,
    "increases dividend":1.5, "authorizes buyback":1.5,
}
BEAR_PHRASES = {
    "misses estimates":2.4, "misses expectations":2.4, "misses earnings":2.5,
    "cuts guidance":2.6, "lowers guidance":2.6, "cuts full-year outlook":2.6, "cuts forecast":2.1,
    "price target cut":2.0, "downgraded to sell":2.4, "revenue falls":1.8, "revenue declines":1.8,
    "shares fall":3.1, "shares drop":3.1, "shares plunge":3.2, "shares tumble":3.2,
    "shares slide":2.8, "shares sink":3.0, "stock falls":3.0, "stock drops":3.0, "stock tumbles":3.2,
    "profit warning":2.4, "going concern":2.8, "accounting probe":2.0, "cuts dividend":1.8,
    "growth slows":2.0, "slowing growth":2.0, "revenue miss":2.0, "earnings miss":2.0,
    "lowers price target":2.0, "demand weakens":1.8, "customer churn":1.8, "dilutive offering":2.0,
    "halts production":2.0, "recalls vehicles":1.8, "fda rejects":2.6, "approval denied":2.5,
    "trial fails":2.8, "clinical hold":2.4, "failed trial":2.8, "loses contract":2.2,
}
NEGATORS = {"not", "no", "never", "without", "isnt", "isn't", "wasnt", "wasn't", "can't", "cannot", "unable", "fails", "failed", "denies", "denied", "rejects", "rejected"}
INTENSIFIERS = {"sharply":1.35, "significantly":1.3, "strongly":1.25, "major":1.2, "record":1.15}
ISSUER_CONTEXT = {
    "company", "business", "earnings", "quarter", "results", "result", "revenue", "sales", "eps", "guidance", "outlook", "forecast",
    "profit", "profits", "margin", "demand", "customer", "customers", "contract", "product",
    "dividend", "buyback", "offering", "debt", "default", "bankruptcy", "fraud", "breach",
    "fda", "trial", "recall", "lawsuit", "probe", "investigation", "ceo", "cfo", "executive",
    "analyst", "price", "target", "acquisition", "merger", "production", "factory", "launch",
    "regulatory", "approval", "approved", "denied", "denies", "denial", "downgrade", "upgrade",
}
MARKET_CONTEXT = re.compile(
    r"\b(?:markets?|stocks?|wall street|nasdaq|s&p\s*500|dow(?:\s+jones)?|futures|"
    r"treasur(?:y|ies)|bonds?|oil prices|the economy|economy|sector|indices|index)\b",
    re.IGNORECASE,
)
LEGAL_SUFFIXES = {"inc", "incorporated", "corp", "corporation", "company", "co", "ltd", "limited", "plc", "holdings"}


def _selected_issuer_mentioned(text: str, symbol: str | None, company_name: str | None) -> bool:
    upper = text.upper()
    ticker = (symbol or "").strip().upper().lstrip("$")
    if len(ticker) >= 2 and re.search(rf"(?<![A-Z0-9])\$?{re.escape(ticker)}(?![A-Z0-9])", upper):
        return True
    normalized = re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
    if company_name:
        name = re.sub(r"[^a-z0-9]+", " ", company_name.casefold()).strip()
        if len(name) >= 4 and name in normalized:
            return True
        aliases = [word for word in name.split() if len(word) >= 4 and word not in LEGAL_SUFFIXES]
        if any(re.search(rf"\b{re.escape(alias)}\b", normalized) for alias in aliases):
            return True
    return False


def classify_headline(text: str, symbol: str | None = None,
                      company_name: str | None = None) -> dict:
    """Return conservative three-way polarity with issuer relevance and evidence."""
    normalized = re.sub(r"([.!?;:,])", " | ", text.lower())
    normalized = re.sub(r"[^a-z0-9' |\-]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    token_matches = list(re.finditer(r"\||[a-z0-9]+(?:'[a-z]+)?", normalized))
    tokens = [match.group(0) for match in token_matches]
    bull = 0.0
    bear = 0.0
    evidence = []
    phrase_spans = []

    phrases = [(phrase, weight, 1) for phrase, weight in BULL_PHRASES.items()]
    phrases += [(phrase, weight, -1) for phrase, weight in BEAR_PHRASES.items()]
    for phrase, weight, polarity in sorted(phrases, key=lambda item:len(item[0]), reverse=True):
        start = 0
        while True:
            match = re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", normalized[start:])
            if match is None:
                break
            position = start + match.start()
            prefix = normalized[:position].rsplit("|", 1)[-1].split()[-4:]
            negated = any(word in NEGATORS for word in prefix) and "not only" not in " ".join(prefix)
            adjusted = -polarity if negated else polarity
            if adjusted > 0:
                bull += weight
            else:
                bear += weight
            evidence.append(("Bullish" if adjusted > 0 else "Bearish", phrase, weight))
            phrase_spans.append((position, position + len(phrase)))
            start = position + len(phrase)

    for index, (word_match, word) in enumerate(zip(token_matches, tokens)):
        if word == "|":
            continue
        if any(start <= word_match.start() and word_match.end() <= end for start, end in phrase_spans):
            continue
        polarity = 1 if word in BULL_WORDS else -1 if word in BEAR_WORDS else 0
        if not polarity:
            continue
        nearby_tokens = tokens[max(0,index-3):min(len(tokens),index+4)]
        if "|" in nearby_tokens:
            nearby_tokens = nearby_tokens[nearby_tokens.index("|")+1:]
        nearby = set(nearby_tokens)
        if word in {"beat", "beats", "miss", "misses", "missed"} and not nearby.intersection({"earnings","estimate","estimates","expectations","eps","revenue","forecast"}):
            continue
        previous = tokens[max(0,index-3):index]
        if "|" in previous:
            previous = previous[previous.index("|")+1:]
        negated = any(token in NEGATORS for token in previous) and "not only" not in " ".join(previous)
        weight = BULL_WORDS[word] if polarity > 0 else BEAR_WORDS[word]
        if any(token in INTENSIFIERS for token in previous):
            weight *= max(INTENSIFIERS[token] for token in previous if token in INTENSIFIERS)
        adjusted = -polarity if negated else polarity
        if adjusted > 0:
            bull += weight
        else:
            bear += weight
        evidence.append(("Bullish" if adjusted > 0 else "Bearish", word, weight))

    difference = bull - bear
    signal_mass = bull + bear
    margin = abs(difference) / signal_mass if signal_mass else 0.0
    selected_issuer_match = _selected_issuer_mentioned(text, symbol, company_name)
    issuer_context = any(token in ISSUER_CONTEXT for token in tokens)
    broad_market_headline = bool(MARKET_CONTEXT.search(text))
    relevant = selected_issuer_match or (issuer_context and not broad_market_headline)

    # Weak cues, conflicting cues, and broad-market stories without a clear
    # selected-company link are neutral instead of being forced into Bearish.
    directional = relevant and signal_mass >= 1.5 and margin >= 0.35
    label = ("Bullish" if difference > 0 else "Bearish") if directional else "Neutral"
    strength = ("High" if signal_mass >= 4.0 and margin >= 0.65 else
                "Medium" if signal_mass >= 1.5 and margin >= 0.4 else "Low") if directional else "Low"
    leading = []
    for side, phrase, _ in sorted(evidence, key=lambda item:item[2], reverse=True):
        if side == label and phrase not in leading:
            leading.append(phrase)
        if len(leading) == 2:
            break
    if label == "Neutral":
        if not relevant:
            reason = "broad-market or unrelated wording; no clear selected-company link"
        elif signal_mass >= 1.5 and margin < 0.35:
            reason = "bullish and bearish cues conflict"
        else:
            reason = "no strong company-specific directional evidence"
    else:
        reason = ", ".join(leading) if leading else "directional language"
    return {"label":label, "confidence":strength, "bull_score":bull, "bear_score":bear,
            "reason":reason, "issuer_relevant":relevant}


def classify_news_topic(text: str) -> str:
    lowered = text.lower()
    topics = [
        ("Earnings & guidance", ("earnings", "quarter", "revenue", "eps", "guidance", "outlook", "forecast")),
        ("Analyst activity", ("analyst", "price target", "upgrade", "downgrade", "rating")),
        ("Products & deals", ("launch", "product", "partnership", "contract", "acquisition", "deal", "customer")),
        ("Legal & regulatory", ("lawsuit", "court", "sec ", "regulator", "investigation", "antitrust", "recall", "approval")),
        ("Capital & leadership", ("dividend", "buyback", "offering", "shares", "ceo", "resigns", "layoffs")),
    ]
    for label, terms in topics:
        if any(term in lowered for term in terms):
            return label
    return "Company news"
