# Trading Bot

A Discord-based options trading bot that listens to alerts and executes trades automatically.

## Features

- **Discord Alert Parsing** - Listens to Discord channels for trade alerts
- **Multiple Broker Support** - IBKR, Alpaca, Tradier, TD Ameritrade
- **Price Buffer** - Configurable safety margin on entry price
- **Bracket Orders** - Profit target + stop loss management
- **Trailing Stops** - Dynamic trailing stop that moves with price
- **Position Management** - Track and manage open positions
- **Risk Management** - Max positions, correlation limits, duplicate detection

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file:

```bash
cp backend/.env.example backend/.env
```

Edit `.env` with your settings:

```bash
# Discord Bot Token (required)
DISCORD_BOT_TOKEN=your-bot-token

# Channel IDs to listen on
DISCORD_CHANNEL_IDS=123456789

# Broker settings (IBKR example)
IBKR_GATEWAY_URL=https://localhost:5000
IBKR_ACCOUNT_ID=your-account-id

# Trading mode
SIMULATION_MODE=true  # Set to false for real trading
```

### 3. Run the Bot

```bash
python -m uvicorn backend.server:app --host 0.0.0.0 --port 8000
```

Or use the run script:

```bash
python backend/run.py
```

### 4. Access the API

- API: http://localhost:8000
- Docs: http://localhost:8000/docs

## Discord Alert Format

The bot listens for messages like:

```
$QQQ
$653 CALLS
EXPIRATION 4/17/2026
$.29 Entry
@everyone
```

### Supported Alert Types

**Buy Alert:**
```
$QQQ
$653 CALLS
EXPIRATION 4/17/2026
$.29 Entry
```

**Sell Alert:**
```
SELL $QQQ $653 CALLS
```

**Average Down:**
```
$QQQ
$653 CALLS
EXPIRATION 4/17/2026
$.25 AVG DOWN
```

## API Endpoints

| Endpoint | Method | Description |
|----------|-------|------------|
| `/api/health` | GET | Health check |
| `/api/settings` | GET/PUT | Bot settings |
| `/api/settings/discord` | GET/PUT | Discord settings |
| `/api/brokers` | GET/POST | Broker configs |
| `/api/trading/positions` | GET | List positions |
| `/api/trading/execute` | POST | Execute trade |
| `/api/trading/close` | POST | Close position |
| `/api/trading/stats` | GET | Trading stats |

## Configuration Options

### Price Buffer
- `USE_PRICE_BUFFER=true` - Apply buffer to entry price
- `PRICE_BUFFER_PERCENTAGE=3` - Buffer % (default 3%)

### Bracket Orders
- `ENABLE_BRACKET_ORDERS=true` - Enable profit target + stop loss
- `DEFAULT_PROFIT_TARGET=50` - Profit target %
- `DEFAULT_STOP_LOSS=30` - Stop loss %

### Trailing Stop
- `ENABLE_TRAILING_STOP=true` - Enable trailing stop
- `TRAILING_PERCENTAGE=25` - Trailing stop %

### Risk Management
- `MAX_OPEN_POSITIONS=10` - Max total positions
- `MAX_POSITIONS_PER_TICKER=3` - Max positions per ticker
- `MAX_POSITION_SIZE=1000` - Max $ per position

## Broker Setup

### Interactive Brokers
1. Download IBKR Gateway from IBKR website
2. Run Gateway app locally
3. Configure `IBKR_GATEWAY_URL=https://localhost:5000`
4. Set `IBKR_ACCOUNT_ID` to your account

### Alpaca
1. Get API keys from https://app.alpaca.markets
2. Set `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`
3. Set `ALPACA_PAPER=true` for paper trading

### Tradier
1. Create account at Tradier
2. Get API keys from developer dashboard
3. Set `TRADIER_ACCOUNT_ID` and `TRADIER_ACCESS_TOKEN`

## Security Notes

- Never commit `.env` to version control
- Keep your API keys secret
- Use paper trading for testing
- Review all trades before enabling live trading