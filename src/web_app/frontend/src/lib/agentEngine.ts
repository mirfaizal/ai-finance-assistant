import type { Agent, AgentType } from './types';

export const AGENTS: Record<AgentType, Agent> = {
  advisor: {
    type: 'advisor',
    name: 'Finnie Advisor',
    title: 'Finance Q&A',
    color: '#14b8a6',
    accent: 'teal',
    description: 'General financial education and concepts',
  },
  analyst: {
    type: 'analyst',
    name: 'Finnie Analyst',
    title: 'Market Analyst',
    color: '#8b5cf6',
    accent: 'violet',
    description: 'Stock market analysis, indices, and sector dynamics',
  },
  tax_pro: {
    type: 'tax_pro',
    name: 'Finnie Tax Pro',
    title: 'Tax Educator',
    color: '#f59e0b',
    accent: 'amber',
    description: 'Tax concepts, deductions, and retirement accounts',
  },
  portfolio: {
    type: 'portfolio',
    name: 'Finnie Portfolio',
    title: 'Portfolio Analyst',
    color: '#3b82f6',
    accent: 'blue',
    description: 'Portfolio review, diversification & allocation',
  },
  planner: {
    type: 'planner',
    name: 'Finnie Planner',
    title: 'Goal Planner',
    color: '#10b981',
    accent: 'green',
    description: 'Financial goal-setting, budgeting, and savings plans',
  },
  news: {
    type: 'news',
    name: 'Finnie News',
    title: 'News Synthesizer',
    color: '#ec4899',
    accent: 'pink',
    description: 'Financial news synthesis and market context',
  },
  stock: {
    type: 'stock',
    name: 'Finnie Stock',
    title: 'Stock Analyst',
    color: '#f97316',
    accent: 'orange',
    description: 'Live stock quotes, financials, technicals and fundamentals via yfinance',
  },
  trader: {
    type: 'trader',
    name: 'Finnie Trader',
    title: 'Trading Agent',
    color: '#22d3ee',
    accent: 'cyan',
    description: 'Paper buy/sell trades and position tracking stored in SQLite',
  },
};

// ── Keyword maps (order determines priority) ──────────────────────────────────

// Individual stock / fundamentals queries — checked before generic ANALYST_KEYWORDS
const STOCK_KEYWORDS = [
  // live price signals
  'stock price', 'trading at', 'quote', 'share price', 'current price',
  // fundamentals
  'pe ratio', 'p/e', 'eps', 'earnings per share', 'price to earnings',
  'revenue', 'margins', 'debt to equity', 'roe', 'analyst target',
  'analyst rating', 'analyst recommendation', 'buy rating', 'sell rating',
  // history / technicals
  '52-week', '52 week', 'all time high', 'year to date', 'ytd return',
  'stock history', 'stock chart', 'candlestick',
  // explicit ticker patterns (3–5 upper-case letters) handled via regex in detectAgent
];

const PORTFOLIO_KEYWORDS = [
  'portfolio', 'holdings', 'allocation', 'diversif', 'rebalance',
  'my stocks', 'my investments', 'asset mix', 'concentration',
  'review my', 'analyse my', 'analyze my', 'my assets', 'my holdings',
  'overweight', 'underweight', 'weighting',
];

const NEWS_KEYWORDS = [
  'news', 'article', 'headline', 'announcement', 'press release',
  'latest', 'breaking', 'what happened', 'summarize', 'synthesize',
  'earnings report',
];

const TAX_KEYWORDS = [
  'tax', 'irs', 'deduction', 'filing', 'w-2', '1099', 'refund',
  'withholding', 'roth', 'ira', '401k', 'traditional ira', 'tax bracket',
  'capital gains tax', 'depreciation', 'write off', 'audit',
  'tax return', 'tax credit', 'estate tax',
];

const ANALYST_KEYWORDS = [
  'market', 'stock', 'price', 'chart', 'ticker', 'aapl', 'tsla', 'spy',
  'nasdaq', 'dow', 's&p', 'etf', 'index', 'options', 'earnings', 'pe ratio',
  'technical', 'bullish', 'bearish', 'volatility', 'shares', 'equity',
  'crypto', 'bitcoin', 'sector', 'market trend', 'market analysis',
];

const PLANNER_KEYWORDS = [
  'goal', 'plan', 'budget', 'retire', 'retirement', 'emergency fund',
  'save', 'saving', 'debt', 'mortgage', 'college', 'wealth', 'target',
  'timeline', 'financial plan', 'how much should i', 'financial goal',
];

const TRADING_KEYWORDS = [
  'buy', 'sell', 'trade', 'paper trade', 'paper trading',
  'position', 'positions', 'my position', 'my trade', 'my trades',
  'execute', 'place order', 'order', 'shares of',
  'p&l', 'profit and loss', 'unrealized', 'realized gain',
];

// Matches lone ticker symbols like AAPL, NVDA, TSLA (2-5 upper-case letters surrounded by word boundaries)
const TICKER_RE = /\b[A-Z]{2,5}\b/;

export function detectAgent(message: string): AgentType {
  const q = message.toLowerCase();

  // Order mirrors backend router.py — most-specific first
  if (TRADING_KEYWORDS.some((kw) => q.includes(kw)))      return 'trader';
  if (PORTFOLIO_KEYWORDS.some((kw) => q.includes(kw)))    return 'portfolio';
  if (NEWS_KEYWORDS.some((kw) => q.includes(kw)))         return 'news';
  // Stock-specific fundamentals / live price queries
  if (STOCK_KEYWORDS.some((kw) => q.includes(kw)))        return 'stock';
  // Raw ticker symbol with a price/action verb nearby
  if (TICKER_RE.test(message) && /price|trading|worth|hold|overvalued|undervalued|target|forecast|up|down/.test(q)) return 'stock';
  if (ANALYST_KEYWORDS.some((kw) => q.includes(kw)))      return 'analyst';
  if (TAX_KEYWORDS.some((kw) => q.includes(kw)))          return 'tax_pro';
  if (PLANNER_KEYWORDS.some((kw) => q.includes(kw)))      return 'planner';
  return 'advisor';
}

/** Map a backend agent string to our frontend AgentType. */
export function backendAgentToType(backendName: string): AgentType {
  const map: Record<string, AgentType> = {
    finance_qa_agent:         'advisor',
    portfolio_analysis_agent: 'portfolio',
    market_analysis_agent:    'analyst',
    tax_education_agent:      'tax_pro',
    goal_planning_agent:      'planner',
    news_synthesizer_agent:   'news',
    stock_agent:              'stock',
    trading_agent:            'trader',
  };
  return map[backendName] ?? 'advisor';
}

export function getAgent(type: AgentType): Agent {
  return AGENTS[type];
}
