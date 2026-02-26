import { useEffect, useState, useCallback } from 'react';
import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { Edit2 } from 'lucide-react';
import { getHoldings, saveHoldings, type Holding } from '../lib/holdingsStore';
import { PortfolioInput } from './PortfolioInput';
import { usePortfolioSummary } from '../lib/hooks/usePortfolioSummary';

import { BASE_URL } from '../lib/config';
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
    const [summary, setSummary] = useState<Summary | null>(null);
    const [loading, setLoading] = useState(false);
    const [showEdit, setShowEdit] = useState(false);

    // Use shared portfolio summary to drive pie and summary (keeps UI in sync)
    const { data: sharedData } = usePortfolioSummary();
    const syncFromSQLite = useCallback(async () => {
        const data = sharedData as any;
        if (!data) return;
        const sqliteHoldings: Holding[] = (data.holdings ?? []).map(
            (h: { ticker: string; shares?: number; avg_cost?: number }) => ({
                ticker: h.ticker,
                shares: h.shares ?? 0,
                avg_cost: h.avg_cost ?? 0,
            }),
        );
        if (sqliteHoldings.length > 0) {
            const local = getHoldings();
            const sqliteTickers = new Set(sqliteHoldings.map((h) => h.ticker));
            const localOnly = local.filter((h) => !sqliteTickers.has(h.ticker));
            const merged = [...sqliteHoldings, ...localOnly];
            saveHoldings(merged);
            setHoldings(merged);
            const segs: PieSegment[] = (data.holdings ?? []).map(
                (h: { ticker: string; allocation_pct: number }, i: number) => ({
                    name: h.ticker,
                    value: h.allocation_pct,
                    color: PIE_COLORS[i % PIE_COLORS.length],
                }),
            );
            setSegments(segs);
            setSummary(data.summary ?? null);
        }
    }, [sharedData]);

    // Re-read localStorage / re-sync whenever the trading agent saves
    useEffect(() => {
        syncFromSQLite();
        const onUpdate = () => {
            setHoldings(getHoldings());
            syncFromSQLite();
        };
        window.addEventListener('portfolioUpdated', onUpdate);
        return () => window.removeEventListener('portfolioUpdated', onUpdate);
    }, [syncFromSQLite]);

    const analyse = useCallback(async (hs: Holding[]) => {
        if (hs.length === 0) { setSegments([]); setSummary(null); return; }
        setLoading(true);
        try {
            const res = await fetch(`${BASE_URL}/portfolio/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ holdings: hs }),
            });
            if (!res.ok) throw new Error(`${res.status}`);
            const data = await res.json();
            const segs: PieSegment[] = (data.holdings ?? []).map(
                (h: { ticker: string; allocation_pct: number }, i: number) => ({
                    name: h.ticker,
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

    // Re-analyse localStorage holdings only when SQLite sync found nothing
    useEffect(() => {
        if (segments.length === 0) { analyse(holdings); }
    }, [holdings, analyse, segments.length]);

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
                            formatter={(v: number | undefined) => [`${(v ?? 0).toFixed(1)}%`, '']}
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

