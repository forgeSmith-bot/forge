# GitHub App Setup

This guide walks through creating and configuring a GitHub App so Forge can receive webhooks and act on repositories.

## Why a GitHub App

GitHub Apps get their own identity, fine-grained permission scopes, per-installation rate limits, and signed webhook delivery. A personal access token works for experimentation but does not scale across multiple repositories or teams.

## Step 1 — Create the GitHub App

Go to **GitHub → Settings → Developer settings → GitHub Apps → New GitHub App**.

Fill in the following fields:

| Field | Value |
|---|---|
| **App name** | `forge-bot` (or any name) |
| **Homepage URL** | Your Forge instance URL |
| **Webhook URL** | `https://<your-forge-host>/api/v1/webhooks/github` |
| **Webhook secret** | A random secret string — save this for Step 4 |

### Repository permissions

| Permission | Level |
|---|---|
| Contents | Read & write |
| Pull requests | Read & write |
| Issues | Read & write |
| Checks | Read & write |
| Commit statuses | Read |
| Metadata | Read (mandatory) |

### Events to subscribe to

| Event | Purpose |
|---|---|
| `pull_request` | PR opened, closed, merged |
| `pull_request_review` | Approval or changes requested |
| `check_run` | CI check pass/fail |
| `check_suite` | CI suite completion |
| `issue_comment` | `/forge skip-gate` commands on PRs |
| `push` | Branch updates |

Click **Create GitHub App**.

## Step 2 — Generate a private key

On the App settings page, scroll to **Private keys** and click **Generate a private key**. A `.pem` file will download — keep it safe.

Note the following from the App settings page:
- **App ID** (shown at the top)

## Step 3 — Install the App on your repositories

From the App settings page, click **Install App** and select the repositories Forge will manage. GitHub begins delivering webhooks immediately after installation.

Note the **Installation ID** from the URL after installing:
`https://github.com/settings/installations/<installation-id>`

## Step 4 — Configure Forge

Add the following to your `.env` file:

```bash
# GitHub App credentials
GITHUB_TOKEN=<personal access token or installation access token>
GITHUB_WEBHOOK_SECRET=<the secret you set in Step 1>

# GitHub repo Forge will open PRs against (e.g. "org/repo")
GITHUB_DEFAULT_REPO=<org/repo>
```

### Generating an installation access token

Installation tokens expire after 1 hour. For long-running deployments, generate one with the GitHub CLI:

```bash
# Authenticate as the App installation to get a token
gh auth login
gh api \
  --method POST \
  -H "Accept: application/vnd.github+json" \
  /app/installations/<installation-id>/access_tokens \
  | jq -r '.token'
```

Use the resulting token as `GITHUB_TOKEN`. Automate rotation if needed — Forge does not currently handle token refresh automatically.

## Step 5 — Expose Forge publicly

GitHub must be able to reach your Forge instance over HTTPS. The webhook endpoint is:

```
POST /api/v1/webhooks/github
```

**For local development**, use a tunnel:

```bash
ngrok http 8000
```

Update the webhook URL in your GitHub App settings to the ngrok URL. Note that the URL changes each time ngrok restarts unless you have a paid plan.

**For production**, put Forge behind a reverse proxy with a real domain and TLS:

```nginx
location /api/ {
    proxy_pass http://localhost:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## Step 6 — Verify the connection

Start Forge and check that the ping event from GitHub is handled:

```bash
uv run uvicorn forge.main:app --reload --port 8000 --host 0.0.0.0
```

In your GitHub App settings, go to **Advanced → Recent Deliveries**. You should see a `ping` event with a `200` response containing `{"status": "pong", ...}`.

If the ping fails, check:
- The webhook URL is reachable from the internet
- `GITHUB_WEBHOOK_SECRET` matches the secret set in Step 1
- Forge is running and healthy at `/api/v1/health`

## How Forge associates GitHub events with Jira tickets

Forge extracts the Jira ticket key from the PR branch name. The branch must follow the pattern `<TICKET-KEY>-<description>`, for example:

```
AISOS-123-add-user-authentication
```

Events on PRs without a recognisable ticket key in the branch name are silently skipped.
