# Disclaimer

**stock-helper is a research aid. It is not investment advice.**

- Nothing this software produces is a recommendation to buy, sell, or hold any
  security. There are intentionally **no buy/sell/hold labels** anywhere in the
  application.
- Signals are transparent, rule-based descriptions of disclosed financial data.
  They describe *what the filings say*, not *what a stock will do*.
- No signal in this application has been backtested. **No predictive accuracy is
  claimed or implied.** The roadmap gates any performance statement behind a
  validation phase (walk-forward testing with cost assumptions and
  multiple-testing controls) that has not been built.
- Outputs distinguish four things, and you should too when reading them:
  - **Fact** — a value as filed with the SEC (with accession and filed date).
  - **Calculation** — arithmetic over facts (formula shown in SIGNAL_DEFINITIONS.md).
  - **Interpretation** — a plain-English reading of a calculation ("evidence
    suggests margins are compressing"). Always accompanied by a caveat.
  - **Speculation** — not produced by this tool.
- Data can be wrong. SEC XBRL data is "as filed" by registrants; companies restate,
  amend, and use custom tags. Prices from the optional connector are explicitly
  non-canonical. Every metric shows a confidence level and caveats for this reason.
- You are responsible for your own investment decisions. Consult a qualified
  financial adviser for advice.
