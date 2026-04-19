# SDACS GitHub Pages — Deployment Guide

This `docs/` directory is published as a static site via **GitHub Pages** (GitHub Actions deployment).

## Contents

```
docs/
├── index.html              # Landing page (Korean + English, mobile-responsive)
├── _config.yml             # Jekyll configuration
├── README.md               # This file
├── images/                 # 15 report figures (PNG + SVG)
├── report/                 # v6 technical + v7 easy-read reports (.docx)
├── test_report.html        # pytest coverage report
└── presentation_script.md  # Presentation notes
```

## Enable GitHub Pages (one-time setup)

1. Push this branch to `main` on GitHub.
2. Go to the repo on GitHub → **Settings** → **Pages** (left sidebar).
3. Under **Build and deployment**:
   - **Source**: select `GitHub Actions` (NOT "Deploy from a branch").
4. Go to **Actions** tab → confirm `Deploy SDACS Landing Page to GitHub Pages` workflow exists.
5. Trigger the first deployment:
   - Push any change to `docs/` on `main`, OR
   - Actions tab → select the workflow → **Run workflow** (manual dispatch).
6. Wait ~1-2 minutes for the `build` + `deploy` jobs to complete.

## Expected URL

```
https://<github-username>.github.io/swarm-drone-atc/
```

For this repo (owner `sun475300-sudo`):

```
https://sun475300-sudo.github.io/swarm-drone-atc/
```

## Local preview

No build step is required — `index.html` is fully self-contained (inline CSS/JS).

```bash
# Simple HTTP server
cd docs/
python -m http.server 8000
# Open http://localhost:8000
```

## Updating the landing page

Edit `docs/index.html` directly. All CSS and JavaScript are inline — no external
build or bundling required. Only external dependency is Google Fonts (Inter).

## Workflow details

- **Trigger**: push to `main` touching `docs/**`, or manual dispatch.
- **Build**: uploads `docs/` as a Pages artifact.
- **Deploy**: publishes to the `github-pages` environment.
- **Concurrency**: single in-flight deploy, new pushes cancel prior builds (`cancel-in-progress: false` means in-progress deploys finish).

See [.github/workflows/deploy-pages.yml](../.github/workflows/deploy-pages.yml) for the full configuration.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| 404 on deploy | Verify Settings → Pages → Source = `GitHub Actions` |
| Images broken | Paths in `index.html` are relative (`images/...`, `report/...`); push entire `docs/` folder |
| Workflow not triggering | Default branch must be `main`; or use Actions → Run workflow |
| Old content cached | Browser hard-refresh (Ctrl+Shift+R) or wait for CDN purge (~5 min) |
