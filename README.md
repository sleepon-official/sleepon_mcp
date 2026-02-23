# Sleepon MCP Server

[![PyPI](https://img.shields.io/pypi/v/sleepon-mcp)](https://pypi.org/project/sleepon-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that connects AI assistants like **Claude** to your [Sleepon](https://www.sleepon.us) sleep tracker data. Ask your AI to analyze your sleep quality, compare nights, generate reports, and get personalized improvement tips — all powered by your real sleep data.

## Features

- 🛏️ **Daily Sleep Summary** — sleep score, efficiency, duration, and stage breakdown
- 📊 **Detailed Segments** — per-segment heart rate, blood oxygen (SpO2), HRV, movement, and ODI
- 📅 **Sleep Calendar** — see which days have data over a date range
- 📈 **Trend Analysis** — track how your sleep metrics change over time
- 🏷️ **Sleep Labels** — view user-added tags (e.g. "exercised", "drank coffee") and notes
- 🤖 **Built-in Prompts** — one-click deep analysis, comparison, reports, and improvement tips

## Quick Start

### 1. Install

```bash
# Using uvx (recommended, auto-downloads without install)
uvx sleepon-mcp

# Or install via pip
pip install sleepon-mcp
```

### 2. Configure Claude Desktop

To use this MCP server with Claude Desktop, you need to add it to your configuration file.

**Step 1:** Open the configuration file based on your operating system:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

*(Tip: You can quickly open this from Claude Desktop: Menu -> Settings -> Developer -> Edit Config)*

**Step 2:** Add the `sleepon` server to the `mcpServers` object. Replace the email and password with your actual Sleepon account credentials.

```json
{
  "mcpServers": {
    "sleepon": {
      "command": "uvx",
      "args": ["sleepon-mcp"],
      "env": {
        "SLEEPON_USERNAME": "your-sleepon-email@example.com",
        "SLEEPON_PASSWORD": "your-password"
      }
    }
  }
}
```

*Note: `uvx` is recommended as it automatically manages the Python environment for you. If you prefer to use your system Python, you can use `"command": "python", "args": ["-m", "sleepon_mcp.server"]` instead.*

> ⚠️ **Troubleshooting: `spawn uvx ENOENT` Error**
> If Claude Desktop shows an `ENOENT` error, it means it cannot find the `uvx` command in its system path. To fix this, you must provide the **absolute path** to `uvx`.
> 1. Open your terminal and run `which uvx` (Mac/Linux) or `where uvx` (Windows).
> 2. Copy the resulting path (e.g., `/Users/username/.pyenv/shims/uvx` or `C:\\Users\\username\\.cargo\\bin\\uvx.exe`).
> 3. Replace `"uvx"` in the `"command"` field of the config with this absolute path.

### 3. Restart Claude Desktop

1. Completely quit Claude Desktop (`Cmd+Q` on Mac, or right-click the system tray icon and exit on Windows).
2. Re-open Claude Desktop.
3. Look for the **hammer icon (🔨)** in the chat input area. Click on it to see the available Sleepon tools and prompts.

---

## Available Tools

| Tool | Description |
|---|---|
| `login_and_check_status` | Verify that your credentials are correct and the API is reachable |
| `get_user_profile` | Get your Sleepon user profile information |
| `get_daily_sleep_summary` | Get complete sleep summary for a specific date |
| `get_detailed_sleep_segments` | Get detailed segment data (heart rate, SpO2, HRV, sleep stages) |
| `get_sleep_calendar` | View which days have data in a date range |
| `get_sleep_trend` | Get sleep metric trends over a date range |
| `get_sleep_labels` | Get user-added sleep labels and notes for a date |
| `get_latest_data_time` | Find the most recent data sync timestamp |

## Built-in Prompts

These prompts guide the AI through multi-step analysis workflows:

| Prompt | Description |
|---|---|
| `analyze_sleep` | Comprehensive analysis of a single night (summary + segments + labels) |
| `compare_sleep` | Side-by-side comparison of two nights with tables |
| `sleep_report` | Full report for a date range (trends, best/worst days, health alerts) |
| `sleep_improvement_tips` | Personalized recommendations based on your recent data |

## Example Conversations

- *"Analyze my sleep from last night"*
- *"Compare my sleep on Monday vs Friday"*
- *"Generate a sleep report for the past month"*
- *"How can I improve my sleep quality?"*

## Development

```bash
# Clone the repo
git clone https://github.com/sleepon-official/sleepon_mcp.git
cd sleepon_mcp

# Install in development mode
pip install -e .

# Test with MCP Inspector
npx -y @modelcontextprotocol/inspector sleepon-mcp
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SLEEPON_USERNAME` | Yes | Your Sleepon account email |
| `SLEEPON_PASSWORD` | Yes | Your Sleepon account password |

## Requirements

- Python >= 3.10
- A [Sleepon](https://www.sleepon.us) account with a paired sleep tracker

## License

[MIT](LICENSE)
