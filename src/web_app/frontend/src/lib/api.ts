const BASE_URL = 'http://localhost:8000';

export interface AskResponse {
  question: string;
  answer: string;
  agent: string;
}

export async function askQuestion(question: string): Promise<AskResponse> {
  const res = await fetch(`${BASE_URL}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });

  if (!res.ok) {
    const errBody = await res.text();
    throw new Error(`Backend error ${res.status}: ${errBody}`);
  }

  return res.json() as Promise<AskResponse>;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE_URL}/health`);
    return res.ok;
  } catch {
    return false;
  }
}
