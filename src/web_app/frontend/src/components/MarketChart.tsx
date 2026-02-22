import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, Legend,
} from 'recharts';
import { MARKET_DATA } from '../lib/mockData';

export function MarketChart() {
    return (
        <div className="chart-card">
            <div className="chart-header">
                <h3>Market Trends</h3>
                <span className="chart-badge">12M</span>
            </div>
            <ResponsiveContainer width="100%" height={200}>
                <LineChart data={MARKET_DATA} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e2a3a" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6b7280' }} />
                    <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} />
                    <Tooltip
                        contentStyle={{ background: '#111827', border: '1px solid #1e2a3a', borderRadius: 8 }}
                        labelStyle={{ color: '#9ca3af' }}
                        itemStyle={{ color: '#e5e7eb' }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Line type="monotone" dataKey="sp500" stroke="#14b8a6" strokeWidth={2} dot={false} name="S&P 500" />
                    <Line type="monotone" dataKey="nasdaq" stroke="#8b5cf6" strokeWidth={2} dot={false} name="NASDAQ" />
                    <Line type="monotone" dataKey="dow" stroke="#3b82f6" strokeWidth={1.5} dot={false} name="DOW" />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}
