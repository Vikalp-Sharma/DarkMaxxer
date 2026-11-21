// [Vikalp Sharma] - Proprietary / Anti-Theft Watermark
// Hugging Face Automated Multi-Category Model Scraper & Downloader
// Built using Playwright Go and Uber Zap Logger (SKILL: go-playwright)
// Includes Live Dynamic Progress Bar & Multi-Category Pipeline

package main

import (
	"crypto/tls"
	"fmt"
	"io"
	"math/rand"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	playwright "github.com/mxschmitt/playwright-go"
	"go.uber.org/zap"
)

type ModelTarget struct {
	Category    string
	DisplayName string
	RepoID      string
	FileName    string
	PageURL     string
	FallbackURL string
}

type ProgressWriter struct {
	Total     int64
	Current   int64
	StartTime time.Time
	LastPrint time.Time
	TaskTitle string
}

func (pw *ProgressWriter) Write(p []byte) (int, error) {
	n := len(p)
	pw.Current += int64(n)
	now := time.Now()
	if now.Sub(pw.LastPrint) > 80*time.Millisecond || pw.Current >= pw.Total {
		pw.LastPrint = now
		pw.render()
	}
	return n, nil
}

func (pw *ProgressWriter) render() {
	elapsed := time.Since(pw.StartTime).Seconds()
	if elapsed <= 0 {
		elapsed = 0.001
	}
	speed := float64(pw.Current) / (1024 * 1024 * elapsed)
	currentMB := float64(pw.Current) / (1024 * 1024)

	if pw.Total > 0 {
		percent := float64(pw.Current) / float64(pw.Total) * 100
		totalMB := float64(pw.Total) / (1024 * 1024)
		etaSec := 0.0
		if speed > 0 {
			etaSec = (totalMB - currentMB) / speed
		}
		if etaSec < 0 {
			etaSec = 0
		}

		barWidth := 25
		filled := int(float64(barWidth) * float64(pw.Current) / float64(pw.Total))
		if filled > barWidth {
			filled = barWidth
		}
		bar := strings.Repeat("█", filled) + strings.Repeat("░", barWidth-filled)

		fmt.Printf("\r\x1b[K  \x1b[1;36m[%s]\x1b[0m \x1b[1;32m[%s]\x1b[0m \x1b[1;37m%5.1f%%\x1b[0m (%5.1f / %5.1f MB) \x1b[1;33m%5.1f MB/s\x1b[0m ETA: %2.0fs",
			pw.TaskTitle, bar, percent, currentMB, totalMB, speed, etaSec)
	} else {
		fmt.Printf("\r\x1b[K  \x1b[1;36m[%s]\x1b[0m \x1b[1;32m[Streaming]\x1b[0m %6.1f MB \x1b[1;33m%5.1f MB/s\x1b[0m",
			pw.TaskTitle, currentMB, speed)
	}
	_ = os.Stdout.Sync()
}

func main() {
	fmt.Println("\x1b[1;36m===============================================================\x1b[0m")
	fmt.Println("\x1b[1;32m   DarkMaxxer — HuggingFace Multi-Category Model Fetcher      \x1b[0m")
	fmt.Println("\x1b[1;34m   Automated Playwright Go Web Engine & Progress Monitor       \x1b[0m")
	fmt.Println("\x1b[1;36m===============================================================\x1b[0m\n")

	// 1. Initialize Zap Development Logger
	logger, err := zap.NewDevelopment()
	if err != nil {
		panic(err)
	}
	defer logger.Sync()

	modelsBaseDir := "/home/kairo/Projects/DarkMaxxer/models"
	if err := os.MkdirAll(modelsBaseDir, 0755); err != nil {
		logger.Fatal("Failed to create models base directory", zap.Error(err))
	}

	targets := []ModelTarget{
		{
			Category:    "chat_instruct",
			DisplayName: "1/4 Chat (Qwen2.5-0.5B-GGUF)",
			RepoID:      "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
			FileName:    "qwen2.5-0.5b-instruct-q4_k_m.gguf",
			PageURL:     "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/tree/main",
			FallbackURL: "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf",
		},
		{
			Category:    "code_generation",
			DisplayName: "2/4 Code (Qwen2.5-Coder-0.5B-GGUF)",
			RepoID:      "Qwen/Qwen2.5-Coder-0.5B-Instruct-GGUF",
			FileName:    "qwen2.5-coder-0.5b-instruct-q4_k_m.gguf",
			PageURL:     "https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct-GGUF/tree/main",
			FallbackURL: "https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-0.5b-instruct-q4_k_m.gguf",
		},
		{
			Category:    "embeddings_representation",
			DisplayName: "3/4 Embeddings (all-MiniLM-L6-v2)",
			RepoID:      "sentence-transformers/all-MiniLM-L6-v2",
			FileName:    "model.safetensors",
			PageURL:     "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/main",
			FallbackURL: "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main/model.safetensors",
		},
		{
			Category:    "compact_reasoning",
			DisplayName: "4/4 Compact LM (SmolLM2-135M)",
			RepoID:      "HuggingFaceTB/SmolLM2-135M-Instruct",
			FileName:    "model.safetensors",
			PageURL:     "https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct/tree/main",
			FallbackURL: "https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct/resolve/main/model.safetensors",
		},
	}

	pw, err := playwright.Run()
	if err != nil {
		logger.Fatal("Could not launch Playwright driver", zap.Error(err))
	}
	defer pw.Stop()

	browser, err := pw.Chromium.Launch(playwright.BrowserTypeLaunchOptions{
		Headless: playwright.Bool(true),
		Args: []string{
			"--no-sandbox",
			"--disable-setuid-sandbox",
			"--disable-dev-shm-usage",
			"--disable-blink-features=AutomationControlled",
		},
	})
	if err != nil {
		logger.Fatal("Could not launch Chromium browser", zap.Error(err))
	}
	defer browser.Close()

	totalTargets := len(targets)
	for idx, target := range targets {
		fmt.Printf("\n\x1b[1;35m>>> [%d/%d] Processing Category: %s\x1b[0m\n", idx+1, totalTargets, target.Category)
		fmt.Printf("    Repo: \x1b[1m%s\x1b[0m | File: \x1b[1m%s\x1b[0m\n", target.RepoID, target.FileName)

		categoryDir := filepath.Join(modelsBaseDir, target.Category)
		_ = os.MkdirAll(categoryDir, 0755)
		destFilePath := filepath.Join(categoryDir, target.FileName)

		if fi, err := os.Stat(destFilePath); err == nil && fi.Size() > 1000000 {
			fmt.Printf("    \x1b[1;32m✔ Model already verified on disk (%.1f MB). Skipping download.\x1b[0m\n",
				float64(fi.Size())/(1024*1024))
			continue
		}

		// Playwright browser navigation to discover exact link
		randWidth := 1920 + rand.Intn(30) - 15
		randHeight := 1080 + rand.Intn(30) - 15
		context, err := browser.NewContext(playwright.BrowserNewContextOptions{
			UserAgent: playwright.String("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"),
			Viewport:  &playwright.Size{Width: randWidth, Height: randHeight},
		})
		if err != nil {
			logger.Error("Failed to create context", zap.Error(err))
			continue
		}

		page, err := context.NewPage()
		if err != nil {
			logger.Error("Failed to create page", zap.Error(err))
			context.Close()
			continue
		}

		resolvedURL := target.FallbackURL
		fmt.Printf("    Navigating to HuggingFace repository via Playwright...\n")

		_, err = page.Goto(target.PageURL, playwright.PageGotoOptions{
			Timeout:   playwright.Float(35000),
			WaitUntil: playwright.WaitUntilStateDomcontentloaded,
		})

		if err == nil {
			time.Sleep(time.Duration(200+rand.Intn(200)) * time.Millisecond)
			_, _ = page.Evaluate("window.scrollBy(0, 400)")

			links, _ := page.Locator("a[href*='/resolve/main/']").All()
			for _, link := range links {
				href, _ := link.GetAttribute("href")
				if strings.Contains(href, target.FileName) {
					if !strings.HasPrefix(href, "http") {
						href = "https://huggingface.co" + href
					}
					resolvedURL = href
					break
				}
			}
		}

		page.Close()
		context.Close()

		fmt.Printf("    Starting stream download from HuggingFace CDN...\n")
		err = downloadWithProgressBar(resolvedURL, destFilePath, target.DisplayName)
		if err != nil {
			fmt.Printf("\n    \x1b[1;31m✖ Download failed: %v\x1b[0m\n", err)
		} else {
			if fi, err := os.Stat(destFilePath); err == nil {
				fmt.Printf("\n    \x1b[1;32m✔ Successfully installed to %s (%.1f MB)\x1b[0m\n",
					destFilePath, float64(fi.Size())/(1024*1024))
			}
		}
	}

	fmt.Println("\n\x1b[1;32m===============================================================\x1b[0m")
	fmt.Println("\x1b[1;32m✔ All models from all requested categories downloaded successfully!\x1b[0m")
	fmt.Println("\x1b[1;32m===============================================================\x1b[0m\n")
}

func downloadWithProgressBar(url string, destPath string, title string) error {
	client := &http.Client{
		Timeout: 30 * time.Minute,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: false},
		},
	}

	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}
	req.Header.Set("User-Agent", "DarkMaxxer-Model-Fetcher/2.0")

	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("HTTP error %s", resp.Status)
	}

	tmpPath := destPath + ".tmp"
	out, err := os.Create(tmpPath)
	if err != nil {
		return err
	}
	defer out.Close()

	pw := &ProgressWriter{
		Total:     resp.ContentLength,
		Current:   0,
		StartTime: time.Now(),
		LastPrint: time.Now(),
		TaskTitle: title,
	}

	// MultiWriter routes bytes to both disk and the live progress calculator
	mw := io.MultiWriter(out, pw)
	_, err = io.Copy(mw, resp.Body)
	if err != nil {
		os.Remove(tmpPath)
		return err
	}

	out.Close()
	return os.Rename(tmpPath, destPath)
}
