# How to Demo the Andel Group Website

This guide covers how to share a live, fully functional preview of the site with a client using ngrok.

---

## Prerequisites

- The project is set up locally and the server runs without errors
- See [README.md](README.md) for local development setup

---

## 1. Install ngrok

```bash
brew install ngrok
```

## 2. Create a free ngrok account

Sign up at [ngrok.com](https://ngrok.com) and copy your authtoken from the dashboard.

## 3. Configure the authtoken (one time only)

```bash
ngrok config add-authtoken <your-token>
```

## 4. Start the app

```bash
source .venv/bin/activate
uvicorn app.main:app --port 8000
```

## 5. Start the tunnel

In a second terminal:

```bash
ngrok http 8000
```

ngrok will display a public URL:

```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

Share that URL with the client.

---

## What the client can see and do

All features are fully functional over the ngrok URL:

- **Main site** — marketing pages, services, portfolio, contact form
- **Newsletter** — subscribe and unsubscribe at `/newsletter.html`
- **Resident login** — email/password login at `/login.html`
- **Resident portal** — protected dashboard at `/portal.html`

> To create a test resident account for the demo, see [README.md — Creating a test user](README.md#creating-a-test-user). Remember to set `REGISTRATION_SECRET` in `.env` first.

---

## Things to know

**The URL changes every session.** Each time you restart the ngrok tunnel, you get a new URL. You will need to share the new URL with the client each session. A paid ngrok plan allows a fixed custom domain.

**First-time visitors see a browser warning.** ngrok displays a "Visit Site" interstitial the first time someone opens the URL. The client clicks the button once to proceed — this does not happen on repeat visits.

**Sessions time out.** The free tier tunnel will close after a few hours of inactivity. Restart with `ngrok http 8000` to get a new URL.

**The API docs are automatically blocked externally.** `/docs`, `/redoc`, and `/openapi.json` return 403 for any request that does not originate from the host server. They remain accessible at `http://localhost:8000/docs` for development.

**Keep your terminal open.** Both the uvicorn server and the ngrok tunnel must stay running for the demo to be accessible. Closing either terminal will take the site offline.
