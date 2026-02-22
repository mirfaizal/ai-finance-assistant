import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { PORTFOLIO_DATA } from '../lib/mockData';

export function PortfolioChart() {
    return (
        <div className="chart-card">
            <div className="chart-header">
                <h3>Portfolio Allocation</h3>
                <span className="chart-badge">Sample</span>
            </div>
            <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                    <Pie
                        data={PORTFOLIO_DATA}
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={85}
                        paddingAngle={3}
                        dataKey="value"
                    >
                        {PORTFOLIO_DATA.map((entry) => (
                            <Cell key={entry.name} fill={entry.color} />
                        ))}
                    </Pie>
                    <Tooltip
                        contentStyle={{ background: '#111827', border: '1px solid #1e2a3a', borderRadius: 8 }}
                        formatter={(v: number | undefined) => [`${v ?? 0}%`, '']}
                        itemStyle={{ color: '#e5e7eb' }}
                    />
                    <Legend
                        formatter={(value) => <span style={{ fontSize: 11, color: '#9ca3af' }}>{value}</span>}
                    />
                </PieChart>
            </ResponsiveContainer>
        </div>
    );
}
