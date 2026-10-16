const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export type Court = { id: number; name: string; active: boolean; sort_order?: number };

export type ComplexPublic = {
  id: number;
  name: string;
  slug: string;
  whatsapp_number: string;
  hours_start: string;
  hours_end: string;
  public_hours_start: string;
  schedule: {
    hours_start: string;
    hours_end: string;
    public_hours_start: string;
    teacher_hours_start: string;
    teacher_hours_end: string;
  };
  courts: Court[];
};

export type BusyInterval = {
  starts_at: string;
  ends_at: string;
  status: string;
  kind: string;
};

export type CalendarDay = { date: string; court_id: number; busy: BusyInterval[] };

export type CartItem = {
  court_id: number;
  court_name: string;
  date: string;
  starts_at: string;
  ends_at: string;
};

export type CartResult = {
  booking_ids: number[];
  items_count: number;
  whatsapp_url: string;
  whatsapp_message: string;
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
  kind: string;
  student_count: number | null;
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
  public_hours_start: string;
  published_courts_count: number;
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
    const detail = typeof err.detail === 'string' ? err.detail : 'Error de servidor';
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getComplex: (slug: string) => request<ComplexPublic>(`/api/public/complexes/${slug}`),
  getCalendar: (slug: string, courtId: number, from: string) =>
    request<CalendarDay[]>(
      `/api/public/complexes/${slug}/calendar?court_id=${courtId}&from=${from}&days=14`,
    ),
  submitCart: (slug: string, body: Record<string, unknown>) =>
    request<CartResult>(`/api/public/complexes/${slug}/cart`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  login: (username: string, password: string) =>
    request<{ access_token: string }>('/api/admin/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  teacherLogin: (username: string, password: string) =>
    request<{ access_token: string }>('/api/teacher/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  teacherContext: (token: string) =>
    request<{
      complex: ComplexPublic;
      teacher: { full_name: string };
      courts: Court[];
    }>('/api/teacher/complex', { headers: { Authorization: `Bearer ${token}` } }),
  teacherBooking: (token: string, body: Record<string, unknown>) =>
    request<{ id: number; message: string }>('/api/teacher/bookings', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
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
