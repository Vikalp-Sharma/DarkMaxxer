# Hugging Face Automated Model Downloader (Playwright Go)

Built in accordance with the `go-playwright` automation skill using `github.com/mxschmitt/playwright-go` and Uber `zap` structured logging.

## Features
- **Browser Singleton:** Launches headless Chromium with human emulation (randomized viewport, mouse movement, realistic user-agents).
- **DOM Link Scraping:** Navigates Hugging Face repository trees to extract exact CDN resolve URLs (`/resolve/main/`).
- **Live Terminal Progress Bar:** Displays real-time download percentage, transferred megabytes, MB/s transfer speed, and countdown ETA.
- **Multi-Category Verification:** Scrapes models across Chat, Code Generation, Sentence Embeddings, and Compact Reasoning.

## Usage
```bash
go run main.go
```
Downloaded models are saved to `../../models/<category>/`.
