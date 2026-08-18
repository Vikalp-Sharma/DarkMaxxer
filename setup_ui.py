#!/usr/bin/python3
# [Vikalp Sharma] - Proprietary / Anti-Theft Watermark
# DarkMaxxer — First-Run Setup UI
# Red-themed tkinter GUI with dual progress bars (red=overall, blue=per-package)
# Uses ONLY tkinter — no pip dependencies required.

import os
import sys
import subprocess
import threading
import time
import re
import math
import shutil

# ── Paths ─────────────────────────────────────────────────────────
APP_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(APP_DIR, "venv")
REQ_FILE = os.path.join(APP_DIR, "requirements.txt")
LOGO_PATH = os.path.join(APP_DIR, "gui", "logo.png")
SETUP_MARKER = os.path.join(VENV_DIR, ".setup_complete")

# Compressed venv archives bundled inside the installer
ARCHIVE_CPU = os.path.join(APP_DIR, "venv_cpu.tar.zst")
ARCHIVE_ROCM = os.path.join(APP_DIR, "venv_rocm.tar.zst")
ARCHIVE_NVIDIA = os.path.join(APP_DIR, "venv_nvidia.tar.zst")

# Map: mode → (archive_path, extracted_dir_name_inside_tar)
ARCHIVE_MAP = {
    "cpu":        (ARCHIVE_CPU,    "dm_venv_cpu"),
    "gpu_amd":    (ARCHIVE_ROCM,   "dm_venv_rocm"),
    "gpu_nvidia": (ARCHIVE_NVIDIA, "dm_venv_nvidia"),
}



# ── Theme ─────────────────────────────────────────────────────
BG        = "#0a0a0f"
BORDER    = "#1a1014"
RED       = "#dc2626"
RED_DK    = "#7f1d1d"
RED_GLO   = "#ef4444"
RED_BRT   = "#f87171"
BLUE      = "#3b82f6"
BLUE_DK   = "#1e3a5f"
BLUE_GLO  = "#60a5fa"
GREEN     = "#22c55e"
WHITE     = "#e4e4e7"
DIM       = "#71717a"
MUTED     = "#3f3f46"
TRACK     = "#18181b"

# ╔════════════════════════════════════════════════════════════╗
# ║                       HELPERS                             ║
# ╚════════════════════════════════════════════════════════════╝


def detect_gpu():
    """Detect GPU vendor via lspci. Returns 'amd', 'nvidia', or 'none'."""
    try:
        lspci = subprocess.check_output(
            ["lspci", "-nn"], stderr=subprocess.STDOUT, text=True).lower()
        # Find lines with 'vga', '3d', or 'display' to avoid mistaking AMD CPU/Host Bridge for AMD GPU
        for line in lspci.splitlines():
            if "vga" in line or "3d" in line or "display" in line:
                if "nvidia" in line:
                    return "nvidia"
                if "amd" in line or "radeon" in line:
                    return "amd"
    except Exception:
        pass
    return "none"



def parse_requirements(path):
    # Packages that are Windows-only or build-tools not needed at runtime
    _SKIP_LINUX = {"pythonnet", "pyinstaller"}
    _SKIP_WIN   = set()

    skip = _SKIP_LINUX if sys.platform.startswith("linux") else _SKIP_WIN

    pkgs = []
    if not os.path.isfile(path):
        return pkgs
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            name = re.split(r"[><=!~\[;]", line)[0].strip()
            if name and name.lower() not in skip:
                pkgs.append(name)
    return pkgs


def has_display():
    if sys.platform.startswith("linux"):
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return True


def _best_font():
    try:
        import tkinter.font as tkfont
        import tkinter as _tk
        _r = _tk.Tk(); _r.withdraw()
        fams = {f.lower(): f for f in tkfont.families(root=_r)}
        _r.destroy()
        for c in ("inter", "cantarell", "noto sans", "ubuntu",
                   "liberation sans", "dejavu sans"):
            if c in fams:
                return fams[c]
    except Exception:
        pass
    return "Helvetica"


# ╔════════════════════════════════════════════════════════════╗
# ║                   GRAPHICAL SETUP UI                      ║
# ╚════════════════════════════════════════════════════════════╝

class DarkMaxxerSetup:
    """Dual-bar setup window — normal (non-overlay) dialog with WM rounded corners."""

    W, H = 580, 640

    def __init__(self):
        import tkinter as tk
        self.tk = tk

        self.root = tk.Tk()
        self.root.title("DarkMaxxer — Setup")
        self.root.configure(bg=BG)
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.resizable(False, False)

        # Centre on screen
        self.root.update_idletasks()
        sx, sy = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"+{(sx-self.W)//2}+{(sy-self.H)//2}")

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Dialog type → WM gives rounded corners, minimal decorations, no overlay
        try:
            self.root.attributes("-type", "dialog")
        except Exception:
            pass

        # State
        self.ff = _best_font()
        self.packages = parse_requirements(REQ_FILE)
        self.total = len(self.packages)
        self.current_idx = 0
        self.gpu_mode = None  # 'cpu', 'gpu_amd', 'gpu_nvidia'

        self.progress    = 0.0
        self.glow_phase  = 0.0
        self.sweep_pos   = 0
        self.blue_active = False
        self.blue_done   = False
        self.finished    = False
        self.failed      = False

        # Bar dimensions
        self.bar_w  = self.W - 80
        self.bar_h  = 20
        self.bar_r  = self.bar_h // 2
        self.blue_h = 10
        self.blue_r = self.blue_h // 2

        # Check if setup already completed → skip selection, go straight to verify
        if os.path.isfile(SETUP_MARKER):
            self.gpu_mode = "skip"  # user already picked CPU/GPU
            self._build_ui()
            self.root.after(600, self._begin_install)
            return

        self._build_selection_ui()

    # ── GPU Selection Screen ───────────────────────────────────
    def _build_selection_ui(self):
        tk = self.tk; ff = self.ff
        self.sel_frame = tk.Frame(self.root, bg=BG)
        self.sel_frame.pack(fill="both", expand=True, padx=28, pady=20)

        # Logo
        self.logo_img = None
        try:
            raw = tk.PhotoImage(file=LOGO_PATH)
            factor = max(1, raw.width() // 72)
            self.logo_img = raw.subsample(factor, factor)
            tk.Label(self.sel_frame, image=self.logo_img,
                     bg=BG, bd=0).pack(pady=(0, 8))
        except Exception:
            pass

        tk.Label(self.sel_frame, text="DARKMAXXER",
                 font=(ff, 20, "bold"), fg=WHITE, bg=BG).pack()
        tk.Label(self.sel_frame, text="First-Time Setup",
                 font=(ff, 11), fg=DIM, bg=BG).pack(pady=(2, 20))

        # Auto-detect GPU
        gpu_vendor = detect_gpu()

        tk.Label(self.sel_frame,
                 text="Select your compute mode:",
                 font=(ff, 13, "bold"), fg=WHITE, bg=BG).pack(pady=(10, 4))

        # Show detected hardware
        if gpu_vendor == "amd":
            hw_text = "✔ AMD GPU detected — ROCm acceleration available"
            hw_color = "#22c55e"
        elif gpu_vendor == "nvidia":
            hw_text = "✔ NVIDIA GPU detected — CUDA acceleration available"
            hw_color = "#22c55e"
        else:
            hw_text = "✘ No supported GPU detected — CPU mode only"
            hw_color = "#ef4444"

        tk.Label(self.sel_frame, text=hw_text,
                 font=(ff, 9), fg=hw_color, bg=BG).pack(pady=(0, 16))

        btn_frame = tk.Frame(self.sel_frame, bg=BG)
        btn_frame.pack(pady=10)

        if gpu_vendor != "none":
            # GPU button with specific label
            gpu_label = ("⚡  GPU — AMD ROCm" if gpu_vendor == "amd"
                         else "⚡  GPU — NVIDIA CUDA")
            gpu_mode = ("gpu_amd" if gpu_vendor == "amd" else "gpu_nvidia")

            gpu_btn = tk.Button(
                btn_frame, text=f"  {gpu_label}  (Recommended)  ",
                font=(ff, 13, "bold"), bg="#1e3a5f", fg=WHITE,
                activebackground="#3b82f6", activeforeground=WHITE,
                relief="flat", cursor="hand2", bd=0, padx=24, pady=12,
                command=lambda m=gpu_mode: self._select_mode(m))
            gpu_btn.pack(pady=6, fill="x")

        cpu_btn = tk.Button(
            btn_frame,
            text=("  🖥  CPU Only  " if gpu_vendor != "none"
                  else "  🖥  CPU Only  (Continue)  "),
            font=(ff, 13, "bold" if gpu_vendor == "none" else ""),
            bg=("#1e3a5f" if gpu_vendor == "none" else TRACK),
            fg=(WHITE if gpu_vendor == "none" else DIM),
            activebackground="#27272a", activeforeground=WHITE,
            relief="flat", cursor="hand2", bd=0, padx=24, pady=12,
            command=lambda: self._select_mode("cpu"))
        cpu_btn.pack(pady=6, fill="x")

        if gpu_vendor != "none":
            tk.Label(self.sel_frame,
                     text="GPU: Faster inference using your graphics card\n"
                          "CPU: Works on any machine, slower",
                     font=(ff, 9), fg=MUTED, bg=BG,
                     justify="center").pack(pady=(16, 0))

    def _select_mode(self, mode):
        self.gpu_mode = mode
        self.sel_frame.destroy()
        self._build_ui()
        self.root.after(400, self._begin_install)

    # ── Build Progress UI ─────────────────────────────────────
    def _build_ui(self):
        tk = self.tk; ff = self.ff

        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=28, pady=20)

        # Logo
        if not hasattr(self, 'logo_img') or self.logo_img is None:
            try:
                raw = tk.PhotoImage(file=LOGO_PATH)
                factor = max(1, raw.width() // 72)
                self.logo_img = raw.subsample(factor, factor)
            except Exception:
                pass
        if self.logo_img:
            tk.Label(main, image=self.logo_img, bg=BG, bd=0).pack(pady=(0, 8))

        # Title
        tk.Label(main, text="DARKMAXXER", font=(ff, 20, "bold"),
                 fg=WHITE, bg=BG).pack()

        # Subtitle
        mode_text = {
            "cpu": "CPU Mode",
            "gpu_amd": "GPU Mode — AMD ROCm",
            "gpu_nvidia": "GPU Mode — NVIDIA CUDA",
            "skip": "Verifying installation…",
        }.get(self.gpu_mode, "Preparing your environment…")
        self.phase_lbl = tk.Label(main, text=mode_text,
                                   font=(ff, 10), fg=DIM, bg=BG)
        self.phase_lbl.pack(pady=(2, 10))

        # Hardware info


        # ── Red bar: overall progress ────────────────────────
        tk.Label(main, text="Overall Progress", font=(ff, 9, "bold"),
                 fg=DIM, bg=BG, anchor="w").pack(fill="x")

        self.red_cv = tk.Canvas(main, width=self.bar_w, height=self.bar_h,
                                bg=BG, highlightthickness=0, bd=0)
        self.red_cv.pack(pady=(4, 0))
        self._rounded_rect(self.red_cv, 0, 0, self.bar_w, self.bar_h,
                           self.bar_r, fill=TRACK, outline="")

        ri = tk.Frame(main, bg=BG); ri.pack(fill="x", pady=(4, 14))
        self.pct_var = tk.StringVar(value="0%")
        tk.Label(ri, textvariable=self.pct_var, font=(ff, 11, "bold"),
                 fg=RED, bg=BG).pack(side="left")
        self.ctr_var = tk.StringVar(value=f"0 / {self.total} packages")
        tk.Label(ri, textvariable=self.ctr_var, font=(ff, 9),
                 fg=MUTED, bg=BG).pack(side="right")

        # ── Blue bar: current package ────────────────────────
        self.blue_lbl_var = tk.StringVar(value="Current Package")
        tk.Label(main, textvariable=self.blue_lbl_var, font=(ff, 9, "bold"),
                 fg=DIM, bg=BG, anchor="w").pack(fill="x")

        self.blue_cv = tk.Canvas(main, width=self.bar_w, height=self.blue_h,
                                  bg=BG, highlightthickness=0, bd=0)
        self.blue_cv.pack(pady=(4, 0))
        self._rounded_rect(self.blue_cv, 0, 0, self.bar_w, self.blue_h,
                           self.blue_r, fill=TRACK, outline="")

        self.blue_st_var = tk.StringVar(value="Waiting…")
        tk.Label(main, textvariable=self.blue_st_var, font=(ff, 8),
                 fg=MUTED, bg=BG, anchor="w",
                 wraplength=self.bar_w).pack(fill="x", pady=(3, 12))

        # Status
        self.status_var = tk.StringVar(value="Initializing…")
        tk.Label(main, textvariable=self.status_var, font=(ff, 9),
                 fg=DIM, bg=BG, wraplength=self.bar_w).pack(pady=(0, 6))

        # ── Pseudo Terminal Box (5 lines) ──────────────────────────
        tk.Label(main, text="CONSOLE LOG", font=(ff, 8, "bold"),
                 fg=DIM, bg=BG, anchor="w").pack(fill="x", pady=(4, 2))

        term_box = tk.Frame(main, bg="#050508", bd=1, relief="solid",
                            highlightbackground="#1e1e24", highlightthickness=1)
        term_box.pack(fill="x", pady=(0, 6))

        self.log_buffer = ["$ pip install -r requirements.txt", "", "", "", ""]
        self.term_lbl = tk.Label(term_box, text="\n".join(self.log_buffer),
                                 font=("Monospace", 8), fg="#4ade80", bg="#050508",
                                 justify="left", anchor="nw", height=5,
                                 wraplength=self.bar_w - 16)
        self.term_lbl.pack(fill="both", expand=True, padx=8, pady=6)

        # Error button frame (empty until needed)
        self.btn_frame = tk.Frame(main, bg=BG)
        self.btn_frame.pack()

        # Footer
        tk.Label(main, text="⚡  Please wait — do not close this window",
                 font=(ff, 8), fg=MUTED, bg=BG).pack(side="bottom", pady=(0, 4))

        # Start animation loop
        self._animate()

    # ── Canvas drawing ────────────────────────────────────────
    def _rounded_rect(self, cv, x1, y1, x2, y2, r, **kw):
        pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r,
               x2,y2-r, x2,y2, x2-r,y2, x1+r,y2,
               x1,y2, x1,y2-r, x1,y1+r, x1,y1]
        return cv.create_polygon(pts, smooth=True, **kw)

    def _clip_dy(self, ix, w, r, h):
        """Vertical clip offset for a rounded bar at pixel ix."""
        if ix < r:
            d = r - ix
            sq = r*r - d*d
            return r - int(math.sqrt(max(0, sq))) if sq > 0 else h // 2
        if ix > w - r - 1:
            d = ix - (w - r - 1)
            sq = r*r - d*d
            return r - int(math.sqrt(max(0, sq))) if sq > 0 else h // 2
        return 0

    # ── Red bar (gradient fill) ──
    def _paint_red(self):
        self.red_cv.delete("fill")
        if self.progress <= 0:
            return
        fw = max(self.bar_r * 2 + 2, int(self.bar_w * self.progress))
        fw = min(fw, self.bar_w)
        for ix in range(fw):
            t = ix / max(1, fw - 1)
            r = int(0x7F + (0xDC - 0x7F) * t)
            g = int(0x1D + (0x26 - 0x1D) * t)
            b = int(0x1D + (0x26 - 0x1D) * t)
            dy = self._clip_dy(ix, fw, self.bar_r, self.bar_h)
            self.red_cv.create_line(ix, dy + 1, ix, self.bar_h - dy - 1,
                                    fill=f"#{r:02x}{g:02x}{b:02x}", tags="fill")
        # Glow tip
        if 0 < self.progress < 1.0 and fw > 6:
            p = 0.5 + 0.5 * math.sin(self.glow_phase)
            gr = int(0xDC + (0xF8 - 0xDC) * p)
            gg = int(0x26 + (0x71 - 0x26) * p)
            gb = int(0x26 + (0x71 - 0x26) * p)
            sz = int(4 + 2 * p)
            cx, cy = fw - 2, self.bar_h // 2
            self.red_cv.create_oval(cx-sz, cy-sz, cx+sz, cy+sz,
                                    fill=f"#{gr:02x}{gg:02x}{gb:02x}",
                                    outline="", tags="fill")

    # ── Blue bar (indeterminate sweep) ──
    def _paint_blue_sweep(self):
        self.blue_cv.delete("fill")
        sw = 100
        cx = self.sweep_pos
        for i in range(sw):
            t = i / sw
            bri = (1.0 - abs(2 * t - 1)) ** 0.6
            px = int(cx - sw / 2 + i)
            if px < 0 or px >= self.bar_w:
                continue
            r = int(0x18 + (0x3B - 0x18) * bri)
            g = int(0x18 + (0x82 - 0x18) * bri)
            b = int(0x1B + (0xF6 - 0x1B) * bri)
            dy = self._clip_dy(px, self.bar_w, self.blue_r, self.blue_h)
            self.blue_cv.create_line(px, dy + 1, px, self.blue_h - dy - 1,
                                      fill=f"#{r:02x}{g:02x}{b:02x}", tags="fill")

    def _paint_blue_full(self):
        self.blue_cv.delete("fill")
        for ix in range(self.bar_w):
            t = ix / max(1, self.bar_w - 1)
            r = int(0x1E + (0x3B - 0x1E) * t)
            g = int(0x3A + (0x82 - 0x3A) * t)
            b = int(0x5F + (0xF6 - 0x5F) * t)
            dy = self._clip_dy(ix, self.bar_w, self.blue_r, self.blue_h)
            self.blue_cv.create_line(ix, dy + 1, ix, self.blue_h - dy - 1,
                                      fill=f"#{r:02x}{g:02x}{b:02x}", tags="fill")

    # ── Animation loop ──
    def _animate(self):
        if self.finished:
            return
        self.glow_phase += 0.18
        if 0 < self.progress < 1.0:
            self._paint_red()
        if self.blue_active and not self.blue_done:
            self.sweep_pos = (self.sweep_pos + 5) % (self.bar_w + 100)
            self._paint_blue_sweep()
        self.root.after(50, self._animate)

    # ── Thread-safe setters ───────────────────────────────────
    def _set_red(self, frac, status="", phase=""):
        self.root.after(0, self._apply_red, frac, status, phase)

    def _apply_red(self, frac, status, phase):
        self.progress = max(self.progress, min(1.0, frac))
        self._paint_red()
        self.pct_var.set(f"{int(self.progress * 100)}%")
        if status:
            self.status_var.set(status)
        if phase:
            self.phase_lbl.configure(text=phase)
        self.ctr_var.set(f"{self.current_idx} / {self.total} packages")

    def _set_blue(self, label="", status="", active=True, done=False):
        self.root.after(0, self._apply_blue, label, status, active, done)

    def _apply_blue(self, label, status, active, done):
        if label:
            self.blue_lbl_var.set(label)
        if status:
            self.blue_st_var.set(status)
        self.blue_active = active
        self.blue_done = done
        if done:
            self._paint_blue_full()
        elif not active:
            self.blue_cv.delete("fill")

    def _is_progress(self, text):
        return ("MB" in text or "kB" in text or "B/s" in text or "eta" in text or "%" in text) and ("/" in text or "%" in text)

    def _append_log(self, text):
        if not hasattr(self, 'pending_logs'):
            self.pending_logs = []
            self.pending_logs_lock = threading.Lock()
            self.root.after(100, self._flush_logs)
        with self.pending_logs_lock:
            self.pending_logs.append(text)

    def _flush_logs(self):
        if not hasattr(self, 'pending_logs'):
            return
            
        with self.pending_logs_lock:
            if not self.pending_logs:
                self.root.after(100, self._flush_logs)
                return
            logs_to_process = self.pending_logs[:]
            self.pending_logs.clear()
            
        changed = False
        for text in logs_to_process:
            clean = text.strip()
            if not clean:
                continue
            if len(clean) > 85:
                clean = clean[:82] + "…"

            is_prog = self._is_progress(clean)
            if is_prog and self.log_buffer and self._is_progress(self.log_buffer[-1]):
                self.log_buffer[-1] = clean
            else:
                self.log_buffer.append(clean)
                if len(self.log_buffer) > 5:
                    self.log_buffer = self.log_buffer[-5:]
            changed = True

        if changed:
            lines = self.log_buffer + [""] * (5 - len(self.log_buffer))
            self.term_lbl.configure(text="\n".join(lines))
            self.term_lbl.update_idletasks()
            
        self.root.after(100, self._flush_logs)

    # ── Install worker ────────────────────────────────────────
    def _begin_install(self):
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            # ── Skip mode: setup already complete, just verify ──
            if self.gpu_mode == "skip":
                python_bin = os.path.join(VENV_DIR, "bin", "python3")
                self._set_red(0.50, "Verifying installation…",
                              "Quick verification")
                self._append_log("Setup marker found — verifying…")
                chk = subprocess.run(
                    [python_bin, "-c",
                     "import torch, airllm; print('ok')"],
                    capture_output=True, text=True, timeout=30)
                if "ok" in chk.stdout:
                    self._append_log("✔ All OK")
                    self.current_idx = self.total
                    self._set_red(1.0, "✔ Ready!",
                                  "Launching DarkMaxxer…")
                    self._set_blue("Complete", "✔ Ready to launch",
                                   active=False, done=True)
                    self.finished = True
                    self.root.after(0, self._show_success)
                    self.root.after(1500, self._finish)
                else:
                    self._error(
                        "Verification failed.\n"
                        "Try deleting venv/ and re-running.")
                return

            archive_path, tar_dir_name = ARCHIVE_MAP[self.gpu_mode]

            # ── 0–10%: Check archive + tools ─────────────────
            self._set_red(0.02, "Checking archives…",
                          "Step 1 / 4 — Preparation")
            self._set_blue("Archive", "Checking…")
            self._append_log(f"Selected mode: {self.gpu_mode}")
            self._append_log(f"Archive: {os.path.basename(archive_path)}")

            if not os.path.isfile(archive_path):
                self._error(
                    f"Archive not found:\n{archive_path}\n\n"
                    f"The installer may be corrupted.\n"
                    f"Please reinstall DarkMaxxer.")
                return

            arc_size = os.path.getsize(archive_path)
            arc_mb = arc_size / (1024 * 1024)
            self._append_log(f"Archive size: {arc_mb:.0f} MB")
            self._set_blue("Archive", f"✔ Found ({arc_mb:.0f} MB)",
                           active=False, done=True)

            # ── Ensure zstandard pip package is available ─────
            try:
                import zstandard as _zstd
                self._append_log("✔ zstandard available")
            except ImportError:
                self._append_log("zstandard not found — installing via pip…")
                self._set_blue("zstandard", "Installing pip package…")
                # Try with --break-system-packages for PEP 668 distros
                r = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--user",
                     "zstandard", "--break-system-packages"],
                    capture_output=True, text=True)
                if r.returncode != 0:
                    # Fallback without --break-system-packages
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install",
                         "--user", "zstandard"],
                        capture_output=True, text=True)
                try:
                    import zstandard as _zstd
                    self._append_log("✔ zstandard installed via pip")
                    self._set_blue("zstandard", "✔ Installed",
                                   active=False, done=True)
                except ImportError:
                    self._error(
                        "Failed to install 'zstandard' via pip.\n"
                        "Please run: pip install zstandard")
                    return

            self._set_red(0.10, "Ready to extract")

            # ── 10–60%: Extract selected venv ────────────────
            self._set_red(0.10, "Extracting environment…",
                          "Step 2 / 4 — Extraction")
            self._set_blue("Extracting", "Decompressing archive…")
            self._append_log(f"Extracting {os.path.basename(archive_path)}…")
            self._append_log("This may take a minute…")

            # Remove old venv if exists
            if os.path.isdir(VENV_DIR):
                import shutil
                self._append_log("Removing old venv…")
                shutil.rmtree(VENV_DIR, ignore_errors=True)

            # Extract purely in Python using zstandard + tarfile
            import tarfile
            extraction_done = threading.Event()
            extraction_error = [None]  # mutable container for thread

            def _do_extract():
                try:
                    dctx = _zstd.ZstdDecompressor()
                    with open(archive_path, 'rb') as ifh:
                        with dctx.stream_reader(ifh) as reader:
                            with tarfile.open(fileobj=reader, mode='r|') as tf:
                                try:
                                    tf.extractall(path=APP_DIR, filter='fully_trusted')
                                except TypeError:
                                    tf.extractall(path=APP_DIR)
                except Exception as e:
                    extraction_error[0] = e
                finally:
                    extraction_done.set()

            extract_thread = threading.Thread(target=_do_extract, daemon=True)
            start_t = time.time()
            extract_thread.start()

            # Animate extraction progress (10% → 60%)
            while not extraction_done.is_set():
                elapsed = time.time() - start_t
                est_frac = min(0.95, elapsed / 120.0)  # ~2 min estimate
                frac = 0.10 + 0.50 * est_frac
                self._set_red(frac, f"Extracting… {int(est_frac * 100)}%")
                time.sleep(0.3)

            if extraction_error[0]:
                self._error(f"Extraction failed:\n{str(extraction_error[0])[:400]}")
                return

            elapsed = time.time() - start_t
            self._append_log(f"✔ Extracted in {elapsed:.1f}s")

            # Rename extracted dir to "venv"
            extracted_dir = os.path.join(APP_DIR, tar_dir_name)
            if os.path.isdir(extracted_dir):
                os.rename(extracted_dir, VENV_DIR)
                self._append_log(f"✔ Extracted and renamed to venv/")
            elif os.path.isdir(VENV_DIR):
                self._append_log("✔ venv/ already in place")
            else:
                self._error(
                    f"Extraction produced unexpected directory.\n"
                    f"Expected: {tar_dir_name}")
                return

            self._set_red(0.60, "Extraction complete!")
            self._set_blue("Extracting", "✔ Done",
                           active=False, done=True)

            # ── Cleanup unused archives immediately ───────────
            self._append_log("Deleting all venv archives to save space…")
            arcs_to_delete = [arc for arc in [ARCHIVE_CPU, ARCHIVE_ROCM, ARCHIVE_NVIDIA] if os.path.isfile(arc)]
            if arcs_to_delete:
                permission_denied_arcs = []
                for arc in arcs_to_delete:
                    try:
                        os.remove(arc)
                        self._append_log(f"  Deleted {os.path.basename(arc)}")
                    except PermissionError:
                        permission_denied_arcs.append(arc)
                    except OSError as e:
                        self._append_log(f"  Warning: could not delete {os.path.basename(arc)}: {e}")
                
                if permission_denied_arcs:
                    import subprocess
                    try:
                        subprocess.run(["pkexec", "rm", "-f"] + permission_denied_arcs, check=True)
                        for arc in permission_denied_arcs:
                            self._append_log(f"  Deleted {os.path.basename(arc)} (via pkexec)")
                    except Exception as e:
                        self._append_log(f"  Warning: pkexec rm failed: {e}")

            # ── 60–90%: Verify all packages ──────────────────
            python_bin = os.path.join(VENV_DIR, "bin", "python3")
            self._set_red(0.60, "Verifying packages…",
                          "Step 3 / 4 — Verification")

            import_map = {
                "airllm": "airllm",
                "pywebview": "webview",
                "transformers": "transformers",
                "torch": "torch",
                "accelerate": "accelerate",
                "huggingface_hub": "huggingface_hub",
                "gguf": "gguf",
                "pillow": "PIL",
                "sentencepiece": "sentencepiece",
                "safetensors": "safetensors",
                "protobuf": "google.protobuf",
                "numpy": "numpy",
                "certifi": "certifi",
            }

            verify_pkgs = list(import_map.keys())
            total_verify = len(verify_pkgs)
            all_ok = True

            for i, pkg in enumerate(verify_pkgs):
                import_name = import_map[pkg]
                frac = 0.60 + 0.30 * ((i + 1) / total_verify)
                self._set_red(frac,
                    f"Verifying: {i + 1} / {total_verify}")
                self._set_blue(pkg, "Checking…")

                check = subprocess.run(
                    [python_bin, "-c", f"import {import_name}"],
                    capture_output=True, text=True, timeout=30)

                if check.returncode == 0:
                    self._append_log(f"✔ {pkg}")
                    self._set_blue(pkg, "✔ OK",
                                   active=False, done=True)
                else:
                    self._append_log(f"✘ {pkg} — FAILED")
                    self._set_blue(pkg, "✘ Failed")
                    all_ok = False

                self.current_idx = i + 1
                time.sleep(0.03)

            if not all_ok:
                self._error(
                    "Some packages failed verification.\n"
                    "The archive may be corrupted.\n"
                    "Try reinstalling DarkMaxxer.")
                return

            self._set_red(0.90, "All packages verified!")
            self._set_blue("Packages", "✔ All verified",
                           active=False, done=True)

            # ── 90–95%: Finalize ──────────────────────────────
            self._set_red(0.90, "Finalizing…",
                          "Step 4 / 4 — Finalizing")
            self._set_blue("Cleanup", "✔ Installation cleaned up",
                           active=False, done=True)
            self._set_red(0.95, "Finalizing…")

            # ── Marker + shortcut ─────────────────────────────
            try:
                with open(SETUP_MARKER, "w") as f:
                    f.write("ok\n")
            except OSError:
                pass
            self._update_desktop_shortcut()

            # ── Done ──────────────────────────────────────────
            self.current_idx = self.total
            self._set_red(1.0, "✔ Setup complete!",
                          "Launching DarkMaxxer…")
            self._set_blue("Complete", "✔ Ready to launch",
                           active=False, done=True)
            self.finished = True
            self.root.after(0, self._show_success)
            self.root.after(2200, self._finish)

        except Exception as exc:
            self._error(str(exc))

    # ── Desktop shortcut ──────────────────────────────────────
    def _update_desktop_shortcut(self):
        """Switch .desktop from 'setup' comment to normal app comment."""
        content = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=DarkMaxxer\n"
            "GenericName=AI Coding IDE\n"
            "Comment=Local AI Coding IDE — Run 70B+ parameter models "
            "on consumer hardware. No cloud. No API keys.\n"
            "Exec=/usr/local/bin/darkmaxxer\n"
            "Icon=darkmaxxer\n"
            "Terminal=false\n"
            "Categories=Development;IDE;ArtificialIntelligence;\n"
            "Keywords=AI;LLM;IDE;coding;local;offline;darkmaxxer;\n"
            "StartupNotify=true\n"
            "StartupWMClass=DarkMaxxer\n"
            "MimeType=text/plain;text/x-python;application/json;\n"
        )
        # Try system-wide first
        try:
            with open("/usr/share/applications/darkmaxxer.desktop", "w") as f:
                f.write(content)
            return
        except PermissionError:
            pass
        # Fall back to user-local override
        try:
            d = os.path.expanduser("~/.local/share/applications")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "darkmaxxer.desktop"), "w") as f:
                f.write(content)
        except Exception:
            pass

    # ── Success / Error UI ────────────────────────────────────
    def _show_success(self):
        self.pct_var.set("100%")
        self.phase_lbl.configure(text="Launching DarkMaxxer…", fg=GREEN)
        self.status_var.set("✔  Setup complete — starting application")
        self.ctr_var.set(f"{self.total} / {self.total} packages")
        self._paint_red()

    def _error(self, msg):
        self.failed = True
        self.finished = True
        self.root.after(0, self._show_error, msg)

    def _show_error(self, msg):
        self.phase_lbl.configure(text="Setup Failed", fg=RED_BRT)
        self.status_var.set(msg)
        self.blue_active = False
        tk = self.tk
        # Clear old buttons
        for w in self.btn_frame.winfo_children():
            w.destroy()
        tk.Button(self.btn_frame, text="  Retry  ", command=self._retry,
                  bg=RED_DK, fg=WHITE, activebackground=RED,
                  activeforeground=WHITE, font=(self.ff, 10),
                  relief="flat", cursor="hand2", bd=0,
                  padx=16, pady=6).pack(side="left", padx=6)
        tk.Button(self.btn_frame, text="  Close  ",
                  command=self._close_and_uninstall,
                  bg=TRACK, fg=DIM, activebackground="#27272a",
                  activeforeground=WHITE, font=(self.ff, 10),
                  relief="flat", cursor="hand2", bd=0,
                  padx=16, pady=6).pack(side="left", padx=6)

    def _retry(self):
        for w in self.btn_frame.winfo_children():
            w.destroy()
        self.failed = self.finished = False
        self.progress = self.glow_phase = 0.0
        self.current_idx = self.sweep_pos = 0
        self.blue_active = self.blue_done = False
        self.red_cv.delete("fill")
        self.blue_cv.delete("fill")
        self.pct_var.set("0%")
        self.status_var.set("Retrying…")
        self.phase_lbl.configure(text="Preparing your environment…", fg=DIM)
        self.ctr_var.set(f"0 / {self.total} packages")
        self.blue_lbl_var.set("Current Package")
        self.blue_st_var.set("Waiting…")
        self._animate()
        self.root.after(400, self._begin_install)

    def _on_close(self):
        """Handle window close — trigger full uninstall if incomplete."""
        if not self.finished and not self.failed:
            self._trigger_uninstall()
        self.finished = True
        self.failed = True
        try:
            self.root.destroy()
        except Exception:
            pass

    def _close_and_uninstall(self):
        """Close the error screen and trigger full uninstall."""
        self._trigger_uninstall()
        self.root.destroy()

    def _trigger_uninstall(self):
        """Spawns the uninstaller process to clean up everything."""
        import subprocess
        try:
            if sys.platform.startswith("linux"):
                # On Linux, call the wrapper to trigger the pkexec GUI uninstall
                cmd = ["darkmaxxer", "--uninstall"]
            else:
                # On Windows, run main.py which handles cleanup directly
                cmd = [sys.executable, os.path.join(APP_DIR, "main.py"), "--uninstall"]
                
            subprocess.Popen(cmd, cwd=APP_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def _finish(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()
        return 1 if self.failed else 0


# ╔════════════════════════════════════════════════════════════╗
# ║                TERMINAL FALLBACK                          ║
# ╚════════════════════════════════════════════════════════════╝

def run_terminal_install():
    try:
        C = "\033[1;31m[DarkMaxxer]\033[0m"
        print(f"{C} Setting up environment…")

        gpu_vendor = detect_gpu()
        if gpu_vendor == "amd":
            mode = "gpu_amd"
        elif gpu_vendor == "nvidia":
            mode = "gpu_nvidia"
        else:
            mode = "cpu"
            
        archive_path, tar_dir_name = ARCHIVE_MAP[mode]
        
        if not os.path.isfile(archive_path):
            print(f"{C} ERROR: Archive not found: {archive_path}")
            return 1

        try:
            import zstandard as _zstd
        except ImportError:
            print(f"{C} Installing zstandard…")
            # Try with --break-system-packages for PEP 668 distros
            r = subprocess.run([sys.executable, "-m", "pip", "install", "--user", "zstandard", "--break-system-packages"], capture_output=True)
            if r.returncode != 0:
                subprocess.run([sys.executable, "-m", "pip", "install", "--user", "zstandard"], capture_output=True)
            try:
                import zstandard as _zstd
            except ImportError:
                print(f"{C} ERROR: Failed to install zstandard")
                return 1

        if os.path.isdir(VENV_DIR):
            import shutil
            shutil.rmtree(VENV_DIR, ignore_errors=True)

        print(f"{C} Extracting {os.path.basename(archive_path)}…")
        import tarfile
        dctx = _zstd.ZstdDecompressor()
        with open(archive_path, 'rb') as ifh:
            with dctx.stream_reader(ifh) as reader:
                with tarfile.open(fileobj=reader, mode='r|') as tf:
                    try:
                        tf.extractall(path=APP_DIR, filter='fully_trusted')
                    except TypeError:
                        tf.extractall(path=APP_DIR)

        extracted_dir = os.path.join(APP_DIR, tar_dir_name)
        if os.path.isdir(extracted_dir):
            os.rename(extracted_dir, VENV_DIR)
        elif not os.path.isdir(VENV_DIR):
            print(f"{C} ERROR: Extraction failed")
            return 1

        python_bin = os.path.join(VENV_DIR, "bin", "python3")
        print(f"{C} Verifying installation…")
        if subprocess.run([python_bin, "-c", "import torch, airllm"], capture_output=True).returncode != 0:
            print(f"{C} ERROR: Verification failed")
            return 1

        print(f"{C} Cleaning up archives…")
        for arc in [ARCHIVE_CPU, ARCHIVE_ROCM, ARCHIVE_NVIDIA]:
            if os.path.isfile(arc):
                try:
                    os.remove(arc)
                except OSError:
                    pass

        try:
            with open(SETUP_MARKER, "w") as f:
                f.write("ok\n")
        except OSError:
            pass
        print(f"{C} \033[1;32m✔ Setup complete!\033[0m")
        return 0
    except Exception as e:
        print(f"{C} ERROR: {e}")
        return 1
    finally:
        marker = os.path.join(VENV_DIR, ".setup_complete")
        if os.path.isdir(VENV_DIR) and not os.path.exists(marker):
            try:
                import shutil
                shutil.rmtree(VENV_DIR, ignore_errors=True)
            except Exception:
                pass


# ╔════════════════════════════════════════════════════════════╗
# ║                       ENTRY                               ║
# ╚════════════════════════════════════════════════════════════╝

def main():
    if os.path.isfile(SETUP_MARKER):
        return 0
    if has_display():
        try:
            return DarkMaxxerSetup().run()
        except ImportError:
            print("[DarkMaxxer] tkinter unavailable — terminal mode")
            return run_terminal_install()
        except Exception as e:
            print(f"[DarkMaxxer] GUI error ({e}) — terminal mode")
            return run_terminal_install()
    else:
        return run_terminal_install()


if __name__ == "__main__":
    sys.exit(main())
