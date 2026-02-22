import { useState } from 'react';
import { Plus, Trash2, CheckCircle } from 'lucide-react';
import { addHolding, removeHolding, type Holding } from '../lib/holdingsStore';

interface PortfolioInputProps {
  holdings: Holding[];
  onHoldingsChange: (holdings: Holding[]) => void;
}

export function PortfolioInput({ holdings, onHoldingsChange }: PortfolioInputProps) {
  const [ticker, setTicker]   = useState('');
  const [shares, setShares]   = useState('');
  const [cost,   setCost]     = useState('');
  const [error,  setError]    = useState<string | null>(null);

  const handleAdd = () => {
    const t = ticker.trim().toUpperCase();
    const s = parseFloat(shares);
    const c = parseFloat(cost);

    if (!t)         return setError('Enter a ticker symbol (e.g. AAPL)');
    if (isNaN(s) || s <= 0) return setError('Shares must be a positive number');
    if (isNaN(c) || c <= 0) return setError('Avg cost must be a positive number');

    setError(null);
    addHolding({ ticker: t, shares: s, avg_cost: c });
    onHoldingsChange([...holdings]);   // trigger parent re-fetch via key change
    setTicker(''); setShares(''); setCost('');
  };

  const handleRemove = (t: string) => {
    removeHolding(t);
    onHoldingsChange(holdings.filter((h) => h.ticker !== t));
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleAdd();
  };

  return (
    <div className="portfolio-input-panel">
      <p className="pi-hint">Add your positions to see live P&amp;L</p>

      {/* Input row */}
      <div className="pi-row">
        <input
          className="pi-field pi-ticker"
          placeholder="AAPL"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          onKeyDown={handleKey}
          maxLength={6}
        />
        <input
          className="pi-field pi-shares"
          placeholder="Shares"
          type="number"
          min="0"
          step="any"
          value={shares}
          onChange={(e) => setShares(e.target.value)}
          onKeyDown={handleKey}
        />
        <input
          className="pi-field pi-cost"
          placeholder="Avg cost $"
          type="number"
          min="0"
          step="any"
          value={cost}
          onChange={(e) => setCost(e.target.value)}
          onKeyDown={handleKey}
        />
        <button className="pi-add-btn" onClick={handleAdd} title="Add position">
          <Plus size={14} />
        </button>
      </div>

      {error && <p className="pi-error">{error}</p>}

      {/* Existing holdings list */}
      {holdings.length > 0 && (
        <ul className="pi-holdings-list">
          {holdings.map((h) => (
            <li key={h.ticker} className="pi-holding-item">
              <CheckCircle size={12} style={{ color: '#14b8a6' }} />
              <span className="pi-holding-ticker">{h.ticker}</span>
              <span className="pi-holding-meta">
                {h.shares} sh @ ${h.avg_cost.toFixed(2)}
              </span>
              <button
                className="pi-remove-btn"
                onClick={() => handleRemove(h.ticker)}
                title={`Remove ${h.ticker}`}
              >
                <Trash2 size={11} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
