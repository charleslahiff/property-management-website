const BASE = '';  // same origin — Cloud Run serves both API and frontend

async function req(method, path, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(BASE + path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export const api = {
  // Budget
  getBudget: (year) => req('GET', `/api/${year}/budget`),
  saveBudget: (year, data) => req('PUT', `/api/${year}/budget`, data),

  // Leaseholders
  getLeaseholders: (year) => req('GET', `/api/${year}/leaseholders/`),
  createLeaseholder: (year, data) => req('POST', `/api/${year}/leaseholders/`, data),
  updateLeaseholder: (year, id, data) => req('PUT', `/api/${year}/leaseholders/${id}`, data),
  deleteLeaseholder: (year, id) => req('DELETE', `/api/${year}/leaseholders/${id}`),

  // Expenditure
  getExpenditure: (year, fund = null) => {
    const qs = fund ? `?fund=${fund}` : '';
    return req('GET', `/api/${year}/expenditure${qs}`);
  },
  createExpenditure: (year, data) => req('POST', `/api/${year}/expenditure`, data),
  deleteExpenditure: (year, id) => req('DELETE', `/api/${year}/expenditure/${id}`),

  // Invoice upload
  uploadInvoice: async (year, expId, file) => {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${BASE}/api/${year}/expenditure/${expId}/invoice`, {
      method: 'POST',
      body: form,
    });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
  },
  getInvoiceUrl: (year, expId) => req('GET', `/api/${year}/expenditure/${expId}/invoice-url`),

  // Payments
  getPayments: (year) => req('GET', `/api/${year}/payments`),
  updatePayment: (year, lhId, data) => req('PUT', `/api/${year}/payments/${lhId}`, data),
};
