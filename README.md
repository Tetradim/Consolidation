# Consolidation Trading Bot

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Discord-API-green.svg" alt="Discord">
  <img src="https://img.shields.io/badge/Docker-Ready-blue.svg" alt="Docker">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

A production-grade Discord-based options trading bot that listens to trade alerts from financial analysts and automatically executes trades through your broker. Designed for community-based trading where you follow analyst alerts.

## Table of Contents

1. [What It Does](#what-it-does)
2. [How It Works](#how-it-works)
3. [Architecture](#architecture)
4. [Features](#features)
5. [Supported Brokers](#supported-brokers)
6. [Installation](#installation)
7. [Configuration](#configuration)
8. [Trading Strategies](#trading-strategies)
9. [Risk Management](#risk-management)
10. [API Endpoints](#api-endpoints)
11. [Monitoring](#monitoring)
12. [Development](#development)

---

## What It Does

### Core Functionality

**Consolidation** bridges your Discord community alerts with your brokerage account:

1. **Listens to Discord** - Monitors specified channels for trade alerts in any format
2. **Parses Alerts** - Extracts ticker, strike, expiration, call/put, and action (BTO/STC/etc)
3. **Validates Trades** - Runs risk checks before execution
4. **Executes Orders** - Places trades through your broker's API
5. **Manages Positions** - Sets profit targets, stop losses, trailing stops
6. **Tracks P&L** - Monitors performance and provides analytics

### Supported Trade Types

| Alert Type | Description |
|------------|-------------|
| **BTO** | Buy to Open - Enter long position |
| **STC** | Sell to Close - Exit long position |
| **BTC** | Buy to Close - Exit short position |
| **STO** | Sell to Open - Enter short position |

### Supported Order Types

- **Market Orders** - Immediate execution at best price
- **Limit Orders** - Execute at specified price or better
- **Stop Orders** - Trigger at specified price
- **Bracket Orders** - Entry + profit target + stop loss
- **Trailing Stops** - Dynamic stop that follows price

---

## How It Works

### High-Level Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Discord Alert  │────▶│  Parse & Validate│────▶│  Risk Checks    │
│  (Analyst msg)  │     │  (Extract fields)│     │  (Duplicate,    │
└─────────────────┘     └──────────────────┘     │   correlation)  │
                                                   └────────┬────────┘
                                                            │
                          ┌──────────────────┐              │
                          │  Place Order     │◀─────────────┘
                          │  (Broker API)    │
                          └────────┬─────────┘
                                   │
                          ┌────────▼─────────┐
                          │  Monitor Position│
                          │  (PT/SL/Trailing)│
                          └──────────────────┘
```

### Alert Parsing Pipeline

The bot uses a flexible parsing system that handles **32+ analyst formats**:

```python
# Example: Analyst sends "BTO AAPL 150C May 17 2024"
# Bot extracts:
{
    "ticker": "AAPL",
    "strike": 150,
    "option_type": "CALL",
    "expiration": "2024-05-17",
    "alert_type": "BTO",
    "quantity": 5
}
```

**Supported Formats Include:**
- Default, Enhanced Market, Vader, SwingTrader, ThetaGang
- Momentum, Mean Reversion, Breakout, RSI, MACD
- Iron Condor, Straddle, Strangle, Butterfly
- Grid, DCA, Scalp, Swing, Trend
- Chinese, Korean, and more...

### Risk Validation

Before any trade executes:

1. **Duplicate Check** - Same alert within 60 seconds is blocked
2. **Correlation Check** - Max positions per ticker (default: 3)
3. **Position Size Check** - Won't exceed max position size
4. **Daily Loss Check** - Stops trading if daily loss exceeds threshold
5. **Drawdown Check** - Halts trading if portfolio drawdown exceeds limit

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React/Expo)                    │
│  ┌─────────┐ ┌────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐ │
│  │Dashboard│ │ Alerts │ │ Positions│ │ Trades │ │ Settings  │ │
│  └────┬────┘ └───┬────┘ └────┬─────┘ └───┬────┘ └─────┬─────┘ │
└───────┼─────────┼──────────┼───────────┼────────────┼────────┘
        │         │          │           │            │
        └─────────┴──────────┴───────────┴────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Nginx Proxy     │
                    │   (Rate Limiting) │
                    └─────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼───────┐   ┌────────▼────────┐   ┌────────▼────────┐
│  FastAPI      │   │  Sentinel Edge  │   │  Discord Bot    │
│  Backend      │   │  (Confidence)   │   │  (Alert Intake) │
└───────┬───────┘   └─────────────────┘   └─────────────────┘
        │
┌───────┼───────────────────────────────────────────────────────┐
│       │                    Data Layer                          │
│  ┌────▼────┐   ┌─────────┐   ┌──────────┐   ┌────────────┐  │
│  │ MongoDB │◀─▶│  Redis  │◀─▶│ SQLite   │◀─▶│  Brokers   │  │
│  │(Primary)│   │(Cache)  │   │(Backup)  │   │(IBKR, etc) │  │
│  └─────────┘   └─────────┘   └──────────┘   └────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

### Component Descriptions

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | React Native/Expo | Web dashboard for monitoring and control |
| **Backend** | Python FastAPI | REST API, business logic, order management |
| **Discord Bot** | discord.py | Listen to alerts, send notifications |
| **Database** | MongoDB | Primary data store (positions, trades, settings) |
| **Cache** | Redis | Session cache, rate limiting |
| **Backup DB** | SQLite | Local fallback storage |
| **Sentinel Edge** | Python | Market confidence analysis |
| **Proxy** | Nginx | Rate limiting, SSL termination |

---

## Features

### Trading Features

- **Multiple Broker Support** - IBKR, Alpaca, TD Ameritrade, and more
- **Options Chain Integration** - Automatic strike selection (ATM, OTM, ITM, Delta, Risk/Reward)
- **Multi-leg Strategies** - Spreads, straddles, strangles, iron condors
- **Grid Trading** - Automated buy-low/sell-high in price range
- **DCA (Dollar Cost Averaging)** - Average down with configurable steps
- **Paper Trading** - Test strategies without real money

### Analyst Alert Formats

The bot parses **32 different formats** including:

- **Directional**: Bullish, Bearish, Long, Short
- **Strategy-specific**: Momentum, Mean Reversion, Breakout, Gap Fill
- **Options**: Calls, Puts, Spreads, Iron Condors
- **Regional**: English, Chinese (中文), Korean (한국어)

### Position Management

- **Profit Targets** - Exit when X% profit reached
- **Stop Losses** - Limit downside with automatic exits
- **Trailing Stops** - Lock in profits as price moves
- **Partial Exits** - Take profit on portion of position
- **Rollovers** - Roll expiring positions to next expiration

### Risk Controls

- **Duplicate Detection** - Block repeated alerts
- **Correlation Limits** - Max positions per ticker
- **Position Sizing** - Kelly Criterion-based sizing
- **Sector Exposure** - Limit exposure by sector
- **Daily Loss Limits** - Auto-halt after X% loss
- **Drawdown Protection** - Pause trading after X% drawdown

---

## Supported Brokers

| Broker | Status | Features |
|--------|--------|----------|
| **Interactive Brokers** | ✅ | Stocks, Options, Futures, Forex, Crypto |
| **Alpaca** | ✅ | Stocks, Options, Crypto |
| **TD Ameritrade** | ✅ | Stocks, Options |
| **Tradier** | ✅ | Stocks, Options |
| **TradeStation** | ✅ | Stocks, Options, Futures |
| **ThinkOrSwim** | ✅ | Stocks, Options, Futures |
| **eTrade** | ✅ | Stocks, Options |
| **Webull** | ✅ | Stocks, Options |
| **Fidelity** | ✅ | Stocks, Options |
| **Charles Schwab** | ✅ | Stocks, Options |
| **Binance** | ✅ | Spot, Futures, Options |
| **Coinbase** | ✅ | Spot, Futures |
| **Kraken** | ✅ | Spot, Futures |
| **Bybit** | ✅ | Spot, Futures, Options |
| **Hyperliquid** | ✅ | Spot, Futures |
| **Polymarket** | ✅ | Prediction Markets |
| **Degiro** | ✅ | EU Stocks, Options |
| **OANDA** | ✅ | Forex |
| **Wealthsimple** | ✅ | Canadian Stocks |

---

## Installation

### Option 1: Windows Installer (Recommended)

1. Download `TradeBot-Setup-1.0.0.exe` from releases
2. Run as Administrator
3. Follow installation wizard
4. Edit configuration file
5. Launch from desktop shortcut

### Option 2: Docker Compose

```bash
# Clone the repository
git clone https://github.com/Tetradim/Consolidation.git
cd Consolidation

# Copy environment file
cp .env.example .env

# Edit configuration
# (See Configuration section below)

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Option 3: Manual Installation

```bash
# Prerequisites
# - Python 3.11+
# - MongoDB
# - Redis

# Clone and setup
git clone https://github.com/Tetradim/Consolidation.git
cd Consolidation

# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env
python -m backend

# Frontend (separate terminal)
cd ../frontend
npm install
npx expo start
```

---

## Configuration

### Environment Variables

Create a `.env` file with these settings:

```env
# ===================
# Discord (Required)
# ===================
DISCORD_BOT_TOKEN=your-bot-token
DISCORD_CHANNEL_IDS=123456789,987654321
DISCORD_GUILD_ID=123456789

# ===================
# Database
# ===================
MONGO_URL=mongodb://localhost:27017
MONGO_USER=tradebot
MONGO_PASSWORD=your-secure-password
DB_NAME=tradebot

# ===================
# Redis
# ===================
REDIS_URL=redis://localhost:6379

# ===================
# Broker (Choose one or more)
# ===================
# Interactive Brokers
IBKR_GATEWAY_URL=https://localhost:5000
IBKR_ACCOUNT_ID=DU123456

# Alpaca
ALPACA_API_KEY=your-key
ALPACA_API_SECRET=your-secret
ALPACA_PAPER=true

# ===================
# Security
# ===================
SECRET_KEY=random-32-character-string

# ===================
# Trading
# ===================
SIMULATION_MODE=true
DEFAULT_QUANTITY=5
MAX_POSITION_SIZE=1000
```

### Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create new application
3. Add Bot user
4. Enable Message Content Intent
5. Copy Bot Token
6. Invite bot to server with appropriate permissions

### Broker Setup

**Interactive Brokers:**
1. Install IB Gateway
2. Configure API access (port 5000)
3. Note your account ID

**Alpaca:**
1. Create account at alpaca.markets
2. Generate API keys
3. Enable paper trading for testing

---

## Trading Strategies

### Built-in Strategies

| Strategy | Description |
|----------|-------------|
| **Mean Reversion** | Buy oversold, sell overbought |
| **Momentum** | Trade in direction of strong trends |
| **Breakout** | Enter on price breakouts |
| **RSI** | Trade based on RSI overbought/oversold |
| **MACD** | Use MACD crossovers |
| **Bollinger Bands** | Trade mean reversion with bands |

### Options Strike Selection

When selecting strikes, choose from:

| Method | Description |
|--------|-------------|
| **ATM** | At-the-money (strike = current price) |
| **OTM** | Out-of-the-money (directional bet) |
| **ITM** | In-the-money (more conservative) |
| **Delta** | Target specific delta (0.3, 0.5, 0.7) |
| **Risk/Reward** | Fixed risk/reward ratio |
| **High IV** | Highest implied volatility |
| **Liquidity** | Most liquid strikes |

---

## Risk Management

### Position Sizing

The bot uses Kelly Criterion-inspired sizing:

```
position_size = min(
    max_capital / entry_price,    # Capital limit
    risk_amount / stop_loss       # Risk-based limit
)
```

### Risk Checks Order

1. **Duplicate Alert** → Block if within 60 seconds
2. **Max Positions** → Block if exceeds limit per ticker
3. **Position Size** → Reduce if exceeds max
4. **Sector Exposure** → Block if sector overweight
5. **Daily Loss** → Halt if exceeded
6. **Drawdown** → Pause if max drawdown reached

---

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/positions` | List open positions |
| GET | `/trades` | Trade history |
| GET | `/alerts` | Alert history |
| POST | `/alerts/check` | Check alert confidence |
| GET | `/settings` | Get settings |
| PUT | `/settings` | Update settings |

### Broker Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/brokers` | List configured brokers |
| POST | `/brokers/{id}/connect` | Connect broker |
| POST | `/brokers/{id}/order` | Place order |
| DELETE | `/brokers/{id}/order/{id}` | Cancel order |

### Monitoring

| Endpoint | Description |
|----------|-------------|
| `/metrics` | Prometheus metrics |
| `/logs` | Application logs |

---

## Monitoring

### Grafana Dashboards

Access at `http://localhost:3030`:

- **Trading Overview** - P&L, win rate, drawdown
- **Position Analytics** - Open positions, Greeks
- **System Health** - API latency, error rates
- **Broker Performance** - Order fill times

### Prometheus Metrics

Key metrics tracked:
- `tradebot_orders_total` - Total orders placed
- `tradebot_positions_active` - Open positions
- `tradebot_pnl_total` - Cumulative P&L
- `tradebot_alerts_processed` - Alerts processed
- `tradebot_risk_blocked` - Risk check failures

---

## Development

### Project Structure

```
Consolidation/
├── backend/
│   ├── __main__.py          # Entry point
│   ├── server.py            # FastAPI server
│   ├── routes/              # API routes
│   ├── brokers/             # Broker adapters
│   ├── unified_risk.py      # Risk management
│   ├── analyst_formats.py   # Alert parsers
│   ├── options_chain.py     # Strike selection
│   ├── grid_dca.py          # Trading strategies
│   └── discord_config.py    # Discord integration
├── frontend/
│   ├── app/                 # Expo screens
│   ├── components/          # React components
│   └── utils/               # Frontend utilities
├── nginx/                   # Nginx configs
├── prometheus/              # Monitoring configs
├── docker-compose.yml       # Full stack
└── installer/               # Windows installer
```

### Running Tests

```bash
cd backend
pytest tests/ -v --cov=. --cov-report=html
```

### Adding New Broker

1. Create adapter in `backend/brokers/`
2. Inherit from `BrokerAdapter` base class
3. Implement required methods
4. Register in `broker_registry.py`

---

## License

MIT License - See LICENSE file for details.

---

## Support

- Issues: [GitHub Issues](https://github.com/Tetradim/Consolidation/issues)
- Discussions: [GitHub Discussions](https://github.com/Tetradim/Consolidation/discussions)

---

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Python web framework
- [MongoDB](https://www.mongodb.com/) - Database
- [Redis](https://redis.io/) - Caching
- [Discord.py](https://discordpy.readthedocs.io/) - Discord API
- [Expo](https://expo.dev/) - React Native framework
- [NautilusTrader](https://nautilustrader.io/) - Architecture inspiration
- [OctoBot](https://www.octobot.cloud/) - Strategy inspiration