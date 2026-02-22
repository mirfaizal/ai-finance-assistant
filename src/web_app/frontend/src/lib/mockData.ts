import type { MarketDataPoint, PortfolioSegment } from './types';

export const MARKET_DATA: MarketDataPoint[] = [
  { date: 'Jan', sp500: 4700, nasdaq: 14800, dow: 37200 },
  { date: 'Feb', sp500: 4850, nasdaq: 15300, dow: 38100 },
  { date: 'Mar', sp500: 4620, nasdaq: 14500, dow: 36800 },
  { date: 'Apr', sp500: 4900, nasdaq: 15700, dow: 38600 },
  { date: 'May', sp500: 5100, nasdaq: 16200, dow: 39400 },
  { date: 'Jun', sp500: 5250, nasdaq: 16900, dow: 40100 },
  { date: 'Jul', sp500: 5400, nasdaq: 17100, dow: 40600 },
  { date: 'Aug', sp500: 5200, nasdaq: 16400, dow: 39800 },
  { date: 'Sep', sp500: 5350, nasdaq: 16800, dow: 40300 },
  { date: 'Oct', sp500: 5500, nasdaq: 17400, dow: 41000 },
  { date: 'Nov', sp500: 5650, nasdaq: 17900, dow: 41700 },
  { date: 'Dec', sp500: 5820, nasdaq: 18300, dow: 42400 },
];

export const PORTFOLIO_DATA: PortfolioSegment[] = [
  { name: 'US Stocks', value: 45, color: '#14b8a6' },
  { name: 'Int\'l Stocks', value: 20, color: '#8b5cf6' },
  { name: 'Bonds', value: 20, color: '#3b82f6' },
  { name: 'Real Estate', value: 10, color: '#f59e0b' },
  { name: 'Cash', value: 5, color: '#6b7280' },
];

export const QUICK_INSIGHTS = [
  {
    id: 1,
    icon: '📈',
    title: 'Market Up +1.2%',
    desc: 'S&P 500 gained ground after strong earnings reports.',
    badge: 'Markets',
    badgeColor: '#8b5cf6',
  },
  {
    id: 2,
    icon: '🏦',
    title: 'Fed Rate Decision',
    desc: 'Federal Reserve holds rates steady for Q1 2026.',
    badge: 'Economy',
    badgeColor: '#14b8a6',
  },
  {
    id: 3,
    icon: '💡',
    title: 'Tax Tip',
    desc: 'Max out your HSA contribution before April 15.',
    badge: 'Tax',
    badgeColor: '#f59e0b',
  },
];

export const QUICK_ACTIONS = [
  { id: 'portfolio', label: 'Review Portfolio', icon: '📊' },
  { id: 'taxes', label: 'Tax Questions', icon: '🧾' },
  { id: 'budget', label: 'Budget Help', icon: '💰' },
  { id: 'retire', label: 'Retirement Plan', icon: '🎯' },
];

export const EDUCATIONAL_CARDS = [
  { title: 'What is Dollar-Cost Averaging?', category: 'Investing Basics', readTime: '3 min' },
  { title: 'Understanding the 50/30/20 Rule', category: 'Budgeting', readTime: '4 min' },
  { title: 'Roth vs Traditional IRA Explained', category: 'Retirement', readTime: '5 min' },
];
