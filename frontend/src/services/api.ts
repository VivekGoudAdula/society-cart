/**
 * API client service connecting Society Cart frontend to FastAPI backend.
 */

import {
  ApiOrderRound,
  ApiRoundListResponse,
  ApiGrocerySubmission,
  ApiGroceryOrder,
  ApiGroceryOrderItem,
  ApiCompiledShoppingList,
  ApiUnresolvedOrderInfo,
  ApiPurchaseRecord,
  ApiRecordPurchaseRequest,
  ApiUpdatePurchaseRequest,
  ApiAllocationPreviewResponse,
  ApiFinalizeBillsRequest,
  ApiGroceryBill,
  ApiPublishBillsAnnouncementResponse,
  ApiSocietySpendingSummary,
  ApiRetailBenchmark,
  ApiRecordBenchmarkRequest,
  ApiSocietySavingsSummary,
} from '../types';

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

  rounds: {
    getActive: (societyId: string) =>
      request<ApiOrderRound | null>(`/api/societies/${societyId}/rounds/active`),

    list: (societyId: string, skip = 0, limit = 20) =>
      request<ApiRoundListResponse>(`/api/societies/${societyId}/rounds?skip=${skip}&limit=${limit}`),

    getById: (societyId: string, roundId: string) =>
      request<ApiOrderRound>(`/api/societies/${societyId}/rounds/${roundId}`),

    create: (
      societyId: string,
      data: {
        title: string;
        description?: string;
        deadline_at: string;
        shopping_date: string;
      }
    ) =>
      request<ApiOrderRound>(`/api/societies/${societyId}/rounds`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    open: (societyId: string, roundId: string) =>
      request<ApiOrderRound>(`/api/societies/${societyId}/rounds/${roundId}/open`, {
        method: 'POST',
      }),

    close: (societyId: string, roundId: string) =>
      request<ApiOrderRound>(`/api/societies/${societyId}/rounds/${roundId}/close`, {
        method: 'POST',
      }),

    reserveSubmission: (
      societyId: string,
      roundId: string,
      data: {
        submission_id: string;
        raw_text: string;
      }
    ) =>
      request<ApiGrocerySubmission>(`/api/societies/${societyId}/rounds/${roundId}/submissions/reserve`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    confirmSubmission: (
      societyId: string,
      roundId: string,
      submissionId: string,
      data: {
        message_id: string;
      }
    ) =>
      request<ApiGrocerySubmission>(`/api/societies/${societyId}/rounds/${roundId}/submissions/${submissionId}/confirm`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    failSubmission: (
      societyId: string,
      roundId: string,
      submissionId: string,
      data?: {
        reason?: string;
      }
    ) =>
      request<ApiGrocerySubmission>(`/api/societies/${societyId}/rounds/${roundId}/submissions/${submissionId}/fail`, {
        method: 'POST',
        body: JSON.stringify(data || {}),
      }),

    submitOrder: (
      societyId: string,
      roundId: string,
      data: {
        message_id: string;
        raw_text: string;
      }
    ) =>
      request<ApiGrocerySubmission>(`/api/societies/${societyId}/rounds/${roundId}/submissions`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    getSubmissions: (societyId: string, roundId: string) =>
      request<ApiGrocerySubmission[]>(`/api/societies/${societyId}/rounds/${roundId}/submissions`),
  },

  orders: {
    listByRound: (societyId: string, roundId: string) =>
      request<ApiGroceryOrder[]>(`/api/societies/${societyId}/rounds/${roundId}/orders`),

    getById: (orderId: string) =>
      request<ApiGroceryOrder>(`/api/orders/${orderId}`),

    clarify: (orderId: string, clarificationText: string) =>
      request<ApiGroceryOrder>(`/api/orders/${orderId}/clarify`, {
        method: 'POST',
        body: JSON.stringify({ clarification_text: clarificationText }),
      }),

    updateItems: (orderId: string, items: ApiGroceryOrderItem[]) =>
      request<ApiGroceryOrder>(`/api/orders/${orderId}/items`, {
        method: 'PATCH',
        body: JSON.stringify({ items }),
      }),

    confirm: (orderId: string) =>
      request<ApiGroceryOrder>(`/api/orders/${orderId}/confirm`, {
        method: 'POST',
      }),

    reject: (orderId: string) =>
      request<ApiGroceryOrder>(`/api/orders/${orderId}/reject`, {
        method: 'POST',
      }),

    retry: (orderId: string) =>
      request<ApiGroceryOrder>(`/api/orders/${orderId}/retry`, {
        method: 'POST',
      }),
  },

  shoppingList: {
    compile: (societyId: string, roundId: string) =>
      request<ApiCompiledShoppingList>(
        `/api/societies/${societyId}/rounds/${roundId}/shopping-list/compile`,
        { method: 'POST' }
      ),

    get: (societyId: string, roundId: string) =>
      request<ApiCompiledShoppingList>(
        `/api/societies/${societyId}/rounds/${roundId}/shopping-list`
      ),

    getUnresolved: (societyId: string, roundId: string) =>
      request<ApiUnresolvedOrderInfo[]>(
        `/api/societies/${societyId}/rounds/${roundId}/shopping-list/unresolved`
      ),

    downloadCsv: async (
      societyId: string,
      roundId: string,
      type: 'consolidated' | 'packing' = 'consolidated'
    ): Promise<void> => {
      const headers: Record<string, string> = {};
      if (storedToken) {
        headers['Authorization'] = `Bearer ${storedToken}`;
      }
      const res = await fetch(
        `${API_BASE_URL}/api/societies/${societyId}/rounds/${roundId}/shopping-list/export?type=${type}`,
        { headers }
      );
      if (!res.ok) {
        throw new Error(`Failed to export CSV: ${res.statusText}`);
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `shopping_list_round_${roundId}_${type}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },
  },

  billing: {
    recordPurchase: (societyId: string, roundId: string, data: ApiRecordPurchaseRequest) =>
      request<ApiPurchaseRecord>(
        `/api/societies/${societyId}/rounds/${roundId}/purchases`,
        { method: 'POST', body: JSON.stringify(data) }
      ),

    listPurchases: (societyId: string, roundId: string) =>
      request<ApiPurchaseRecord[]>(
        `/api/societies/${societyId}/rounds/${roundId}/purchases`
      ),

    updatePurchase: (
      societyId: string,
      roundId: string,
      purchaseId: string,
      data: ApiUpdatePurchaseRequest
    ) =>
      request<ApiPurchaseRecord>(
        `/api/societies/${societyId}/rounds/${roundId}/purchases/${purchaseId}`,
        { method: 'PATCH', body: JSON.stringify(data) }
      ),

    deletePurchase: (societyId: string, roundId: string, purchaseId: string) =>
      request<{ status: string; purchase_id: string }>(
        `/api/societies/${societyId}/rounds/${roundId}/purchases/${purchaseId}`,
        { method: 'DELETE' }
      ),

    getAllocationPreview: (societyId: string, roundId: string) =>
      request<ApiAllocationPreviewResponse>(
        `/api/societies/${societyId}/rounds/${roundId}/allocation/preview`
      ),

    finalizeBills: (societyId: string, roundId: string, data: ApiFinalizeBillsRequest) =>
      request<ApiGroceryBill[]>(
        `/api/societies/${societyId}/rounds/${roundId}/bills/finalize`,
        { method: 'POST', body: JSON.stringify(data) }
      ),

    getRoundBills: (societyId: string, roundId: string) =>
      request<ApiGroceryBill[]>(
        `/api/societies/${societyId}/rounds/${roundId}/bills`
      ),

    publishAnnouncement: (societyId: string, roundId: string) =>
      request<ApiPublishBillsAnnouncementResponse>(
        `/api/societies/${societyId}/rounds/${roundId}/bills/publish`,
        { method: 'POST' }
      ),

    getSpendingSummary: (societyId: string, roundId: string) =>
      request<ApiSocietySpendingSummary>(
        `/api/societies/${societyId}/rounds/${roundId}/spending-summary`
      ),

    recordBenchmark: (societyId: string, roundId: string, data: ApiRecordBenchmarkRequest) =>
      request<ApiRetailBenchmark>(
        `/api/societies/${societyId}/rounds/${roundId}/benchmarks`,
        { method: 'POST', body: JSON.stringify(data) }
      ),

    listBenchmarks: (societyId: string, roundId: string) =>
      request<ApiRetailBenchmark[]>(
        `/api/societies/${societyId}/rounds/${roundId}/benchmarks`
      ),

    getSavingsSummary: (societyId: string, roundId: string) =>
      request<ApiSocietySavingsSummary>(
        `/api/societies/${societyId}/rounds/${roundId}/savings`
      ),

    getMyBills: () =>
      request<ApiGroceryBill[]>('/api/users/me/bills'),

    getMyBillById: (billId: string) =>
      request<ApiGroceryBill>(`/api/users/me/bills/${billId}`),
  },
};
