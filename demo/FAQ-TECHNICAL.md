# AgentReach — Technical FAQ

Anticipated tough questions with honest answers. Credibility over completeness.

---

## "Why doesn't [platform] detect this as a bot?"

**Short answer:** It sometimes does. When it doesn't, here's why.

AgentReach replays a **real authenticated human session** — the cookies and localStorage from an actual human login on actual Chrome. From the server's perspective, requests arrive with:

1. Real session cookies (not constructed auth headers)
2. A real Chromium TLS fingerprint (not an HTTP client like requests or curl)
3. A plausible User-Agent string
4. Cookies scoped to the correct domain/path with correct HttpOnly and Secure flags

Platforms primarily detect bots via:
- **Behavioral signals**: typing cadence, mouse movement, scroll patterns, time-on-page
- **IP reputation**: datacenter IPs vs. residential IPs
- **Browser fingerprint anomalies**: missing plugins, wrong WebGL strings, `navigator.webdriver = true`
- **Request rate anomalies**: too many requests per second, unnaturally consistent timing
- **Challenge-based detection**: CAPTCHAs, JavaScript puzzles (Cloudflare, reCAPTCHA)

AgentReach with `playwright-stealth` addresses the browser fingerprint anomalies. It does nothing about behavioral signals (because operations are automated, not simulated-human), IP reputation, or challenges.

**The reason it often succeeds anyway:** These platforms are primarily detecting mass account creation bots, credential stuffing attacks, and scraping at scale. A single authenticated session performing one operation per day looks nearly indistinguishable from a human user — especially when the session was created by a real human login in the first place.

---

## "What happens when playwright-stealth gets detected?"

The operation fails. The page may return a CAPTCHA challenge, a "suspicious activity" interstitial, or simply redirect to the login page.

`playwright-stealth` is a known project with a known fingerprint. Sophisticated bot detection services (Cloudflare Bot Management, Akamai Bot Manager, DataDome) have published detection logic for it. The patches `playwright-stealth` makes are themselves detectable:
- The override of `navigator.plugins` with fake plugin data is non-trivial to perfectly mimic
- Permission API overrides leave traces in certain browser behavior tests
- WebGL spoofing can be detected by cross-referencing with reported GPU vendor

**What we do about it:** This is why `playwright-stealth` is an optional dependency. It's applied when available but we don't build our entire detection-evasion strategy around it. Our primary defense is using real session cookies from a real human login — which is harder to detect than constructed sessions.

**Long-term:** If a platform adds robust bot detection that consistently blocks AgentReach, we will need to document that platform as "unsupported for headless operation" and require more frequent re-harvest or manual operations. We will not try to build an arms race with Cloudflare.

---

## "How is this different from just using Selenium?"

Four concrete differences:

**1. Session harvest model vs. always-headful**  
Selenium-based tools typically automate the login itself (store credentials, replay form fill). AgentReach separates harvest (human-driven, one-time) from replay (machine-driven, repeatable). This means credentials are never stored — only post-authentication state.

**2. Playwright vs. Selenium WebDriver**  
Playwright uses Chrome DevTools Protocol directly. Selenium uses WebDriver (W3C standard, which Playwright helped inform). CDP gives Playwright access to:
- `Input.setFiles` (used in upload Strategy 1)
- `Page.fileChooserOpened` (used in upload Strategy 3)
- `Network.setCookies` (used in session restoration)
- Full `storage_state` serialization/restoration

Selenium does not expose these. Session state restoration in Selenium requires `driver.get(url)` first, then `driver.add_cookie()` per cookie — no localStorage support.

**3. Async-native**  
Playwright is async-native (asyncio). Selenium's async support is bolted on. For operations that launch multiple parallel browser contexts (multiple platforms simultaneously), async matters.

**4. Platform-specific drivers**  
AgentReach has opinionated, versioned drivers for each platform — not generic browser automation. The KDP driver knows the KDP DOM structure, the Reddit driver knows the Reddit DOM structure. Selenium gives you a browser; AgentReach gives you platform actions.

---

## "Why not use official APIs instead?"

Where official APIs exist and are sufficient, we use them:

- **Gumroad**: uses the official Gumroad API (`api.gumroad.com/v2/products`)
- **Etsy**: uses the official Etsy Open API v3 with OAuth

Where official APIs do not exist or are insufficient:

- **Amazon KDP**: There is no public KDP API for creating or managing print books. Amazon has APIs for Kindle Direct Publishing on the Kindle side, but paperback title creation is browser-only.
- **Pinterest**: The Pinterest API v5 supports pins and boards, but with significant rate limiting and approval requirements for non-approved apps. Browser automation is faster to bootstrap for individual users.
- **Reddit**: The Reddit API exists but was heavily restricted in 2023 (killing third-party apps). Rate limits, API key approval, and rate limiting make it less attractive for low-volume personal use.
- **Twitter/X**: The API tiers since 2023 charge $100/month for basic write access. Browser automation of your own account is free.
- **Nextdoor**: No public API exists.

The honest answer is: APIs are used where they exist and are accessible. Browser automation is the fallback. This is the same reasoning behind tools like Buffer's Pinterest integration or IFTTT's Twitter integration — when platforms don't provide accessible APIs, browser automation fills the gap.

---

## "What's your session expiry rate?"

We estimate based on published platform behavior and user reports. These are estimates, not guarantees:

| Platform | Estimated Session TTL | Notes |
|----------|----------------------|-------|
| KDP      | 30 days | Amazon aggressively invalidates sessions |
| Etsy     | 45 days | More lenient; varies by activity |
| Gumroad  | 60 days | API tokens don't expire; browser sessions do |
| Pinterest| 60 days | Generally stable |
| Reddit   | 90 days | Long-lived sessions |
| Twitter  | 21 days | Conservative estimate; varies widely |
| Nextdoor | 30 days | Anecdotal |

**Real-world observation:** Sessions often last longer than estimated when the account is actively used (which ours are, by definition). Sessions expire faster when:
- The user logs in from a different IP concurrently
- The platform detects unusual activity
- The user changes their password
- The platform pushes a forced re-authentication event

The `agentreach doctor` command and the session monitor warn when sessions approach expiry. Re-harvest takes about 2 minutes.

---

## "How do you handle 2FA?"

**During harvest:** The browser is visible and human-controlled. The human handles 2FA exactly as they would in a regular browser. AgentReach waits up to 5 minutes (configurable). This works for all 2FA types: SMS, authenticator apps, hardware keys, push notifications.

**During headless replay:** We don't handle mid-session 2FA challenges. If a platform triggers a 2FA prompt during a headless operation (unusual but possible), the operation fails. The session health checker will catch this as an invalid session and prompt re-harvest.

**Amazon step-up auth:** This is specifically handled in the KDP harvester. Amazon requires step-up authentication (essentially a fresh 2FA/password confirmation) for sensitive operations like title creation. We solve this by having the human navigate to the title creation form during harvest, capturing the deeper auth cookies at that point.

---

## "What about CAPTCHA?"

**During harvest:** Human-visible browser — the human solves any CAPTCHA as they normally would.

**During headless replay:** We do not handle CAPTCHAs. If a CAPTCHA is presented during headless operation, the operation fails.

**We will not integrate CAPTCHA-solving services.** This is a deliberate choice. CAPTCHA-solving services (2captcha, Anti-CAPTCHA, CapSolver) either:
1. Route CAPTCHAs to human solvers for pennies (ethically questionable, adds cost and latency)
2. Use ML to bypass them (arms race with CAPTCHA providers, increasingly ineffective)

For the target use case — one person automating their own legitimate accounts — CAPTCHAs during headless replay are rare. If they become frequent for a platform, that platform's driver should be flagged as degraded.

---

## "Isn't this against ToS?"

**Honest answer: probably, in the strict reading. Practically: it depends on what you're doing.**

Most platform ToS prohibit "automated access" or "bots" in some form. For example:
- Amazon's Conditions of Use prohibit "use any robot, spider, scraper, or other automated means to access the Service"
- Twitter's ToS prohibit "using automated means to create accounts, post tweets, or perform other actions"
- Reddit's ToS prohibit "using automated methods to access Reddit in a manner that violates these Terms"

However, the context matters:

**What these clauses are designed to prevent:**
- Mass account creation
- Scraping content for resale
- Manipulation (fake engagement, coordinated inauthentic behavior)
- Denial-of-service via high-volume requests

**What AgentReach does:**
- Automates a single human's legitimate account
- Performs actions the human would do manually
- Low volume (one operation at a time, not bulk API calls)
- No scraping of others' content for resale

This is the same legal/ethical territory as browser extensions (many of which automate interactions), Grammarly (injects into web pages), password managers (fill in forms programmatically), and productivity tools like Make/Zapier when they use browser-based integrations.

**The practical risk:** Being suspended or banned from a platform. Not legal liability. Platforms do not generally pursue legal action against individual users automating their own accounts at low volume.

**Our position:** We document this honestly. Users should understand that ToS risk exists. We recommend not using AgentReach for actions that could constitute manipulation or harm to the platform or other users.

---

## "How do you know the session replay actually works and you're not just getting a logged-out page?"

Three verification mechanisms:

**1. `agentreach verify <platform>`**  
Calls the driver's `verify_session()` method, which navigates to a platform-specific authenticated URL and checks for expected content. If the page redirects to login, it returns `False`.

**2. Driver-level health checks**  
Before each operation, drivers call `check_session()` which checks estimated session expiry. If estimated to be expired, the operation fails with `SessionExpiredError` before any browser is launched.

**3. Post-operation assertions**  
Drivers check the outcome URL and DOM state after operations. For example, the KDP driver checks for a success confirmation element after an upload attempt. If the DOM shows a login form instead, the operation is retried or flagged as a session failure.

**What we don't do:** We don't ping the platform's API to verify session validity before every headless operation. This would require an extra network round-trip and could itself trigger rate limiting. Verification is on-demand (via `agentreach verify`) and estimated-TTL-based.

---

## "What's the failure mode if a platform changes their UI?"

The driver fails, usually with a `TimeoutError` from Playwright waiting for a selector that no longer exists.

This is a real limitation of any browser automation approach. UI changes break selectors. We handle this by:

1. **Selector constants at the top of each driver** — easy to find and update
2. **Meaningful error messages** — instead of a raw Playwright timeout, drivers catch and re-raise with context ("Could not find title input field — KDP UI may have changed")
3. **Test coverage** — 230 unit tests catch selector regressions in mocked environments

What we don't have: automatic UI change detection or visual diffing. When a platform changes its UI, a human needs to update the driver. This is labor — it's a real cost of browser automation.

---

## "Why 230 tests for what is essentially a wrapper around Playwright?"

Because the edge cases are where the bugs live:

- What happens when the vault file exists but was encrypted on a different machine?
- What happens when a platform name contains a path traversal character?
- What happens when `playwright-stealth` is not installed?
- What happens when all 4 upload strategies fail?
- What happens when the harvest times out before login completes?
- What happens when the KDP deep-auth step is skipped?
- What happens when the JSON in a vault file is valid but missing required fields?

Each of these has a test. All 230 pass in 0.37 seconds because all browser and network calls are mocked with `unittest.mock`. The test suite validates business logic, error handling, and edge cases — not that Playwright works (it has its own test suite).
