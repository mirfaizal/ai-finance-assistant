export type AgentType = 'advisor' | 'analyst' | 'tax_pro' | 'portfolio' | 'planner' | 'news' | 'stock' | 'trader';

export interface Agent {
  type: AgentType;
  name: string;
  title: string;
  color: string;
  accent: string;
  description: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  agent?: AgentType;
  timestamp: number;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
}

export interface UserProfile {
  isNewUser: boolean;
  riskTolerance: 'conservative' | 'moderate' | 'aggressive' | null;
  investmentGoals: string[];
  completedOnboarding: boolean;
}

export interface MarketDataPoint {
  date: string;
  sp500: number;
  nasdaq: number;
  dow: number;
}

export interface PortfolioSegment {
  name: string;
  value: number;
  color: string;
}
