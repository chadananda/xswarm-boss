# Cloudflare Setup Checklist

Quick reference for setting up Cloudflare Workers and R2 storage.

## Information You'll Need to Collect

Use this as your worksheet while following the setup guide:

```bash
# ============================================
# CLOUDFLARE CREDENTIALS WORKSHEET
# ============================================

# Step 2: Account ID
# Location: Dashboard → Workers & Pages (in URL)
ACCOUNT_ID=_________________________________

# Step 3: Cloudflare API Token
# Location: Dashboard → My Profile → API Tokens → Create Token
CLOUDFLARE_API_TOKEN=_________________________________

# Step 5: R2 Access Credentials
# Location: Dashboard → R2 → Manage R2 API Tokens
S3_ACCESS_KEY_ID=_________________________________
S3_SECRET_ACCESS_KEY=_________________________________

# Step 4: R2 Bucket Names (you choose these)
ASSETS_BUCKET=xswarm-assets  # or xswarm-assets-<username> if taken
BACKUPS_BUCKET=xswarm-backups  # or xswarm-backups-<username> if taken

# Step 6: R2 Endpoint (constructed from Account ID)
R2_ENDPOINT=https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com

# Step 9: Worker URL (after deployment)
WORKER_URL=_________________________________
```

## Setup Checklist

### Pre-Setup
- [ ] Node.js 18.0.0+ installed (check: `node --version`)
- [ ] Have email address ready
- [ ] Have credit card ready (required even for free tier)

### Account Setup
- [ ] **Step 1**: Create Cloudflare account at https://dash.cloudflare.com/sign-up
- [ ] Verify email address
- [ ] Skip domain setup (or add domain if you have one)
- [ ] Choose plan (Free tier is fine for development)

### Collect Credentials
- [ ] **Step 2**: Get Account ID from Workers dashboard URL
  - Format: `https://dash.cloudflare.com/<ACCOUNT_ID>/workers-and-pages`
  - Copy the hexadecimal string between slashes
- [ ] **Step 3**: Create Cloudflare API Token
  - Dashboard → Profile → API Tokens → Create Token
  - Use "Edit Cloudflare Workers" template
  - **Copy token immediately (shown once!)**
- [ ] **Step 4**: Enable R2 Storage
  - Dashboard → R2 → Get Started
  - Add payment method (won't be charged on free tier)
  - Create bucket: `xswarm-assets`
  - Create bucket: `xswarm-backups`
- [ ] **Step 5**: Create R2 API Token
  - Dashboard → R2 → Manage R2 API Tokens → Create
  - Permission: Admin Read & Write
  - **Copy both Access Key ID and Secret Access Key immediately!**
- [ ] **Step 6**: Construct R2 endpoint URL
  - Format: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`

### Configure Project
- [ ] **Step 7.1**: Update `.env` file
  ```bash
  CLOUDFLARE_API_TOKEN=<your-token>
  S3_ACCESS_KEY_ID=<your-access-key-id>
  S3_SECRET_ACCESS_KEY=<your-secret-key>
  ```
- [ ] **Step 7.2**: Update `config.toml`
  ```toml
  [storage]
  bucket_name = "xswarm-assets"
  endpoint = "https://<ACCOUNT_ID>.r2.cloudflarestorage.com"

  [storage.backup]
  bucket_name = "xswarm-backups"
  ```
- [ ] **Step 7.3**: Update `packages/server/wrangler.toml`
  ```toml
  account_id = "<ACCOUNT_ID>"

  [[r2_buckets]]
  binding = "ASSETS"
  bucket_name = "xswarm-assets"

  [[r2_buckets]]
  binding = "BACKUPS"
  bucket_name = "xswarm-backups"
  ```

### Test Configuration
- [ ] **Step 8.1**: Install dependencies
  ```bash
  pnpm install
  ```
- [ ] **Step 8.2**: Login to Wrangler
  ```bash
  cd packages/server && pnpm wrangler login
  ```
- [ ] **Step 8.3**: Verify account access
  ```bash
  pnpm wrangler whoami
  ```
- [ ] **Step 8.4**: List R2 buckets
  ```bash
  pnpm wrangler r2 bucket list
  ```
- [ ] **Step 8.5-8.7**: Test R2 upload/download/delete
  ```bash
  echo "test" > test.txt
  pnpm wrangler r2 object put xswarm-assets/test.txt --file=test.txt
  pnpm wrangler r2 object get xswarm-assets/test.txt
  pnpm wrangler r2 object delete xswarm-assets/test.txt
  rm test.txt
  ```

### Deploy
- [ ] **Step 9.1**: Deploy Worker
  ```bash
  pnpm deploy:server
  ```
- [ ] **Step 9.2**: Copy Worker URL from deployment output
- [ ] **Step 9.3**: Test Worker health endpoint
  ```bash
  curl https://<your-worker>.workers.dev/health
  ```

### Production Setup
- [ ] **Step 10**: Set up Stripe webhooks (test mode)
  ```bash
  pnpm setup:webhooks
  ```
- [ ] Test webhook by creating test subscription in Stripe Dashboard
- [ ] Monitor logs: `pnpm wrangler tail`
- [ ] When ready for production: `pnpm setup:webhooks --live`

## Quick Commands Reference

```bash
# Login to Wrangler
cd packages/server && pnpm wrangler login

# Check authentication
pnpm wrangler whoami

# List R2 buckets
pnpm wrangler r2 bucket list

# Deploy Worker
pnpm deploy:server

# View logs (real-time)
pnpm wrangler tail

# Set up webhooks
pnpm setup:webhooks

# Test Stripe API
pnpm test:stripe

# Test local webhooks
# Terminal 1:
pnpm dev:webhooks
# Terminal 2:
pnpm dev:webhook-server
# Terminal 3:
pnpm test:webhooks
```

## Common Issues

### "Account ID is required"
→ Add `account_id` to `packages/server/wrangler.toml`

### "Authentication error"
→ Run `pnpm wrangler login` again

### "Bucket not found"
→ Check bucket names match in `wrangler.toml` and R2 dashboard

### "Module not found" during deploy
→ Run `pnpm build` first

## What Goes Where?

### .env (secrets - gitignored)
```bash
CLOUDFLARE_API_TOKEN=...
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
```

### config.toml (non-secret configuration)
```toml
[storage]
endpoint = "https://<ACCOUNT_ID>.r2.cloudflarestorage.com"
bucket_name = "xswarm-assets"
[storage.backup]
bucket_name = "xswarm-backups"
```

### packages/server/wrangler.toml (Workers config)
```toml
account_id = "<ACCOUNT_ID>"
[[r2_buckets]]
binding = "ASSETS"
bucket_name = "xswarm-assets"
```

## Cost Expectations

### Free Tier (No Credit Card Charges)
- Workers: 100,000 requests/day
- R2: 10 GB storage + 1M Class A operations/month
- Sufficient for development and small production apps

### When You'll Be Charged
- Workers: After 100,000 requests/day → $0.50/million additional
- R2 Storage: After 10 GB → $0.015/GB/month
- R2 Operations: After 1M Class A ops → $4.50/million additional

### Monitor Usage
Dashboard → Workers & Pages → Metrics
Dashboard → R2 → Bucket → Metrics

## Next Steps After Setup

1. **Deploy server**: `pnpm deploy:server`
2. **Set up webhooks**: `pnpm setup:webhooks`
3. **Test API**: `curl https://your-worker.workers.dev/health`
4. **Monitor logs**: `pnpm wrangler tail`
5. **(Optional) Custom domain**: Dashboard → Workers → Settings → Domains

## Time Estimate

- Account creation: 5 minutes
- Credential collection: 10 minutes
- Project configuration: 5 minutes
- Testing: 5 minutes
- Deployment: 5 minutes
- **Total: ~30 minutes**

## Resources

- Full guide: `planning/CLOUDFLARE_SETUP_GUIDE.md`
- Cloudflare Dashboard: https://dash.cloudflare.com/
- Workers Docs: https://developers.cloudflare.com/workers/
- R2 Docs: https://developers.cloudflare.com/r2/
