# The Andel Group Website

Professional property management website for [andel.ca](https://andel.ca), built with a FastAPI backend and static HTML/CSS frontend.

---

## Features

### Main Website

A multi-section marketing site covering the company's services, portfolio, and contact information.

- **Hero** — headline, call-to-action buttons, and key statistics (units managed, occupancy rate, etc.)
- **Services** — residential management, commercial properties, tenant relations, financial reporting, leasing, and maintenance coordination
- **About** — company story and value proposition for owners and residents
- **Portfolio** — showcase of managed communities
- **Contact form** — inquiry form for owners and prospective residents

### Newsletter

Residents, owners, and industry professionals can subscribe to *The Andel Insider*, a monthly email covering market trends, community news, and expert insights.

- Subscribe and unsubscribe via the `/newsletter` page
- Captures name, role, and topic interests
- Subscriptions stored in the database; soft-delete on unsubscribe (re-subscribe supported)
- Monthly sends are handled by `scripts/send_newsletter.py` — see [SETUP.md](SETUP.md#10-sending-the-newsletter)

### Resident Login

A full authentication system at `/login.html` supporting three sign-in methods:

- **Email and password** — bcrypt-hashed passwords, JWT tokens, rate-limited to 10 attempts per minute
- **Sign in with Google** — OAuth 2.0 via Google Cloud Console
- **Sign in with Microsoft** — OAuth 2.0 via Azure Active Directory

Tokens are stored in `localStorage` (persistent) or `sessionStorage` (session-only) depending on the "Keep me signed in" checkbox.

### Resident Portal

A protected dashboard at `/portal.html` that verifies the JWT on every load and redirects unauthenticated users to login.

Placeholder features (ready for implementation):

- Pay Rent
- Maintenance Request
- Lease Documents
- Notices & Announcements
- Contact Manager
- Account Settings

---

## API

The FastAPI backend exposes a REST API at `/api/`. Full interactive documentation is available once the server is running:

| | URL |
| --- | --- |
| **Swagger UI** | `http://localhost:8000/docs` |
| **ReDoc** | `http://localhost:8000/redoc` |
| **OpenAPI JSON** | `http://localhost:8000/openapi.json` |

### Endpoint groups

| Tag | Prefix | Description |
| --- | --- | --- |
| `auth` | `/api/auth` | Register, login, and current-user endpoints |
| `oauth` | `/api/auth` | Google and Microsoft OAuth flows |
| `newsletter` | `/api/newsletter` | Subscribe, unsubscribe, and list subscribers |
| `contact` | `/api/contact` | Contact form submissions |
| `health` | `/api` | Server health check |

---

## Local Development

**Requirements:** Python 3.10+

```sh
# 1. Clone and enter the project
git clone https://github.com/your-org/the-andel-group.git
cd the-andel-group

# 2. Create a virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Copy the example env file and fill in values
cp .env.example .env

# 4. Start the development server
uvicorn app.main:app --reload
```

The site will be available at `http://localhost:8000`.
Swagger UI will be available at `http://localhost:8000/docs`.

### Creating a test user

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@andel.ca", "password": "yourpassword"}'
```

---

## Project Structure

```
/
├── app/                        # FastAPI application
│   ├── main.py                 # App entry point, middleware, routing
│   ├── database.py             # SQLAlchemy engine and session
│   ├── models.py               # Database models (User, Subscriber, ContactSubmission)
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── limiter.py              # slowapi rate limiter instance
│   └── routers/
│       ├── auth.py             # Email/password auth routes
│       ├── oauth.py            # Google and Microsoft OAuth routes
│       ├── newsletter.py       # Newsletter subscription routes
│       └── contact.py          # Contact form routes
├── static/                     # Frontend (served by FastAPI)
│   ├── index.html              # Main marketing site
│   ├── login.html              # Resident login page
│   ├── newsletter.html         # Newsletter sign-up page
│   ├── portal.html             # Resident portal (protected)
│   ├── css/
│   │   ├── styles.css          # Shared design system
│   │   ├── index.css           # Main site styles
│   │   ├── login.css           # Login page styles
│   │   ├── newsletter.css      # Newsletter page styles
│   │   └── portal.css          # Portal styles
│   └── assets/                 # Images
├── scripts/
│   ├── send_newsletter.py      # CLI tool to send the monthly newsletter
│   └── newsletter_template.html # HTML email template
├── requirements.txt
├── .env.example                # Environment variable reference
├── SETUP.md                    # Full server deployment guide
└── SESSION_FLOW.md             # Authentication session flow diagram
```

---

## Deployment

See [SETUP.md](SETUP.md) for the full LAMP server deployment guide, covering:

- Apache reverse proxy configuration
- MySQL database setup
- Systemd service
- HTTPS with Let's Encrypt
- Google and Microsoft OAuth configuration
- Newsletter sending with Postfix
