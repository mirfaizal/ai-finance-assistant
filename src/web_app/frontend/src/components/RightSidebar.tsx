import { MarketChart } from './MarketChart';
import { PortfolioChart } from './PortfolioChart';
import { TrendingUp, TrendingDown } from 'lucide-react';

const TICKERS = [
    { symbol: 'SPY', price: '582.14', change: '+1.2%', up: true },
    { symbol: 'AAPL', price: '237.52', change: '+0.8%', up: true },
    { symbol: 'TSLA', price: '312.19', change: '-1.4%', up: false },
    { symbol: 'BTC', price: '94,210', change: '+2.1%', up: true },
    { symbol: 'NVDA', price: '875.60', change: '+3.2%', up: true },
];

export function RightSidebar() {
    return (
        <aside className="right-sidebar">
            {/* Ticker strip */}
            <div className="ticker-strip">
                {TICKERS.map((t) => (
                    <div key={t.symbol} className="ticker-item">
                        <span className="ticker-symbol">{t.symbol}</span>
                        <span className="ticker-price">{t.price}</span>
                        <span className={`ticker-change ${t.up ? 'up' : 'down'}`}>
                            {t.up ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                            {t.change}
                        </span>
                    </div>
                ))}
            </div>

            <MarketChart />
            <PortfolioChart />
        </aside>
    );
}
