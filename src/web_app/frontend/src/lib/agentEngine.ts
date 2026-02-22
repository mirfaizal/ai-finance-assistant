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
};

// ── Keyword maps (order determines priority) ──────────────────────────────────

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

export function detectAgent(message: string): AgentType {
  const q = message.toLowerCase();

  // Order mirrors backend router.py — most-specific first
  if (PORTFOLIO_KEYWORDS.some((kw) => q.includes(kw))) return 'portfolio';
  if (NEWS_KEYWORDS.some((kw) => q.includes(kw)))       return 'news';      // before analyst
  if (ANALYST_KEYWORDS.some((kw) => q.includes(kw)))    return 'analyst';
  if (TAX_KEYWORDS.some((kw) => q.includes(kw)))        return 'tax_pro';
  if (PLANNER_KEYWORDS.some((kw) => q.includes(kw)))    return 'planner';
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
  };
  return map[backendName] ?? 'advisor';
}

export function getAgent(type: AgentType): Agent {
  return AGENTS[type];
}
