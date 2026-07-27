# APEX Top Free-Tier Operations Architecture

> **Policy:** Maximum High-Agency Execution at $0 Egress Cost  
> **Guiding Principle:** Local-First Compute + Zero-Cost Cloud Relays + MICROWAVE Context Savings (~95%).

---

## 1. Zero-Cost Compute Stack

| Operational Layer | Free Tier Provider / Component | Egress Cost | Configuration File |
| :--- | :--- | :---: | :--- |
| **Local Compute** | Local macOS / Termux / iSH CPU | **$0.00** | `~/bin/apex-*` |
| **Context Optimization** | `token_saver` (MICROWAVE pure_pointer) | **$0.00** | `~/.apex/token_saver.json` |
| **Cloud MCP Relay** | Vercel Serverless / SSE (`mimo-free-relay`) | **$0.00** | `mimo-code/.mcp.json` |
| **CI/CD Build Pipelines** | GitHub Actions Free Runner Allowance (2,000 min/mo) | **$0.00** | `.github/workflows/ci.yml` |
| **State Persistence** | Local JSON Ledgers + GitHub Public Repos | **$0.00** | `~/.apex/*.json` |

---

## 2. Multi-Device Synchronized Deployment

```
                       ┌──────────────────────────────────────┐
                       │     APEX FREE-TIER CLOUD RELAY       │
                       │     (github.com/GlacierEQ/*)         │
                       └──────────────────┬───────────────────┘
                                          │
       ┌──────────────────────────────────┼──────────────────────────────────┐
       ▼                                  ▼                                  ▼
┌────────────────────────┐    ┌────────────────────────┐    ┌────────────────────────┐
│  MacBook Air (2015)    │    │ Android Pixel Tablet   │    │ iPhone 16 Pro Max      │
│  iTerm2 / zsh          │    │ Termux / Android CLI   │    │ iSH Shell / Alpine     │
│  (Full macOS Suite)    │    │ (apex-android-install) │    │ (apex-ish-install)     │
└────────────────────────┘    └────────────────────────┘    └────────────────────────┘
```

---

## 3. Multi-Device Install Commands

### 💻 MacBook Air 2015 (iTerm2 / macOS)
```bash
# Ensure ~/bin is on your PATH
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc

# Run local APEX installer
bash ~/job-app/repos/apex-cli/install.sh
```

### 📱 Android Pixel Tablet (Termux)
```bash
pkg update && pkg install -y python git bash
git clone https://github.com/GlacierEQ/apex-cli.git ~/apex-cli
cd ~/apex-cli && bash install.sh
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
```

### 📱 iPhone 16 Pro Max (iSH App)
```bash
apk update && apk add python3 bash git
git clone https://github.com/GlacierEQ/apex-cli.git ~/apex-cli
cd ~/apex-cli && bash install.sh
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.profile && source ~/.profile
```
