import { useEffect, useRef, useState } from 'react';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, Legend,
} from 'recharts';

const BASE_URL = 'http://localhost:8000';
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

interface ChartPoint {
    date: string;
    sp500: number;
    nasdaq: number;
    dow: number;
}

export function MarketChart() {
    const [data, setData]       = useState<ChartPoint[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError]     = useState(false);
    const cachedAt              = useRef<number>(0);
    const cachedData            = useRef<ChartPoint[]>([]);

    useEffect(() => {
        let cancelled = false;

        async function load() {
            // Serve from in-memory cache if still fresh
            if (Date.now() - cachedAt.current < CACHE_TTL_MS && cachedData.current.length > 0) {
                setData(cachedData.current);
                setLoading(false);
                return;
            }
            try {
                const res = await fetch(`${BASE_URL}/market/chart`);
                if (!res.ok) throw new Error(`${res.status}`);
                const json: ChartPoint[] = await res.json();
                if (!cancelled) {
                    cachedData.current = json;
                    cachedAt.current   = Date.now();
                    setData(json);
                    setError(false);
                }
            } catch {
                if (!cancelled) setError(true);
            } finally {
                if (!cancelled) setLoading(false);
            }
        }

        load();
        return () => { cancelled = true; };
    }, []);

    return (
        <div className="chart-card">
            <div className="chart-header">
                <h3>Market Trends</h3>
                <span className="chart-badge" style={error ? { color: '#ef4444' } : {}}>
                    {loading ? '…' : error ? 'Offline' : '12M Live'}
                </span>
            </div>

            {loading ? (
                <div className="chart-skeleton" style={{ height: 200 }} />
            ) : (
                <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e2a3a" />
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6b7280' }} />
                        <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} />
                        <Tooltip
                            contentStyle={{ background: '#111827', border: '1px solid #1e2a3a', borderRadius: 8 }}
                            labelStyle={{ color: '#9ca3af' }}
                            itemStyle={{ color: '#e5e7eb' }}
                            formatter={(v: number | undefined) => [`$${(v ?? 0).toFixed(0)}`, '']}
                        />
                        <Legend wrapperStyle={{ fontSize: 11 }} />
                        <Line type="monotone" dataKey="sp500"  stroke="#14b8a6" strokeWidth={2} dot={false} name="S&P 500" />
                        <Line type="monotone" dataKey="nasdaq" stroke="#8b5cf6" strokeWidth={2} dot={false} name="NASDAQ" />
                        <Line type="monotone" dataKey="dow"    stroke="#3b82f6" strokeWidth={1.5} dot={false} name="DOW" />
                    </LineChart>
                </ResponsiveContainer>
            )}
        </div>
    );
}

