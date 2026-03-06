# Developer Setup Guide — The Andel Group Website

This guide walks through deploying the Andel Group website on a LAMP server (Linux, Apache, MySQL, Python). Apache acts as a reverse proxy in front of the FastAPI application, which handles both the API and static file serving.

---

## Requirements

- Ubuntu 22.04 LTS (or equivalent Debian-based distro)
- Apache 2.4+
- MySQL 8.0+ or MariaDB 10.6+
- Python 3.10+
- A registered domain pointing to the server (e.g. `andel.ca`)

---

## 1. Install System Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git apache2 mysql-server
```

Enable required Apache modules:

```bash
sudo a2enmod proxy proxy_http headers rewrite ssl
sudo systemctl restart apache2
```

---

## 2. Set Up the Database

```bash
sudo mysql_secure_installation
sudo mysql -u root -p
```

Inside the MySQL shell:

```sql
CREATE DATABASE andel CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'andel_user'@'localhost' IDENTIFIED BY 'your_strong_password';
GRANT ALL PRIVILEGES ON andel.* TO 'andel_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

---

## 3. Deploy the Application

### Clone the repository

```bash
sudo mkdir -p /var/www/andel
sudo chown $USER:$USER /var/www/andel
git clone https://github.com/your-org/the-andel-group.git /var/www/andel
cd /var/www/andel
```

### Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

```bash
cp .env.example .env
nano .env
```

Fill in the values:

```env
DATABASE_URL=mysql+pymysql://andel_user:your_strong_password@localhost/andel
ALLOWED_ORIGINS=https://andel.ca,https://www.andel.ca

SECRET_KEY=replace-with-output-of-command-below
ACCESS_TOKEN_EXPIRE_MINUTES=60

# OAuth — leave blank to disable a provider
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
MICROSOFT_TENANT_ID=common
```

Generate a secure `SECRET_KEY`:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

> Never commit `.env` to version control — it is already listed in `.gitignore`.

### Production values that must be changed

The following settings have insecure or localhost-only defaults that **must** be updated before going live:

| Setting | Location | Default | What to do |
| --- | --- | --- | --- |
| `ALLOWED_ORIGINS` | `.env` | `http://localhost:8000` | Set to your production domain(s), e.g. `https://andel.ca,https://www.andel.ca`. Used in `app/main.py` to configure CORS. |
| `SECRET_KEY` | `.env` | `"change-me-in-production"` | Generate a cryptographically random value with the command above. Used to sign JWTs and the OAuth session cookie. |
| `COOKIE_SECURE` | `.env` | `false` | Set to `true` in production. Tells the browser to only send the session cookie over HTTPS. Must be `false` if testing over plain HTTP (e.g. localhost). |
| `REGISTRATION_SECRET` | `.env` | *(empty — disabled)* | Set to a random secret to enable account creation. Pass it as the `X-Registration-Secret` header when calling `POST /api/auth/register`. Leave blank to disable registration entirely after initial setup. |
| `ProxyHeadersMiddleware` trusted hosts | `app/main.py` line 50 | `"127.0.0.1"` | Hardcoded in source — only change if Apache is **not** running on the same machine as the app (e.g. a separate load balancer). For the standard LAMP setup described here, `127.0.0.1` is correct and does not need to be changed. |

---

## 5. Create Database Tables

With the virtual environment active, run a one-time migration:

```bash
source .venv/bin/activate
python3 -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

---

## 6. Run as a Systemd Service

Create a service file so the application starts automatically and restarts on failure:

```bash
sudo nano /etc/systemd/system/andel.service
```

Paste the following (adjust paths if needed):

```ini
[Unit]
Description=The Andel Group FastAPI Application
After=network.target mysql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/andel
EnvironmentFile=/var/www/andel/.env
ExecStart=/var/www/andel/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo chown -R www-data:www-data /var/www/andel
sudo systemctl daemon-reload
sudo systemctl enable andel
sudo systemctl start andel
sudo systemctl status andel
```

### Block direct access to the application port

The app listens on `127.0.0.1:8000`, but if your firewall allows inbound traffic on port 8000, clients can bypass Apache entirely — defeating rate limiting (which relies on `X-Forwarded-For`) and any future IP-based rules. Block it:

```bash
sudo ufw deny 8000
sudo ufw status
```

> If `ufw` is not active, enable it first: `sudo ufw enable`. Ensure port 22 (SSH), 80 (HTTP), and 443 (HTTPS) are allowed before enabling the firewall.

---

## 7. Configure Apache as a Reverse Proxy

Create a virtual host configuration:

```bash
sudo nano /etc/apache2/sites-available/andel.conf
```

```apache
<VirtualHost *:80>
    ServerName andel.ca
    ServerAlias www.andel.ca

    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    RequestHeader set X-Forwarded-Proto "http"

    ErrorLog ${APACHE_LOG_DIR}/andel_error.log
    CustomLog ${APACHE_LOG_DIR}/andel_access.log combined
</VirtualHost>
```

Enable the site:

```bash
sudo a2ensite andel.conf
sudo a2dissite 000-default.conf
sudo systemctl reload apache2
```

---

## 8. Enable HTTPS with Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-apache
sudo certbot --apache -d andel.ca -d www.andel.ca
```

Certbot will automatically update the Apache config and set up certificate renewal. Verify auto-renewal works:

```bash
sudo certbot renew --dry-run
```

After enabling HTTPS, update `.env`:

```env
ALLOWED_ORIGINS=https://andel.ca,https://www.andel.ca
```

Then restart the service:

```bash
sudo systemctl restart andel
```

---

## 9. Verify the Deployment

```bash
# Check the application is running
sudo systemctl status andel

# Check the health endpoint
curl https://andel.ca/api/health

# Tail application logs
sudo journalctl -u andel -f
```

The site should now be live at `https://andel.ca`.

---

## 10. Sending the Newsletter

The `scripts/` directory contains a Python script that queries the subscriber database and sends the newsletter via the server's local mail service (Postfix).

### 10a. Install and Configure Postfix

If Postfix is not already installed:

```bash
sudo apt install -y postfix
```

During setup, choose **Internet Site** and enter your domain (`andel.ca`). Postfix will handle outbound mail on `localhost:25`. To verify it is running:

```bash
sudo systemctl status postfix
```

Set the sender hostname so outgoing mail identifies your domain:

```bash
sudo nano /etc/postfix/main.cf
```

Ensure these lines are present:

```
myhostname = andel.ca
myorigin = andel.ca
```

```bash
sudo systemctl reload postfix
```

> **SPF / DKIM / DMARC**: Configure DNS records for your domain before sending to real subscribers, or major providers (Gmail, Outlook) will reject or spam-folder your mail. Your hosting provider or DNS registrar will have instructions specific to your setup.

### 10b. Edit the Newsletter Template

The template is at `scripts/newsletter_template.html`. Open it in any text editor and replace the placeholder sections:

- Update the edition date in the hero block
- Replace the `[Replace this with ...]` paragraphs with your content
- The `{{greeting}}` token is automatically replaced with the subscriber's first name (or "Hello," if not provided)

### 10c. Preview Recipients (Dry Run)

Always run with `--dry-run` first to confirm the recipient list before sending:

```bash
cd /var/www/andel
source .venv/bin/activate
python3 scripts/send_newsletter.py \
  --subject "The Andel Insider — March 2026" \
  --body scripts/newsletter_template.html \
  --dry-run
```

This prints every subscriber's email address without sending anything.

### 10d. Send the Newsletter

When you are satisfied with the preview:

```bash
python3 scripts/send_newsletter.py \
  --subject "The Andel Insider — March 2026" \
  --body scripts/newsletter_template.html
```

The script prints `[OK]` or `[FAIL]` for each address and a final summary line.

### 10e. Schedule Monthly Sends with Cron (Optional)

To send automatically on the first of each month at 9 AM server time:

```bash
sudo crontab -e -u www-data
```

Add this line:

```
0 9 1 * * /var/www/andel/.venv/bin/python3 /var/www/andel/scripts/send_newsletter.py \
  --subject "The Andel Insider" \
  --body /var/www/andel/scripts/newsletter_template.html \
  >> /var/log/andel_newsletter.log 2>&1
```

> The subject line and template must be updated before the cron job fires each month. For fully automated sends, consider maintaining a dated template per edition.

---

## 11. Resident Login Authentication

The login page (`/login.html`) supports three sign-in methods. Each requires backend routes and configuration before the buttons become functional. Choose the methods you want to enable — they can be set up independently.

All three methods share the same dependency set, which is already included in `requirements.txt` and installed in Section 3. Ensure the auth variables in `.env` are filled in before proceeding (see Section 4).

---

### 11a. Email and Password Login

This is the traditional username/password flow. Passwords are never stored in plain text — only a bcrypt hash is saved to the database.

#### Create the users table

The `User` model is already defined in `app/models.py`. Run the migration to create the table:

```bash
cd /var/www/andel
source .venv/bin/activate
python3 -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

#### Connect the auth router

The router is implemented at `app/routers/auth.py` and is already registered in `app/main.py`. It exposes four endpoints:

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/auth/register` | Creates a new user. Requires the `X-Registration-Secret` header. Accepts `{"email": "...", "password": "..."}` (minimum 8-character password). |
| `POST` | `/api/auth/login` | Accepts `{"email": "...", "password": "...", "remember_me": true}`. Sets an `httpOnly` session cookie on success. |
| `POST` | `/api/auth/logout` | Clears the session cookie. |
| `GET` | `/api/auth/me` | Reads the session cookie. Returns the current user's profile. |

JWTs are stored in an `httpOnly` cookie (`andel_token`) — never in `localStorage` or `sessionStorage`, making them inaccessible to JavaScript and immune to XSS. The `remember_me` flag controls whether the cookie is persistent (survives browser restarts) or session-only.

#### Creating the first account

Set `REGISTRATION_SECRET` in `.env`, then register via curl:

```bash
curl -X POST https://andel.ca/api/auth/register \
  -H "Content-Type: application/json" \
  -H "X-Registration-Secret: your-registration-secret" \
  -d '{"email": "admin@andel.ca", "password": "yourpassword"}'
```

After creating all required accounts, clear `REGISTRATION_SECRET` from `.env` and restart the service to disable registration:

```bash
sudo systemctl restart andel
```

---

### 11b. Sign In with Google

#### Register your app with Google

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project (or select an existing one).
2. Navigate to **APIs & Services → OAuth consent screen**.
   - Choose **External** user type.
   - Fill in the app name ("The Andel Group Resident Portal"), support email, and developer contact.
   - Add the scope `openid`, `email`, and `profile`.
3. Navigate to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**.
   - Application type: **Web application**.
   - Authorised JavaScript origins: `https://andel.ca`
   - Authorised redirect URIs: `https://andel.ca/api/auth/google/callback`
4. Copy the **Client ID** and **Client Secret** into `.env`:

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

#### Connect the Google OAuth router

The Google routes are implemented in `app/routers/oauth.py` and registered in `app/main.py`. Once `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in `.env`, the provider activates automatically on next restart — no code changes needed.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/auth/google` | Redirects the browser to Google's consent screen. |
| `GET` | `/api/auth/google/callback` | Receives the authorization code from Google, looks up or creates the user, and redirects to `/portal.html?token=<jwt>`. |

`SessionMiddleware` is already configured in `app/main.py` to handle the OAuth state parameter securely. The Google button in `static/login.html` is already enabled and points to `/api/auth/google`.

---

### 11c. Sign In with Microsoft

#### Register your app in Azure

1. Sign in to the [Azure Portal](https://portal.azure.com/) and go to **Azure Active Directory → App registrations → New registration**.
   - Name: `Andel Resident Portal`
   - Supported account types: **Accounts in any organizational directory and personal Microsoft accounts** (allows both work and personal accounts).
   - Redirect URI: **Web** — `https://andel.ca/api/auth/microsoft/callback`
2. After registration, note the **Application (client) ID** and **Directory (tenant) ID** from the Overview page.
3. Go to **Certificates & secrets → New client secret**. Copy the secret value immediately — it will not be shown again.
4. Add to `.env`:

```env
MICROSOFT_CLIENT_ID=your-application-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret-value
MICROSOFT_TENANT_ID=common
```

> Use `common` as the tenant ID to allow both personal and work/school Microsoft accounts. Replace with your specific tenant ID to restrict to a single Azure AD organisation.

#### Connect the Microsoft OAuth router

The Microsoft routes follow the same pattern as Google and live in the same `app/routers/oauth.py` file. Once `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, and `MICROSOFT_TENANT_ID` are set in `.env`, the provider activates automatically on next restart.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/auth/microsoft` | Redirects the browser to Microsoft's consent screen. |
| `GET` | `/api/auth/microsoft/callback` | Receives the authorization code, looks up or creates the user, and redirects to `/portal.html?token=<jwt>`. |

The Microsoft button in `static/login.html` is already enabled and points to `/api/auth/microsoft`.

---

### 11d. Rate Limiting

Login attempts are rate-limited using `slowapi` to prevent brute-force attacks. Limits are enforced per client IP and are already configured in `app/routers/auth.py`:

| Endpoint | Limit |
| --- | --- |
| `POST /api/auth/login` | 10 requests per minute |
| `POST /api/auth/register` | 5 requests per hour |

When the limit is exceeded the API returns `429 Too Many Requests`. The login form displays a human-readable message: *"Too many attempts. Please wait a minute and try again."*

The limiter uses the `X-Forwarded-For` header set by Apache, so the real client IP is used rather than the server's loopback address. No additional configuration is required.

---

### 11e. Resident Portal

After a successful login, users are redirected to `/portal.html` — a protected resident dashboard. Session management in the portal works as follows:

1. On load, the portal checks `localStorage` and `sessionStorage` for `andel_token`.
2. If no token is found, the user is immediately redirected to `/login.html`.
3. If a token is found, the portal calls `GET /api/auth/me` with an `Authorization: Bearer` header to verify the token is still valid.
4. A `401` response (expired or tampered token) clears the stored token and redirects to login.
5. On success, the user's email is displayed in the navigation bar.
6. The **Sign Out** button clears the token from both storages and redirects to login.

OAuth logins (Google/Microsoft) arrive at the portal via a `?token=` query parameter, which the portal absorbs into `sessionStorage` and strips from the URL before the session check runs.

The portal is a template with placeholder cards for future features: Pay Rent, Maintenance Request, Lease Documents, Notices, Contact Manager, and Account Settings.

---

### 11f. Session Security Checklist

Before going live with any authentication method:

- [ ] `SECRET_KEY` is at least 32 random bytes, is not the default `"change-me-in-production"`, and is not committed to version control
- [ ] `ALLOWED_ORIGINS` is set to the production domain — not `localhost`
- [ ] `COOKIE_SECURE=true` is set in `.env` (requires HTTPS to be active first)
- [ ] `REGISTRATION_SECRET` is cleared from `.env` after initial accounts are created
- [ ] HTTPS is enforced — never transmit credentials over plain HTTP
- [ ] Session cookie is `httpOnly` and `SameSite=Strict` — confirm no frontend JS reads `andel_token`
- [ ] JWT tokens have an expiry (`ACCESS_TOKEN_EXPIRE_MINUTES` in `.env`)
- [ ] Passwords are hashed with bcrypt — confirm no plain-text passwords exist in the database
- [ ] Port 8000 is blocked by the firewall (`sudo ufw deny 8000`)
- [ ] OAuth redirect URIs in Google/Azure exactly match the production domain — no trailing slashes
- [ ] Rate limiting is active — confirm `slowapi` is installed and `app.state.limiter` is set in `app/main.py`

---

## Updating the Application

```bash
cd /var/www/andel
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart andel
```

---

## Troubleshooting

| Symptom | Check |
| --- | --- |
| 502 Bad Gateway | `sudo systemctl status andel` — application may have crashed |
| Database connection errors | Verify `DATABASE_URL` in `.env` and MySQL user permissions |
| Static files not loading | Confirm `static/` exists and `www-data` has read access |
| SSL certificate errors | Run `sudo certbot renew` and check `sudo systemctl status certbot.timer` |
| Login returns 401 immediately | Confirm the `users` table exists — re-run the migration from Section 5 |
| Login returns 500 | Check `SECRET_KEY` is set in `.env` and the app has been restarted |
| Portal redirects to login instantly | Token is missing or expired — sign in again; check `ACCESS_TOKEN_EXPIRE_MINUTES` if this happens too frequently |
| Google/Microsoft OAuth fails | Confirm redirect URI in the provider console exactly matches `https://andel.ca/api/auth/google/callback` or `/microsoft/callback` — no trailing slash |
| OAuth state mismatch error | `SessionMiddleware` requires a stable `SECRET_KEY` — ensure it hasn't changed between requests |
| 429 Too Many Requests on login | Rate limit hit — wait one minute, or adjust the limit in `app/routers/auth.py` |
