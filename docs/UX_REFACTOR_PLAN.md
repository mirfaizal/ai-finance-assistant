# FinAI UX Refactoring Plan

## Current state
- **Views**: Two only — Dashboard and Chat, toggled by local state.
- **Nav**: Sidebar shows "Dashboard" and "Chat"; no Markets, Learning, or Portfolio.
- **Brand**: "Finnie AI" in sidebar; target is **FinAI**.
- **Dashboard**: Hero ("Good morning"), "Today's Insights", "Quick Actions", "Learn & Grow".
- **Right sidebar**: Ticker strip (SPY, AAPL, etc.) + MarketChart + PortfolioChart (pie).

## Target state (from design)

### Navigation
- **FinAI** branding.
- **Nav items**: Dashboard, Assistant, Markets, Learning, Portfolio.
- **Sign Out** at bottom of sidebar.
- URL routes: `/` (dashboard), `/assistant`, `/markets`, `/learn`, `/portfolio`.

### Dashboard
- **Welcome**: "Welcome back, User" + subtitle "Here's your financial snapshot for today."
- **Primary CTA**: "Ask Assistant" (opens chat).
- **Metric cards** (single row): Total Balance, YTD Return, Outperforming S&P 500, Est. Savings, Tax Efficiency, Risk Level, Balanced Allocation.
- **Recent Insights**: List of alerts (e.g. Tax Optimization, Portfolio Rebalancing, Dividend Received) with timestamps.
- **Quick Actions**: Rebalance, Buy/Sell, Risk Check, Deposit (with icons).
- **Recommended Learning**: Course/article cards with progress (e.g. "Understanding ETFs" 33%, "The Power of Compounding" 5 min read).

### Right sidebar (all pages)
- **Market Overview**: "Real-time data updates" — S&P 500 and NASDAQ with value + % change (green/red).
- **Portfolio Performance**: "Market Trends" — area/line chart (e.g. Mon–Sun).
- **Asset Allocation**: "Portfolio Allocation" — horizontal bar chart: Stocks, Bonds, Crypto, Cash.
- **Watchlist**: AAPL, MSFT, GOOGL, TSLA with price and daily % change.

### New pages
1. **Markets** (`/markets`): Market Analysis — S&P 500 Performance chart, Sector Allocation bar chart, Market News list.
2. **Learning** (`/learn`): Financial Academy — course cards (Investing 101, Tax Strategies, Market Mechanics, Crypto Basics) with progress; Daily Quiz CTA.
3. **Portfolio** (`/portfolio`): Portfolio Analysis — Export Report button, Allocation Breakdown (bar chart), Top Holdings (VTI, AAPL, MSFT, BND with % and $).

### Assistant (Chat)
- Keep existing ChatInterface; ensure header shows "Finley (General Advisor)" and disclaimer. Route at `/assistant`.

## Implementation order
1. Add `react-router-dom`; define routes and layout.
2. Update Sidebar: FinAI, 5 nav links + Sign Out (no-op or callback).
3. Refactor Dashboard to new layout and content.
4. Restructure RightSidebar: Market Overview, Portfolio Performance, Asset Allocation, Watchlist.
5. Add Markets, Learning, Portfolio page components.
6. Align copy and CTAs (e.g. "Ask Assistant" → open `/assistant` or start chat).

## Data / API
- Market indices and watchlist: use existing `/market/quotes` (or extend) for S&P 500, NASDAQ, AAPL, MSFT, GOOGL, TSLA.
- Dashboard metrics: mock or future API (total balance, YTD return, etc.).
- Recent insights: mock list of alerts.
- Learning: mock courses and progress.
- Portfolio allocation: reuse `/portfolio/analyze` and holdings store; add mock top holdings if needed.
