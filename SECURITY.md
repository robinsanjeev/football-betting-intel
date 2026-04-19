# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

**Email:** robin.snjv@gmail.com

**Please do NOT:**
- Open a public issue for security vulnerabilities
- Post details in discussions or comments

**Please include:**
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

I will acknowledge receipt within 48 hours and aim to provide a fix or mitigation plan within 7 days.

## Scope

This project handles sensitive data including:

- **API keys** for third-party services (Kalshi, football-data.org, The Odds API)
- **RSA private keys** for Kalshi authentication
- **Telegram bot tokens**

### Security Best Practices for Users

1. **Never commit `config/config.yaml`** — it's git-ignored for a reason
2. **Never commit files in `config/keys/`** — your RSA private keys
3. **Use environment variables** or mounted volumes in Docker for secrets
4. **Restrict network access** — the dashboard has no authentication; don't expose it to the public internet without adding auth
5. **Keep dependencies updated** — run `pip install --upgrade -r requirements.txt` periodically

## Known Limitations

- **No built-in authentication** — the web dashboard and API have no login system. If you expose this to the internet, add a reverse proxy with auth (nginx + basic auth, Cloudflare Access, etc.)
- **SQLite** — the database is a local file with no access controls beyond filesystem permissions
- **API keys in config file** — stored as plaintext YAML; consider using a secrets manager for production deployments

## Supported Versions

Only the latest version on `main` is supported with security updates.
