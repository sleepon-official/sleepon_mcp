# Sleepon MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that connects AI assistants like **Claude** to your [Sleepon](https://www.sleepon.com) sleep tracker data. Ask your AI to analyze your sleep quality, compare nights, generate reports, and get personalized improvement tips — all powered by your real sleep data.

## Quick Start

### 1. Install

```bash
# Using uvx (recommended, no install needed)
uvx sleepon-mcp

# Or install via pip
pip install sleepon-mcp
```

### 2. Configure Claude Desktop

Add the following to your Claude Desktop configuration file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

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

### 3. Restart Claude Desktop

After saving the config, restart Claude Desktop. You'll see the Sleepon tools available in the MCP tools menu.

---

## Available Tools

| Tool | Description |
|---|---|
| `login_and_check_status` | Verify that your credentials are correct |
| `get_user_profile` | Get your Sleepon user profile |
| `get_daily_sleep_summary` | Get complete sleep summary for a specific date |
| `get_detailed_sleep_segments` | Get detailed segment data (heart rate, SpO2, HRV, stages) |
| `get_sleep_calendar` | View which days have data in a date range |
| `get_sleep_trend` | Get sleep metric trends over a date range |
| `get_sleep_labels` | Get user-added sleep labels and notes |
| `get_latest_data_time` | Find the most recent data sync date |

## Built-in Prompts

| Prompt | Description |
|---|---|
| `analyze_sleep` | Deep analysis of a single night's sleep |
| `compare_sleep` | Side-by-side comparison of two nights |
| `sleep_report` | Comprehensive report for a date range |
| `sleep_improvement_tips` | Personalized tips based on recent data |

## Example Conversations

- *"Analyze my sleep from last night"*
- *"Compare my sleep on Monday vs Friday"*
- *"Generate a sleep report for the past month"*
- *"How can I improve my sleep quality?"*

## Development

```bash
# Clone the repo
git clone https://github.com/your-org/sleepon-mcp-server.git
cd sleepon-mcp-server

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

## License

MIT
