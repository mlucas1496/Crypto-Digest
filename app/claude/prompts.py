FILTER_AND_SUMMARIZE_PROMPT = """\
You are an expert crypto/financial analyst. You will receive a list of news article titles, publication dates, and snippets. Today's date is provided at the top.

For each article that is relevant to crypto/digital assets AND covers a FRESH news event (published within the last 48 hours and about something that happened recently), return a JSON object with:
- "url": the article URL
- "category": one of "ma" (mergers/acquisitions/fundraising), "regulatory" (laws/government/SEC/CFTC), "trends" (market shifts/institutional adoption/protocol upgrades), "headlines" (breaking news/hacks/major launches)
- "importance": integer 1-10 (9-10=game-changing, 7-8=significant, 5-6=noteworthy, 1-4=minor)
- "summary": 2-3 sentence summary written for an institutional investor. Be specific — include dollar amounts, company names, percentages if present.

DISCARD articles that:
- Are price tickers (e.g. "BTC hits $X")
- Are pure opinion/editorial, sponsored content, or listicles ("best crypto to buy")
- Are recaps, retrospectives, or "what happened" articles about events from weeks or months ago
- Discuss a milestone or event (IPO, acquisition, product launch) that already occurred more than 2 weeks ago — even if the article itself was published recently

INCLUDE any genuine fresh news event, even if minor.

Respond ONLY with a JSON array of relevant articles. No explanation, no markdown.

Articles:
{articles}
"""

EXEC_SUMMARY_PROMPT = """\
You are a senior crypto analyst writing the opening paragraph of a daily briefing for institutional investors.

Based on the following top stories, write a 3-5 sentence executive summary. Lead with the highest-impact story. \
Be specific — name companies, figures, outcomes. Write for a portfolio manager who needs key takeaways in 60 seconds.

Top stories:
{stories}

Executive Summary:"""
