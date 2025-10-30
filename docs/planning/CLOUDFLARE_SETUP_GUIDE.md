# Cloudflare Setup Guide

Complete walkthrough for setting up Cloudflare Workers and R2 storage for xSwarm deployment.

## Overview

You need to collect the following information from Cloudflare:

| Information | Where to Find | Goes In | Purpose |
|------------|---------------|---------|---------|
| **Account ID** | Dashboard → Workers & Pages | `wrangler.toml` | Identifies your Cloudflare account |
| **Cloudflare API Token** | Dashboard → My Profile → API Tokens | `.env` | Deploys Workers via wrangler CLI |
| **R2 Access Key ID** | Dashboard → R2 → Manage R2 API Tokens | `.env` | Accesses R2 storage (S3-compatible) |
| **R2 Secret Access Key** | Dashboard → R2 → Manage R2 API Tokens | `.env` | Authenticates R2 storage access |
| **R2 Account ID** | Dashboard → R2 (in URL) | `config.toml` | R2 storage endpoint |

## Prerequisites

- [ ] Node.js 18.0.0 or later (already installed ✓)
- [ ] Email address for Cloudflare account
- [ ] Credit card (required for Workers and R2, even on free tier)

## Step 1: Create Cloudflare Account

### 1.1 Sign Up

1. Go to: https://dash.cloudflare.com/sign-up
2. Enter your email address
3. Create a strong password
4. Verify your email address (check inbox for verification link)

### 1.2 Skip Domain Setup (Optional)

When asked to add a site/domain:
- **If you already have a domain**: Add it now
- **If you don't have a domain yet**: Click "Skip" or "Set up later"
  - Workers don't require a custom domain
  - You'll get a free `*.workers.dev` subdomain

### 1.3 Choose Plan

For development and testing:
- Select **Free plan** (sufficient for development)
- Workers Free: 100,000 requests/day
- R2 Free: 10 GB storage, 1M Class A operations/month

For production:
- Consider **Workers Paid** ($5/month)
- 10M requests/month included
- Additional requests at $0.50/million

## Step 2: Get Account ID

### 2.1 Navigate to Workers Dashboard

1. Log in to Cloudflare Dashboard: https://dash.cloudflare.com/
2. Click **Workers & Pages** in left sidebar
3. If prompted, accept Workers terms of service

### 2.2 Find Account ID

**Location 1: Workers & Pages Overview**
- Look at the URL in your browser
- Format: `https://dash.cloudflare.com/<ACCOUNT_ID>/workers-and-pages`
- Example: `https://dash.cloudflare.com/7f8c9d0e1f2a3b4c/workers-and-pages`
- Your Account ID is the long hexadecimal string: `7f8c9d0e1f2a3b4c`

**Location 2: Workers Settings**
- Go to Workers & Pages → Overview
- Scroll to right sidebar
- Look for "Account ID" field
- Click copy icon to copy to clipboard

### 2.3 Save Account ID

✏️ **Copy this value - you'll need it multiple times:**
```
YOUR_ACCOUNT_ID_HERE
```

## Step 3: Create Cloudflare API Token (for Workers Deployment)

### 3.1 Navigate to API Tokens

1. Click your profile icon (top right corner)
2. Select **My Profile**
3. Click **API Tokens** tab
4. Click **Create Token** button

### 3.2 Use Workers Template

1. Find "Edit Cloudflare Workers" template
2. Click **Use template** button

### 3.3 Configure Token Permissions

The template automatically sets these permissions:
- **Account** → **Workers Scripts** → **Edit**
- **Account** → **Workers KV Storage** → **Edit** (if using KV)
- **Zone** → **Workers Routes** → **Edit** (if using custom domains)

**Recommended settings:**
- **Account Resources**: Include → All accounts (or specific account)
- **Zone Resources**: All zones (or specific zone if you have one)
- **TTL**: Leave blank (no expiration) or set to 1 year

### 3.4 Review and Create

1. Click **Continue to summary**
2. Review permissions (should match above)
3. Click **Create Token**

### 3.5 Copy API Token

🚨 **CRITICAL: This is shown ONCE. Copy it immediately!**

The token looks like: `y7x8z9w6v5u4t3s2r1q0p9o8n7m6l5k4j3h2g1f0`

✏️ **Save this token securely:**
```
CLOUDFLARE_API_TOKEN=y7x8z9w6v5u4t3s2r1q0p9o8n7m6l5k4j3h2g1f0
```

If you lose it:
- You cannot retrieve it again
- You must create a new token
- Old token will need to be revoked

## Step 4: Set Up R2 Storage

### 4.1 Navigate to R2

1. From Cloudflare Dashboard home
2. Click **R2** in left sidebar
3. Click **Get Started** or **Purchase R2 Plan**

### 4.2 Add Payment Method

🚨 **Required even for free tier**

1. Click **Add Payment Method**
2. Enter credit card details
3. Billing address
4. Click **Confirm**

**Note:** Free tier is truly free:
- You won't be charged unless you exceed free limits
- Free tier: 10 GB storage, 1M Class A operations/month
- Easy to monitor usage in dashboard

### 4.3 Enable R2

After adding payment method:
1. Click **Begin setup** or **Enable R2**
2. Accept R2 terms of service
3. R2 dashboard will now be accessible

### 4.4 Create Your First Bucket

1. Click **Create bucket** button
2. **Bucket name**: `xswarm-assets` (must be globally unique)
   - Use: `xswarm-assets-<your-username>` if taken
   - Allowed characters: lowercase letters, numbers, hyphens
3. **Location**: Automatic (recommended) or select region close to users
4. **Storage class**: Standard
5. Click **Create bucket**

Create a second bucket for backups:
1. Click **Create bucket** again
2. **Bucket name**: `xswarm-backups` (or `xswarm-backups-<your-username>`)
3. Click **Create bucket**

### 4.5 Get R2 Account ID

**From URL:**
- Look at browser URL while on R2 dashboard
- Format: `https://dash.cloudflare.com/<ACCOUNT_ID>/r2/default`
- Should match your Account ID from Step 2

## Step 5: Create R2 API Token

### 5.1 Navigate to R2 API Tokens

1. In R2 dashboard
2. Click **Manage R2 API Tokens** (top right)
3. Click **Create API token** button

### 5.2 Configure R2 Token

**Token name:** `xswarm-r2-access`

**Permissions:** Select **Admin Read & Write**
- This allows full access to all R2 operations
- Required for creating/deleting buckets and objects

**Alternative (more restrictive):**
- **Object Read & Write** - For basic operations only
- Use this if you don't need to create/delete buckets programmatically

**TTL (Time to Live):**
- Leave blank (no expiration) - recommended for production
- Or set to 1 year for added security

**Apply to specific buckets (optional):**
- Leave as "All buckets" for simplicity
- Or select only `xswarm-assets` and `xswarm-backups`

### 5.3 Create and Copy Credentials

1. Click **Create API Token**
2. You'll see two values (copy both immediately):

```
Access Key ID: f7e8d9c0b1a2g3h4i5j6k7l8m9n0o1p2
Secret Access Key: 3q4w5e6r7t8y9u0i1o2p3a4s5d6f7g8h9j0k1l2z
```

✏️ **Save both values:**
```
S3_ACCESS_KEY_ID=f7e8d9c0b1a2g3h4i5j6k7l8m9n0o1p2
S3_SECRET_ACCESS_KEY=3q4w5e6r7t8y9u0i1o2p3a4s5d6f7g8h9j0k1l2z
```

🚨 **Secret Access Key is shown ONCE!** Copy it now or you'll need to create a new token.

## Step 6: Get R2 Endpoint URL

### 6.1 Construct S3-Compatible Endpoint

Your R2 endpoint URL format:
```
https://<ACCOUNT_ID>.r2.cloudflarestorage.com
```

Replace `<ACCOUNT_ID>` with your Account ID from Step 2.

**Example:**
```
https://7f8c9d0e1f2a3b4c.r2.cloudflarestorage.com
```

✏️ **Save this endpoint:**
```
R2_ENDPOINT=https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com
```

### 6.2 Verify Bucket URLs

Your buckets are accessible at:
- `https://<ACCOUNT_ID>.r2.cloudflarestorage.com/xswarm-assets`
- `https://<ACCOUNT_ID>.r2.cloudflarestorage.com/xswarm-backups`

## Step 7: Configure Your Project

### 7.1 Update .env File

Add these lines to your `.env` file:

```bash
# =============================================================================
# Cloudflare Configuration
# =============================================================================

# Cloudflare API Token (for Workers deployment)
# Created in: Dashboard → My Profile → API Tokens
CLOUDFLARE_API_TOKEN=y7x8z9w6v5u4t3s2r1q0p9o8n7m6l5k4j3h2g1f0

# R2 Storage Credentials (S3-compatible)
# Created in: Dashboard → R2 → Manage R2 API Tokens
S3_ACCESS_KEY_ID=f7e8d9c0b1a2g3h4i5j6k7l8m9n0o1p2
S3_SECRET_ACCESS_KEY=3q4w5e6r7t8y9u0i1o2p3a4s5d6f7g8h9j0k1l2z
```

### 7.2 Update config.toml File

Update the storage section in `config.toml`:

```toml
# =============================================================================
# S3-Compatible Storage (Assets & Backups)
# =============================================================================
[storage]
# Provider: "r2" (Cloudflare R2)
provider = "r2"

# Primary bucket for assets (user uploads, generated files, etc.)
bucket_name = "xswarm-assets"  # Use your actual bucket name

# AWS region (for S3) or hint for R2
region = "auto"

# Custom endpoint (required for R2)
# Format: https://<ACCOUNT_ID>.r2.cloudflarestorage.com
endpoint = "https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com"

# Public URL for assets (if using CDN or public bucket)
# Update after setting up R2 custom domain or public access
public_url = "https://assets.xswarm.ai"

# Backup bucket configuration
[storage.backup]
enabled = true
bucket_name = "xswarm-backups"  # Use your actual backup bucket name
retention_days = 90
```

### 7.3 Create wrangler.toml (if it doesn't exist)

The wrangler configuration file should already exist in `packages/server/wrangler.toml`:

```toml
name = "xswarm-server"
main = "src/index.ts"
compatibility_date = "2025-01-15"

# Your Cloudflare Account ID
account_id = "YOUR_ACCOUNT_ID"

# R2 bucket bindings (allows Workers to access R2)
[[r2_buckets]]
binding = "ASSETS"
bucket_name = "xswarm-assets"

[[r2_buckets]]
binding = "BACKUPS"
bucket_name = "xswarm-backups"

# Environment variables (non-secret)
[vars]
ENVIRONMENT = "production"
```

## Step 8: Test Your Configuration

### 8.1 Install Wrangler

Wrangler should already be installed, but verify:

```bash
pnpm install
```

### 8.2 Authenticate Wrangler

```bash
cd packages/server
pnpm wrangler login
```

This will:
1. Open your browser
2. Ask you to authorize Wrangler
3. Click "Allow" to grant access
4. You'll see "Successfully logged in" in terminal

### 8.3 Verify Account Access

```bash
pnpm wrangler whoami
```

Should show:
```
You are logged in with an API Token, associated with the email '<your-email>@example.com'.
Account ID: 7f8c9d0e1f2a3b4c
```

### 8.4 List R2 Buckets

```bash
pnpm wrangler r2 bucket list
```

Should show:
```
xswarm-assets
xswarm-backups
```

### 8.5 Test R2 Upload

```bash
echo "test file" > test.txt
pnpm wrangler r2 object put xswarm-assets/test.txt --file=test.txt
```

Should show:
```
Creating object "test.txt" in bucket "xswarm-assets".
Upload complete.
```

### 8.6 Verify Upload

```bash
pnpm wrangler r2 object get xswarm-assets/test.txt
```

Should output: `test file`

### 8.7 Clean Up Test File

```bash
pnpm wrangler r2 object delete xswarm-assets/test.txt
rm test.txt
```

## Step 9: Deploy Your Worker

### 9.1 Build and Deploy

```bash
# From project root
pnpm deploy:server
```

This will:
1. Build your Worker code
2. Upload to Cloudflare
3. Deploy to `<worker-name>.<your-subdomain>.workers.dev`

### 9.2 Get Your Worker URL

After deployment, you'll see:
```
Published xswarm-server (0.42 sec)
  https://xswarm-server.<your-subdomain>.workers.dev
```

✏️ **Save your Worker URL:**
```
WORKER_URL=https://xswarm-server.<your-subdomain>.workers.dev
```

### 9.3 Test Your Worker

```bash
curl https://xswarm-server.<your-subdomain>.workers.dev/health
```

Should return:
```json
{"status":"ok","timestamp":"2025-10-24T12:00:00.000Z"}
```

## Step 10: Set Up Production Webhooks

Now that your Worker is deployed, set up production Stripe webhooks:

```bash
# From project root
pnpm setup:webhooks
```

This will:
1. Create webhook endpoint in Stripe (test mode)
2. Configure webhook events
3. Push webhook secret to Cloudflare Workers as environment variable

Repeat for live mode when ready:
```bash
pnpm setup:webhooks --live
```

## Troubleshooting

### Error: "Account ID is required"

**Problem:** `wrangler.toml` is missing `account_id`

**Solution:**
1. Open `packages/server/wrangler.toml`
2. Add line: `account_id = "YOUR_ACCOUNT_ID"`
3. Replace with your actual Account ID from Step 2

### Error: "Authentication error"

**Problem:** API token is invalid or expired

**Solution:**
1. Go to Dashboard → My Profile → API Tokens
2. Find your token
3. Click "Roll" to generate new token
4. Update `.env` with new `CLOUDFLARE_API_TOKEN`

### Error: "Bucket not found"

**Problem:** Bucket name in `wrangler.toml` doesn't match actual bucket name

**Solution:**
1. Run: `pnpm wrangler r2 bucket list`
2. Copy exact bucket name
3. Update `wrangler.toml` with correct name

### Error: "Module not found"

**Problem:** Build failed or wrong entry point

**Solution:**
1. Check `packages/server/src/index.ts` exists
2. Run: `pnpm build` from project root
3. Check `packages/server/wrangler.toml` has correct `main` field

### Workers Not Deploying

**Problem:** Deployment hangs or fails

**Solution:**
1. Check internet connection
2. Verify account has Workers enabled
3. Try: `pnpm wrangler whoami` to verify authentication
4. Clear cache: `rm -rf node_modules/.wrangler`
5. Rebuild: `pnpm install && pnpm build`

## Security Best Practices

### API Token Security

- ✅ **DO**: Store in `.env` file (gitignored)
- ✅ **DO**: Use minimal permissions (Workers only)
- ✅ **DO**: Set expiration (1 year recommended)
- ❌ **DON'T**: Commit to Git
- ❌ **DON'T**: Share in public channels
- ❌ **DON'T**: Use same token for multiple projects

### R2 Credentials

- ✅ **DO**: Rotate credentials periodically
- ✅ **DO**: Use separate credentials for dev/prod
- ✅ **DO**: Restrict to specific buckets if possible
- ❌ **DON'T**: Expose in client-side code
- ❌ **DON'T**: Use admin token for public uploads

### Environment Variables

- ✅ **DO**: Use Wrangler secrets for sensitive values: `pnpm wrangler secret put SECRET_NAME`
- ✅ **DO**: Validate environment variables at startup
- ❌ **DON'T**: Log secret values
- ❌ **DON'T**: Return secrets in API responses

## Cost Monitoring

### Workers Free Tier

- 100,000 requests/day
- 10 ms CPU time per request
- **Exceeding limits**: $0.50 per million requests

### R2 Free Tier

- 10 GB storage
- 1M Class A operations/month (write, list)
- 10M Class B operations/month (read)
- **Exceeding limits**: $0.015/GB storage, $4.50/million Class A ops

### Monitor Usage

1. Dashboard → Workers & Pages → Your Worker → Metrics
2. Dashboard → R2 → Your Bucket → Metrics
3. Set up usage alerts: Account Home → Notifications

## Next Steps

After completing this setup:

1. ✅ **Deploy your Worker**: `pnpm deploy:server`
2. ✅ **Set up webhooks**: `pnpm setup:webhooks`
3. ✅ **Test production API**: `curl https://your-worker.workers.dev/health`
4. ✅ **Monitor logs**: `pnpm wrangler tail`
5. ✅ **Set up custom domain** (optional): Dashboard → Workers & Pages → Your Worker → Settings → Domains & Routes

## Resources

- **Cloudflare Dashboard**: https://dash.cloudflare.com/
- **Workers Documentation**: https://developers.cloudflare.com/workers/
- **R2 Documentation**: https://developers.cloudflare.com/r2/
- **Wrangler CLI Docs**: https://developers.cloudflare.com/workers/wrangler/
- **Community Forum**: https://community.cloudflare.com/

## Support

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review official Cloudflare docs
3. Search Cloudflare Community Forum
4. Open issue with error logs in project repository
