/**
 * API client service connecting Society Cart frontend to FastAPI backend.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

let storedToken: string | null = localStorage.getItem('society_cart_token');

export const setAuthToken = (token: string | null) => {
  storedToken = token;
  if (token) {
    localStorage.setItem('society_cart_token', token);
  } else {
    localStorage.removeItem('society_cart_token');
  }
};

export const getAuthToken = (): string | null => {
  return storedToken;
};

/**
 * Core fetch wrapper with auto Authorization header and JSON parsing.
 */
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = new Headers(options.headers || {});

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  if (storedToken) {
    headers.set('Authorization', `Bearer ${storedToken}`);
  }

  const config: RequestInit = {
    ...options,
    headers,
    credentials: 'include', // Include HTTP-only cookies if configured
  };

  const response = await fetch(url, config);

  if (response.status === 204) {
    return {} as T;
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorMsg = data.detail || response.statusText || 'An error occurred';
    throw new ApiError(errorMsg, response.status);
  }

  return data as T;
}

export const api = {
  auth: {
    register: (payload: { name: string; email: string; password: string; phone?: string }) =>
      request<{ access_token: string; user: any }>('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    login: (payload: { email: string; password: string }) =>
      request<{ access_token: string; user: any }>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    logout: () =>
      request<{ message: string }>('/api/auth/logout', {
        method: 'POST',
      }),

    getMe: () =>
      request<{ user: any; societies: any[] }>('/api/auth/me', {
        method: 'GET',
      }),
  },

  users: {
    getMe: () => request<any>('/api/users/me', { method: 'GET' }),
    updateMe: (payload: { name?: string; phone?: string }) =>
      request<any>('/api/users/me', {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),
  },

  societies: {
    create: (payload: {
      name: string;
      address: string;
      city: string;
      state?: string;
      country?: string;
      total_flats?: number;
      creator_flat_number: string;
    }) =>
      request<{ society: any; membership: any }>('/api/societies', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    join: (payload: { invite_code: string; flat_number: string }) =>
      request<{ society: any; membership: any }>('/api/societies/join', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    getMy: () =>
      request<Array<{ society: any; membership: any }>>('/api/societies/my', {
        method: 'GET',
      }),

    getDetails: (societyId: string) =>
      request<any>(`/api/societies/${societyId}`, { method: 'GET' }),

    getMembers: (societyId: string) =>
      request<any[]>(`/api/societies/${societyId}/members`, { method: 'GET' }),

    assignRole: (societyId: string, membershipId: string, role: 'resident' | 'volunteer') =>
      request<any>(`/api/societies/${societyId}/members/${membershipId}/role`, {
        method: 'PATCH',
        body: JSON.stringify({ role }),
      }),

    removeMember: (societyId: string, membershipId: string) =>
      request<void>(`/api/societies/${societyId}/members/${membershipId}`, {
        method: 'DELETE',
      }),
  },

  chat: {
    getToken: (societyId: string) =>
      request<{
        token: string;
        app_key: string;
        user_id: string;
        group_id: string;
        group_name: string;
      }>('/api/chat/token', {
        method: 'POST',
        body: JSON.stringify({ society_id: societyId }),
      }),

    sendSystemMessage: (societyId: string, text: string, extra?: any) =>
      request<{ status: string; message: string }>('/api/chat/system-message', {
        method: 'POST',
        body: JSON.stringify({ society_id: societyId, text, extra }),
      }),
  },
};
