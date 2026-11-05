"""A tiny offline 'Help Center' website used as a deterministic target for the web-goal agent."""
ARTICLES = {
    "refunds": ("Refunds and billing disputes", "Charged twice or billed the wrong amount? Request a refund for duplicate charges, failed payments and cancelled orders. Refunds arrive within 5 business days."),
    "password": ("Reset your password", "Forgot your password or locked out of your account? Use the reset link on the sign-in page to choose a new password and regain access."),
    "pricing": ("Pricing and plans", "Compare Free, Pro and Enterprise plans. See what each tier costs per seat, annual discounts and how to upgrade your subscription."),
    "bug": ("Report a bug or outage", "The app crashes, shows an error or a feature is broken? Check the status page and send us a bug report with steps to reproduce."),
    "export": ("Export your data", "Download all your projects, files and history as CSV or JSON from the account settings page."),
    "careers": ("Careers at Acme", "We are hiring engineers, designers and support staff. Browse open roles and learn about our remote-first culture."),
    "delete": ("Delete your account", "Close your account and permanently remove personal data. This cannot be undone."),
    "invoice": ("Download invoices and receipts", "Find past invoices, VAT receipts and payment history under Billing in your account."),
    "api": ("API and developer docs", "Authenticate with API keys, call REST endpoints, and handle rate limits and webhooks."),
    "security": ("Security and privacy", "How we encrypt data, our compliance certifications and how to enable two-factor authentication."),
    "contact": ("Contact our team", "Chat with support, email us, or book a call with our sales team."),
    "integrations": ("Integrations", "Connect Slack, Google Drive, Jira and 40 more tools to your workspace."),
}
PAGE = """<!doctype html><html lang=en><head><meta charset=utf-8><title>{title} - Acme Help Center</title>
<style>body{{font:16px/1.5 -apple-system,system-ui,sans-serif;max-width:860px;margin:0 auto;padding:24px;color:#1b2230}}
nav a{{margin-right:16px;color:#2a5bd7}}.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}}
.card{{border:1px solid #d6dbe6;border-radius:10px;padding:14px;text-decoration:none;color:inherit;display:block}}
.card:hover{{background:#f3f6fc}}.card h3{{margin:0 0 4px;color:#2a5bd7}}.card p{{margin:0;color:#556}}</style></head>
<body><nav><a href="/help">Help home</a><a href="/help/contact">Contact</a><a href="/help/careers">Careers</a></nav>{body}</body></html>"""

def home():
    cards = "".join(f'<a class="card" href="/help/{k}"><h3>{t}</h3><p>{d[:70]}...</p></a>' for k, (t, d) in ARTICLES.items())
    return PAGE.format(title="Home", body=f'<h1>How can we help?</h1><div class="grid">{cards}</div>')

def article(slug):
    if slug not in ARTICLES: return None
    t, d = ARTICLES[slug]
    return PAGE.format(title=t, body=f"<h1>{t}</h1><p>{d}</p>")
