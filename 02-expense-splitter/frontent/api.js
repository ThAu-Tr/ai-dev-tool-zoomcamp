// The app should import data functions only from this file. Replace these mock
// functions with fetch calls when the backend is ready.
const KEY = 'grabtab-demo-v1';

const initialData = {
  currentUserId: 'anna',
  household: { name: 'Elm Street Home', inviteCode: 'ELM-782', inviteLink: 'grabtab.app/join/elm-782' },
  members: [
    { id: 'anna', name: 'Anna', color: 'anna' },
    { id: 'ben', name: 'Ben', color: 'ben' },
    { id: 'clara', name: 'Clara', color: 'clara' },
  ],
  shopping: [
    { id: 's1', name: 'Oat milk', addedBy: 'clara' },
    { id: 's2', name: 'Toilet paper', addedBy: 'anna' },
    { id: 's3', name: 'Dishwasher tabs', addedBy: 'ben' },
  ],
  expenses: [
    { id: 'e1', name: 'Internet', amount: 42, paidBy: 'anna', participants: ['anna', 'ben', 'clara'], createdAt: '2026-09-05', source: 'direct' },
    { id: 'e2', name: 'Fresh produce', amount: 28.4, paidBy: 'ben', participants: ['anna', 'ben', 'clara'], createdAt: '2026-09-08', source: 'shopping' },
    { id: 'e3', name: 'Cleaning supplies', amount: 12, paidBy: 'clara', participants: ['anna', 'clara'], createdAt: '2026-09-09', source: 'direct' },
  ],
  settlements: [],
};

const wait = (value) => new Promise((resolve) => setTimeout(() => resolve(value), 100));
const clone = (value) => JSON.parse(JSON.stringify(value));
function data() { const saved = localStorage.getItem(KEY); return saved ? JSON.parse(saved) : clone(initialData); }
function save(next) { localStorage.setItem(KEY, JSON.stringify(next)); return clone(next); }
function id(prefix) { return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`; }

export const api = {
  getState: () => wait(data()),
  reset: () => wait(save(clone(initialData))),
  addShoppingItem: (name) => { const d = data(); d.shopping.unshift({ id: id('s'), name: name.trim(), addedBy: d.currentUserId }); return wait(save(d)); },
  buyShoppingItem: ({ itemId, amount }) => {
    const d = data(); const item = d.shopping.find((entry) => entry.id === itemId);
    if (!item) throw new Error('Shopping item was not found');
    d.shopping = d.shopping.filter((entry) => entry.id !== itemId);
    d.expenses.unshift({ id: id('e'), name: item.name, amount: Number(amount), paidBy: d.currentUserId, participants: d.members.map((m) => m.id), createdAt: new Date().toISOString().slice(0, 10), source: 'shopping' });
    return wait(save(d));
  },
  addExpense: ({ name, amount, participants }) => { const d = data(); d.expenses.unshift({ id: id('e'), name: name.trim(), amount: Number(amount), paidBy: d.currentUserId, participants, createdAt: new Date().toISOString().slice(0, 10), source: 'direct' }); return wait(save(d)); },
  updateExpense: (expenseId, fields) => { const d = data(); const expense = d.expenses.find((entry) => entry.id === expenseId); if (!expense || expense.paidBy !== d.currentUserId) throw new Error('You can only edit your own expenses'); Object.assign(expense, fields); return wait(save(d)); },
  deleteExpense: (expenseId) => { const d = data(); const expense = d.expenses.find((entry) => entry.id === expenseId); if (!expense || expense.paidBy !== d.currentUserId) throw new Error('You can only delete your own expenses'); d.expenses = d.expenses.filter((entry) => entry.id !== expenseId); return wait(save(d)); },
  settleDebt: ({ from, to }) => { const d = data(); d.settlements.push({ id: id('st'), from, to }); return wait(save(d)); },
};
