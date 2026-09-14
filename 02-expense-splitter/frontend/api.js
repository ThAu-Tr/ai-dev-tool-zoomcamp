// Centralized HTTP client for the GrabTab backend. Keep UI code dependent on
// this module only, so authentication and endpoint changes remain localized.
const API_BASE_URL = (window.GRABTAB_API_BASE_URL || localStorage.getItem('grabtabApiBaseUrl') || 'http://localhost:8000').replace(/\/$/, '');
const ACCESS_TOKEN = localStorage.getItem('grabtabAccessToken') || 'mock-anna';

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        Authorization: `Bearer ${ACCESS_TOKEN}`,
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new Error('Unable to reach GrabTab API. Start the backend on port 8000.');
  }

  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.message || 'The request could not be completed');
  return body;
}

export const api = {
  getState: () => request('/v1/household/state'),
  reset: () => request('/v1/dev/reset-demo-data', { method: 'POST' }),
  addShoppingItem: (name) => request('/v1/shopping-items', { method: 'POST', body: JSON.stringify({ name }) }),
  buyShoppingItem: ({ itemId, amount }) => request(`/v1/shopping-items/${encodeURIComponent(itemId)}/purchase`, { method: 'POST', body: JSON.stringify({ amount: Number(amount) }) }),
  addExpense: ({ name, amount, participants }) => request('/v1/expenses', { method: 'POST', body: JSON.stringify({ name, amount: Number(amount), participantIds: participants }) }),
  updateExpense: (expenseId, { name, amount, participants }) => request(`/v1/expenses/${encodeURIComponent(expenseId)}`, { method: 'PATCH', body: JSON.stringify({ name, amount: Number(amount), participantIds: participants }) }),
  deleteExpense: (expenseId) => request(`/v1/expenses/${encodeURIComponent(expenseId)}`, { method: 'DELETE' }),
  settleDebt: ({ from, to }) => request('/v1/debt-settlements', { method: 'POST', body: JSON.stringify({ fromMemberId: from, toMemberId: to }) }),
};
