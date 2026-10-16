const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export type Court = { id: number; name: string; active: boolean };

export type ComplexPublic = {
  id: number;
  name: string;
  slug: string;
  whatsapp_number: string;
  hours_start: string;
  hours_end: string;
  courts: Court[];
};

export type Slot = { starts_at: string; ends_at: string };

export type AvailabilityDay = { date: string; court_id: number; slots: Slot[] };

export type BookingResult = {
  id: number;
  court_name: string;
  starts_at: string;
  ends_at: string;
  customer_name: string;
  customer_phone: string;
  customer_email: string;
  status: string;
  whatsapp_url: string;
  whatsapp_message: string;
  calendar_mode: string;
  calendar_tentative: boolean;
  message: string;
};

export type BookingAdmin = {
  id: number;
  court_name: string;
  starts_at: string;
  ends_at: string;
  customer_name: string;
  customer_phone: string;
  customer_email: string;
  customer_notes: string;
  status: string;
  calendar_tentative: boolean;
  notes: string;
};

export type ComplexAdmin = {
  id: number;
  name: string;
  slug: string;
  whatsapp_number: string;
  contact_email: string;
  hours_start: string;
  hours_end: string;
  google_connected: boolean;
  courts: Court[];
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? 'Error de servidor');
  }
  return res.json() as Promise<T>;
}

export const api = {
  getComplex: (slug: string) => request<ComplexPublic>(`/api/public/complexes/${slug}`),
  getAvailability: (slug: string, courtId: number, from: string) =>
    request<AvailabilityDay[]>(
      `/api/public/complexes/${slug}/availability?court_id=${courtId}&from=${from}&days=7`,
    ),
  createBooking: (slug: string, body: Record<string, unknown>) =>
    request<BookingResult>(`/api/public/complexes/${slug}/bookings`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  login: (username: string, password: string) =>
    request<{ access_token: string }>('/api/admin/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  adminComplex: (token: string) =>
    request<ComplexAdmin>('/api/admin/complex', {
      headers: { Authorization: `Bearer ${token}` },
    }),
  updateComplex: (token: string, body: Record<string, unknown>) =>
    request<ComplexAdmin>('/api/admin/complex', {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  listBookings: (token: string) =>
    request<BookingAdmin[]>('/api/admin/bookings', {
      headers: { Authorization: `Bearer ${token}` },
    }),
  bookingAction: (token: string, id: number, action: 'confirm' | 'reject') =>
    request<BookingAdmin>(`/api/admin/bookings/${id}/action`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ action }),
    }),
  integrations: (token: string) =>
    request<{
      google: { configured: boolean; connected: boolean; missing_env: string[]; calendar_mode: string };
    }>('/api/admin/integrations', { headers: { Authorization: `Bearer ${token}` } }),
};
