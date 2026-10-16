const STORAGE_KEY = 'agendamiento_booking_session_id';

export function getBookingSessionId(): string {
  try {
    let id = localStorage.getItem(STORAGE_KEY);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(STORAGE_KEY, id);
    }
    return id;
  } catch {
    return `sess-${Date.now()}`;
  }
}
