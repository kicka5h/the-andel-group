# Case Study: The Andel Group Website

**Client:** The Andel Group
**Industry:** Property Management
**Domain:** andel.ca
**Stack:** FastAPI · SQLAlchemy · MySQL · HTML/CSS · Apache · Let's Encrypt

---

## Overview

The Andel Group is a Canadian property management company providing services to both landlords and residents. Per the client "As property managers we provide clean and safe spaces for tenants and we help landlords get a return on their investment." They required a professional public-facing website that could also serve as an operational platform for residents — supporting secure login, a communication channel through a newsletter, and a direct contact flow for owner and tenant inquiries. The website would be hosted on a previously obtained domain "andel.ca".

---

## Challenge

The client needed a single platform that addressed three distinct audiences with different needs:

- **Prospective clients and residents** — a polished marketing site that communicates trust and professionalism
- **Property owners** — a contact channel and newsletter subscription to stay informed on market trends and portfolio updates
- **Current residents** — a secure login portal as the foundation for future self-service features (rent payment, maintenance requests, lease documents)

The platform also needed to run on an existing LAMP server without introducing unnecessary infrastructure complexity, and had to be maintainable by a small internal team.

---

## Solution

A single FastAPI application serves both the REST API and the static frontend, eliminating the need for a separate web server or CDN for development and keeping the production architecture simple: one systemd service behind an Apache reverse proxy.

### Marketing Site

A multi-section single-page design (`index.html`) covering the company's hero, services, about, portfolio, and contact sections. Fully static HTML and CSS — no JavaScript framework — keeping the site fast and easy to maintain. Key statistics (units managed, occupancy rate, years of experience) are displayed prominently to establish credibility.

### Contact Form

An inquiry form allows property owners and prospective residents to submit questions directly from the site. Submissions are stored in the database with a timestamp and originating IP address. The endpoint is rate-limited to 5 submissions per hour per IP to prevent abuse. The form provides inline status feedback (success, validation errors, rate limit, and network failure) without a page reload.

### Newsletter

Subscribers can sign up at `/newsletter.html` providing their name, role (owner, resident, prospective buyer, industry professional, or other), and topic interests (market trends, community news, investment, maintenance, regulations, listings). Subscriptions are stored with a soft-delete pattern — unsubscribing marks the record inactive rather than deleting it, preserving the audit trail and allowing re-subscription.

A CLI script (`scripts/send_newsletter.py`) queries active subscribers and sends the newsletter via the server's local Postfix mail service. An `--dry-run` flag prints the recipient list without sending, allowing the team to verify the audience before each monthly send. An HTML email template with a personalised greeting token (`{{greeting}}`) is provided and updated each edition.

### Resident Login

Three authentication methods are supported from a single login page:

- **Email and password** — passwords are hashed with bcrypt and never stored in plain text. Successful login returns a signed JWT stored in `localStorage` (persistent) or `sessionStorage` (session-only) based on a "Keep me signed in" checkbox.
- **Sign in with Google** — OAuth 2.0 via Google Cloud Console, activated by setting two environment variables.
- **Sign in with Microsoft** — OAuth 2.0 via Azure Active Directory, activated the same way.

OAuth providers are conditionally registered at startup — if credentials are not configured, those routes simply do not exist, so the app runs cleanly without all providers enabled.

Login is rate-limited to 10 attempts per minute and registration to 5 per hour using `slowapi`. Rate limit errors surface as a human-readable message in the UI rather than a raw HTTP error.

### Resident Portal

A protected dashboard at `/portal.html` verifies the JWT on every load via `GET /api/auth/me`. Unauthenticated users are redirected to login immediately. OAuth logins arrive at the portal via a `?token=` query parameter, which is absorbed into storage and stripped from the URL before the session check runs — preventing the token from appearing in browser history.

The portal is a template with placeholder cards for future resident self-service features: Pay Rent, Maintenance Request, Lease Documents, Notices & Announcements, Contact Manager, and Account Settings.

---

## Technical Decisions

**Single-server architecture.** FastAPI serves both the API and static files from one process. This avoids CORS complexity in development, simplifies the Apache configuration, and keeps the operational footprint small for a team that does not have dedicated DevOps resources.

**SQLAlchemy with `create_all`.** Schema migrations run automatically on startup via `Base.metadata.create_all`. For a project of this scale, this eliminates the overhead of a migration tool while still allowing a transition to Alembic later if the schema grows significantly.

**Conditional OAuth registration.** Providers are only registered if their environment variables are present. This keeps the development environment simple and avoids startup errors when credentials are not yet configured.

**Postfix for email.** Rather than introducing a third-party email API dependency, the newsletter sender uses the server's local Postfix instance. This keeps sending costs at zero and gives the team direct control over delivery, at the cost of requiring SPF/DKIM/DMARC DNS configuration for reliable inbox placement.

**No JavaScript framework.** The frontend is plain HTML, CSS, and vanilla JavaScript. Pages load instantly, there is no build step, and any developer can read and modify the templates without framework-specific knowledge.

---

## Deployment Architecture

```
Internet
    │
    ▼
Apache (port 443, HTTPS via Let's Encrypt)
    │  reverse proxy
    ▼
uvicorn / FastAPI (127.0.0.1:8000, systemd service)
    │
    ├── /api/*     REST API (auth, OAuth, newsletter, contact, health)
    └── /*         Static files (index.html, login.html, portal.html, CSS, assets)
    │
    ▼
MySQL 8 (localhost)
    └── tables: users · subscribers · contact_submissions
```

The application runs as a systemd service under the `www-data` user, restarts automatically on failure, and reads all secrets from an `.env` file excluded from version control.

---

## Outcomes

| Area | Result |
| --- | --- |
| Public site | Responsive marketing site live at andel.ca |
| Contact | Form submissions stored in database, rate-limited |
| Newsletter | Subscriber database with monthly send tooling |
| Authentication | Three sign-in methods with JWT session management |
| Resident portal | Protected dashboard scaffolded for future features |
| Security | HTTPS, bcrypt, rate limiting, environment-based secrets |
| Documentation | Full deployment guide (SETUP.md), API docs (Swagger/ReDoc), session flow diagram |
