# Jira to Vectara Ingestion

Lightweight tool to crawl Jira issues and index them into Vectara.

## Installation

**Windows:**
```bash
setup.bat
```

**macOS/Linux:**
```bash
./setup.sh
```

This will create a virtual environment and install all dependencies.

## Configuration

The setup script created `config.yaml` for you. Edit it with your credentials:

```yaml
vectara:
  api_key: "your-vectara-api-key"
  corpus_key: "your-corpus-key"

jira:
  base_url: "https://your-domain.atlassian.net"
  username: "your-email@example.com"
  api_token: "your-jira-api-token"
  jql: "project = MYPROJECT AND created >= -30d"

ssl:
  verify: true
```

## Run

After editing `config.yaml`, activate the virtual environment and run:

```bash
source venv/bin/activate              # macOS/Linux
# or venv\Scripts\activate            # Windows

python jira_ingest.py --config config.yaml
```

## Get Credentials

**Vectara API Key:**
1. Go to https://console.vectara.com
2. Authorization → Personal API Keys → Create API Key
3. Copy the API key and corpus key

**Jira API Token:**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Create API token
3. Copy the token

## SSL Configuration

### Option 1: Use System Certificates (Default)

```yaml
ssl:
  verify: true
```

### Option 2: Use Custom CA Certificate (Corporate Proxy)

```yaml
ssl:
  verify: "/path/to/corporate-ca.crt"
```

**Get your corporate CA certificate:**

**Windows:**
```powershell
# Export from browser
# Chrome → padlock icon → Certificate → Details → Export
# Save as: C:\certs\corporate-ca.crt

# Or ask your IT department
```

**Linux:**
```bash
# System CA bundle
/etc/ssl/certs/ca-certificates.crt  # Debian/Ubuntu
/etc/pki/tls/certs/ca-bundle.crt   # RedHat/CentOS
```

**macOS:**
```bash
# System CA bundle
/etc/ssl/cert.pem

# Or export from Keychain Access
# Open Keychain Access → System → Find CA → Export
```

### Option 3: Disable Verification (Testing Only)

```yaml
ssl:
  verify: false
```

⚠️ **Not recommended** - Only for testing in trusted environments

## Done

That's it! Your Jira issues will be indexed into Vectara.
