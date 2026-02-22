import { useEffect, useState, useCallback } from 'react';
import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { Edit2 } from 'lucide-react';
import { getHoldings, type Holding } from '../lib/holdingsStore';
import { PortfolioInput } from './PortfolioInput';

const BASE_URL   = 'http://localhost:8000';
const PIE_COLORS = [
    '#14b8a6', '#8b5cf6', '#3b82f6', '#f59e0b',
    '#10b981', '#ec4899', '#f97316', '#6b7280',
];

interface PieSegment { name: string; value: number; color: string; }
interface Summary {
    total_value: number;
    total_pnl: number;
    total_pnl_pct: number;
    concentration_risk: string;
}

export function PortfolioChart() {
    const [holdings, setHoldings] = useState<Holding[]>(getHoldings);
    const [segments, setSegments] = useState<PieSegment[]>([]);
    const [summary,  setSummary]  = useState<Summary | null>(null);
    const [loading,  setLoading]  = useState(false);
    const [showEdit, setShowEdit] = useState(false);

    const analyse = useCallback(async (hs: Holding[]) => {
        if (hs.length === 0) { setSegments([]); setSummary(null); return; }
        setLoading(true);
        try {
            const res = await fetch(`${BASE_URL}/portfolio/analyze`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ holdings: hs }),
            });
            if (!res.ok) throw new Error(`${res.status}`);
            const data = await res.json();
            const segs: PieSegment[] = (data.holdings ?? []).map(
                (h: { ticker: string; allocation_pct: number }, i: number) => ({
                    name:  h.ticker,
                    value: h.allocation_pct,
                    color: PIE_COLORS[i % PIE_COLORS.length],
                }),
            );
            setSegments(segs);
            setSummary(data.summary ?? null);
        } catch {
            setSegments([]); setSummary(null);
        } finally {
            setLoading(false);
        }
    }, []);

    // Re-analyse whenever holdings change (including initial load)
    useEffect(() => { analyse(holdings); }, [holdings, analyse]);

    const handleHoldingsChange = () => {
        const fresh = getHoldings();
        setHoldings(fresh);
    };

    const pnlColor = summary
        ? summary.total_pnl >= 0 ? '#10b981' : '#ef4444'
        : '#6b7280';

    return (
        <div className="chart-card">
            <div className="chart-header">
                <h3>Portfolio Allocation</h3>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    {summary && (
                        <span style={{ fontSize: 11, color: pnlColor, fontWeight: 600 }}>
                            {summary.total_pnl >= 0 ? '+' : ''}
                            {summary.total_pnl_pct.toFixed(1)}%
                        </span>
                    )}
                    <span
                        className="chart-badge"
                        style={loading ? { opacity: 0.5 } : {}}
                    >
                        {loading ? '…' : segments.length > 0 ? 'Live' : 'Empty'}
                    </span>
                    <button
                        className="pi-icon-btn"
                        onClick={() => setShowEdit((v) => !v)}
                        title="Edit holdings"
                    >
                        <Edit2 size={12} />
                    </button>
                </div>
            </div>

            {showEdit && (
                <PortfolioInput
                    holdings={holdings}
                    onHoldingsChange={handleHoldingsChange}
                />
            )}

            {segments.length === 0 && !loading && !showEdit && (
                <div className="chart-empty-hint">
                    <p>No holdings yet.</p>
                    <button className="pi-add-link" onClick={() => setShowEdit(true)}>
                        + Add your first position
                    </button>
                </div>
            )}

            {segments.length > 0 && (
                <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                        <Pie
                            data={segments}
                            cx="50%"
                            cy="50%"
                            innerRadius={55}
                            outerRadius={85}
                            paddingAngle={3}
                            dataKey="value"
                        >
                            {segments.map((entry, i) => (
                                <Cell key={entry.name} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                            ))}
                        </Pie>
                        <Tooltip
                            contentStyle={{ background: '#111827', border: '1px solid #1e2a3a', borderRadius: 8 }}
                            formatter={(v: number) => [`${v.toFixed(1)}%`, '']}
                            itemStyle={{ color: '#e5e7eb' }}
                        />
                        <Legend
                            formatter={(value) => (
                                <span style={{ fontSize: 11, color: '#9ca3af' }}>{value}</span>
                            )}
                        />
                    </PieChart>
                </ResponsiveContainer>
            )}

            {summary && (
                <div className="portfolio-summary-row">
                    <span>Value: <strong>${summary.total_value.toLocaleString()}</strong></span>
                    <span style={{ color: pnlColor }}>
                        P&amp;L: {summary.total_pnl >= 0 ? '+' : ''}${summary.total_pnl.toFixed(0)}
                    </span>
                    <span style={{ color: summary.concentration_risk === 'high' ? '#f59e0b' : '#6b7280', fontSize: 10 }}>
                        Risk: {summary.concentration_risk}
                    </span>
                </div>
            )}
        </div>
    );
}

