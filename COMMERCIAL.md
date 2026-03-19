# AgentReach Commercial Model

AgentReach is open source and always will be. The core is free. We build revenue on top through Pro and Enterprise tiers that serve teams who need more.

---

## Free Tier (Open Source — Current State)

**Who it's for:** Individual developers, AI builders, hobbyists, single-person operations.

**What's included:**
- Full source code (MIT licensed)
- All current platform drivers: KDP, Etsy, Gumroad, Pinterest
- Encrypted local session vault (AES-256)
- CLI tool (`agentreach`)
- Headless browser automation (Playwright)
- React upload bypass engine
- Session health monitoring
- OpenClaw skill integration
- Community support (GitHub Issues, Discord)

**Limits:**
- Local machine only — sessions don't sync to other devices
- Personal use — no team sharing
- Community support only
- New platform drivers depend on community contributions

---

## Pro Tier — $29/month

**Who it's for:** Serious builders, small studios, AI freelancers running multiple client operations.

**What's included (everything in Free, plus):**

### Cloud Session Sync
- Encrypted session vault syncs across devices
- Log in once on your laptop, use from your server
- End-to-end encrypted — we never see your sessions
- Up to 3 devices per account

### Team Vaults
- Share sessions with up to 3 team members
- Role-based access: Owner, Editor, Viewer
- Audit log: who used what session when
- Session revocation: instantly cut access for departed team members

### Priority Driver Updates
- New platform drivers before community release
- Drivers maintained and tested by the core team
- Faster session format updates when platforms change their auth

### Priority Support
- Direct email support (48h response)
- Private Discord channel
- Bug reports prioritized over community queue

### Platform Drivers (Pro-first)
These ship to Pro before going open source:
- LinkedIn
- Shopify
- Substack
- Medium
- YouTube Studio
- Twitter/X posting

### Monitoring Dashboard (coming Q3 2026)
- Web UI for session health across all platforms
- Alert configuration (email/Telegram when sessions expire)
- Usage logs per platform

---

## Enterprise Tier — Custom Pricing

**Who it's for:** Agencies, AI companies, teams with compliance needs, white-label builders.

**What's included (everything in Pro, plus):**

### Custom Drivers
- We build a driver for any platform you need
- Dedicated engineering time
- Full handoff with tests and documentation
- Ongoing maintenance included

### White-Label
- Remove AgentReach branding entirely
- Your company name in the CLI, UI, and docs
- Custom domain for session sync API
- OEM licensing

### On-Premise Deployment
- Run the sync server on your infrastructure
- Never touches our cloud
- Full data sovereignty

### SLA
- 99.9% uptime guarantee for sync API
- 4-hour response SLA for critical issues
- Dedicated Slack channel with core team

### Team Scale
- Unlimited team members
- Unlimited devices
- SSO/SAML integration
- Enterprise audit logs

**Pricing:** Starting at $299/month. Contact josh@tenlifecreatives.com.

---

## Revenue Strategy

### Phase 1 (Q2-Q3 2026): Build the user base
- Keep core free and genuinely excellent
- Get to 500 GitHub stars (social proof matters)
- Launch Pro when we have 50+ active free users asking for team features
- Target: $500/month from Pro subscriptions by end of Q3

### Phase 2 (Q4 2026): Enterprise conversations
- Identify 3-5 AI agencies or teams building on AgentReach
- Offer white-label deals at reduced pricing for case studies
- Target: 2-3 Enterprise clients at $299+/month

### Phase 3 (2027): Platform
- Driver marketplace — community builds, Pro users get early access
- Revenue share with community driver authors
- Potential acquisition target for any AI infrastructure company

---

## Competitive Moat

AgentReach's defensibility comes from:

1. **Real sessions, not APIs** — When platforms lock down APIs, AgentReach still works because it operates like a human. This is hard to replicate without Playwright expertise.

2. **React upload bypass** — Solved a genuinely unsolved problem. Anyone building AI agents on React-heavy platforms needs this.

3. **OpenClaw integration** — First-mover in the OpenClaw ecosystem. Skills marketplace creates distribution.

4. **Switching cost** — Once a team has their sessions in an AgentReach vault and built workflows on it, switching is painful. The vault format is the moat.

---

## Pricing Philosophy

The free tier must be genuinely, non-crippled useful. Not a trial. Not a demo.
If someone is a solo builder who never needs cloud sync, they should never need to pay.
We charge for features that are actually worth paying for: team collaboration, scale, and peace of mind.

We don't: limit platforms, cap API calls, or add artificial restrictions to the free tier.
We do: charge for infrastructure (sync), time (support), and expertise (custom drivers).
