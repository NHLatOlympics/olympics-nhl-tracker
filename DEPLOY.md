# GitHub Pages Deployment Guide

## Quick Setup (First Time)

### 1. Create GitHub Repository

1. Go to [github.com](https://github.com) and log in
2. Click the **+** icon in the top-right corner → **New repository**
3. Repository name: `olympics-nhl-tracker` (or any name you prefer)
4. Description: `2026 Olympics Men's Ice Hockey - NHL Team Rankings`
5. Choose **Public** (required for free GitHub Pages)
6. **Do NOT** initialize with README, .gitignore, or license (we already have these)
7. Click **Create repository**

### 2. Push to GitHub

After creating the repository, run these commands:

```bash
cd /Users/danny.howerton/Research/olympics

# Add the GitHub repository as remote (replace YOUR-USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR-USERNAME/olympics-nhl-tracker.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### 3. Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** (top menu)
3. Click **Pages** (left sidebar)
4. Under "Source":
   - Branch: `main`
   - Folder: `/ (root)`
5. Click **Save**
6. Wait 1-2 minutes for deployment
7. Your site will be live at: `https://YOUR-USERNAME.github.io/olympics-nhl-tracker/`

## Updating the Site

Whenever you want to update the stats:

```bash
cd /Users/danny.howerton/Research/olympics

# Activate virtual environment
source venv/bin/activate

# Run the script to fetch latest stats
python olympics_nhl_points.py

# Copy updated HTML to index.html
cp olympics_nhl_rankings.html index.html

# Commit and push changes
git add index.html
git commit -m "Update Olympic stats - $(date '+%Y-%m-%d %H:%M')"
git push

# Wait 1-2 minutes for GitHub Pages to rebuild
```

## Automation Option

You can automate updates using GitHub Actions. Create `.github/workflows/update-stats.yml`:

```yaml
name: Update Olympic Stats

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:  # Manual trigger

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Fetch latest stats
        run: |
          python olympics_nhl_points.py
          cp olympics_nhl_rankings.html index.html
      
      - name: Commit and push if changed
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add index.html
          git diff --quiet && git diff --staged --quiet || (git commit -m "Auto-update stats $(date)" && git push)
```

## Troubleshooting

**Site not updating?**
- Check the Actions tab on GitHub for errors
- Clear your browser cache
- Wait a few minutes for GitHub Pages to rebuild

**404 Error?**
- Make sure GitHub Pages is enabled in Settings → Pages
- Verify the branch is set to `main` and folder to `/ (root)`
- Check that `index.html` exists in your repository

**Stats not refreshing?**
- Run `python olympics_nhl_points.py` locally
- Verify `olympics_nhl_rankings.html` is generated
- Copy to `index.html` and commit/push

## Custom Domain (Optional)

To use a custom domain like `olympics.yoursite.com`:

1. Add a `CNAME` file to the repository with your domain
2. Configure DNS with your domain provider
3. In GitHub Settings → Pages, add your custom domain
4. Enable "Enforce HTTPS"

See: https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site
