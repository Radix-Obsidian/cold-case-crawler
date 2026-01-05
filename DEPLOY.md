# Cold Case Crawler - Deployment Guide

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Vercel        │────▶│   Railway       │────▶│   Supabase      │
│   (Frontend)    │     │   (API)         │     │   (Database)    │
│                 │     │                 │     │                 │
│ - HTML/CSS/JS   │     │ - FastAPI       │     │ - PostgreSQL    │
│ - Static files  │     │ - Stripe        │     │ - Auth          │
│ - Analytics     │     │ - AI Agents     │     │ - Storage       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Step 1: Deploy Backend to Railway

1. Go to [railway.app](https://railway.app) and sign in
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your Cold Case Crawler repo
4. Add environment variables:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ELEVENLABS_API_KEY=sk_...
   FIRECRAWL_API_KEY=fc-...
   STRIPE_SECRET_KEY=sk_live_...
   SUPABASE_URL=https://pihhufjbriwtkhvybiaa.supabase.co
   SUPABASE_KEY=eyJ...
   THORNE_VOICE_ID=JBFqnCBsd6RMkjVDRZzb
   MAYA_VOICE_ID=FGY2WhTYpPnrIDTdsKH5
   ```
5. Railway will auto-detect the Procfile and deploy
6. Copy your Railway URL (e.g., `https://cold-case-crawler-api.up.railway.app`)

## Step 2: Update Frontend Config

Edit `frontend/vercel.json` and replace the API URL:
```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://YOUR-RAILWAY-URL/api/:path*"
    },
    {
      "source": "/membership/:path*", 
      "destination": "https://YOUR-RAILWAY-URL/membership/:path*"
    }
  ]
}
```

## Step 3: Deploy Frontend to Vercel

1. Go to [vercel.com](https://vercel.com) and sign in
2. Click "Add New" → "Project"
3. Import your GitHub repo
4. Set the root directory to `frontend`
5. Deploy!

Your site will be live at `https://your-project.vercel.app`

## Step 4: Configure Stripe Webhooks

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://YOUR-RAILWAY-URL/membership/webhook`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
4. Copy the webhook signing secret
5. Add to Railway env vars: `STRIPE_WEBHOOK_SECRET=whsec_...`

## Step 5: Configure Supabase Auth

1. Go to Supabase Dashboard → Authentication → Providers
2. Enable "Email" provider
3. Configure email templates (optional)
4. Add your Vercel URL to allowed redirect URLs

## Quick Commands

```bash
# Test locally
uvicorn src.main:app --port 8000

# Check status
python3 podcast_manager.py status

# Generate episode
python3 podcast_manager.py generate
```

## Environment Variables Summary

| Variable | Where | Description |
|----------|-------|-------------|
| ANTHROPIC_API_KEY | Railway | Claude API |
| ELEVENLABS_API_KEY | Railway | Voice synthesis |
| FIRECRAWL_API_KEY | Railway | Web scraping |
| STRIPE_SECRET_KEY | Railway | Payments |
| STRIPE_WEBHOOK_SECRET | Railway | Webhook verification |
| SUPABASE_URL | Railway | Database URL |
| SUPABASE_KEY | Railway | Database key |
| THORNE_VOICE_ID | Railway | Dr. Thorne voice |
| MAYA_VOICE_ID | Railway | Maya voice |

## Monitoring

- **Vercel Analytics**: Built-in traffic tracking
- **Railway Logs**: `railway logs` or dashboard
- **Supabase**: Database metrics in dashboard
- **Stripe**: Payment analytics in dashboard
