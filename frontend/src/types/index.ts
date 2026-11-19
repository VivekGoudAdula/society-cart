/**
 * Core TypeScript type definitions for Society Cart frontend.
 */

export type UserRole = 'resident' | 'volunteer' | 'admin';

export interface ApiSociety {
  id: string;
  name: string;
  address: string;
  city: string;
  state?: string;
  country: string;
  invite_code: string;
  created_by: string;
  created_at: string;
  is_active: boolean;
  total_flats?: number;
}

export interface ApiMembership {
  id: string;
  user_id: string;
  society_id: string;
  flat_number: string;
  role: UserRole;
  joined_at: string;
  is_active: boolean;
  user_name?: string;
  user_email?: string;
}

export interface UserSocietyPair {
  society: ApiSociety;
  membership: ApiMembership;
}

export interface UserProfile {
  id: string;
  name: string;
  flatNumber: string;
  societyId: string;
  societyName: string;
  role: UserRole;
  avatarUrl?: string;
  email: string;
  phone: string;
}

export interface Society {
  id: string;
  name: string;
  locality: string;
  city: string;
  totalFlats: number;
  inviteCode: string;
  activeRoundId: string;
}

export type RoundStatus = 'open' | 'closed' | 'purchasing' | 'delivered';

export interface OrderRound {
  id: string;
  roundNumber: number;
  title: string;
  status: RoundStatus;
  deadlineText: string;
  shopVisitDate: string;
  volunteerName: string;
  volunteerFlat: string;
  participatingFlatsCount: number;
  totalItemsCount: number;
  estimatedTotalValue: number;
  finalPurchasedValue?: number;
}

export type GroceryCategory =
  | 'Vegetables'
  | 'Fruits'
  | 'Grains & Staples'
  | 'Dairy'
  | 'Household'
  | 'Others';

export interface FlatRequest {
  flatNumber: string;
  residentName: string;
  quantity: number;
}

export interface GroceryItem {
  id: string;
  name: string;
  category: GroceryCategory;
  totalQuantity: number;
  unit: string;
  flatsCount: number;
  flatRequests: FlatRequest[];
  isPurchased: boolean;
  estimatedUnitPrice: number;
  benchmarkUnitPrice: number;
}

export interface ChatMessage {
  id: string;
  senderId: string;
  senderName: string;
  senderRole: UserRole | 'bot';
  senderFlat?: string;
  avatarUrl?: string;
  timestamp: string;
  text: string;
  isBotInterpretation?: boolean;
  structuredItems?: Array<{
    name: string;
    quantity: string;
  }>;
}

export interface BillItem {
  id: string;
  name: string;
  quantity: number;
  unit: string;
  unitPrice: number;
  totalPrice: number;
  benchmarkPrice: number;
}

export interface ResidentBill {
  id: string;
  roundId: string;
  roundTitle: string;
  orderDate: string;
  flatNumber: string;
  residentName: string;
  items: BillItem[];
  subtotal: number;
  deliveryHandlingFee: number;
  finalPayableAmount: number;
  benchmarkMarketTotal: number;
  totalSavings: number;
  status: 'paid' | 'pending';
}

export interface ActivityNotification {
  id: string;
  title: string;
  description: string;
  timestamp: string;
  type: 'round_opened' | 'order_confirmed' | 'volunteer_update' | 'bill_generated';
  read: boolean;
}

export type ApiRoundStatus = 'draft' | 'open' | 'closed' | 'cancelled';

export interface AnnouncementDeliveryState {
  status: 'pending' | 'sent' | 'failed';
  attempts: number;
  last_attempt_at?: string;
  sent_at?: string;
  last_error?: string;
}

export interface ApiOrderRound {
  id: string;
  society_id: string;
  round_number: number;
  title: string;
  description?: string;
  status: ApiRoundStatus;
  created_by: string;
  created_at: string;
  opened_at?: string;
  deadline_at: string;
  shopping_date: string;
  closed_at?: string;
  updated_at: string;
  submissions_count: number;
  opening_announcement?: AnnouncementDeliveryState;
  closing_announcement?: AnnouncementDeliveryState;
  opening_announcement_sent?: boolean;
  closing_announcement_sent?: boolean;
}

export interface ApiRoundListResponse {
  items: ApiOrderRound[];
  total: number;
}

export interface ApiGrocerySubmission {
  id: string;
  submission_id?: string;
  society_id: string;
  round_id: string;
  round_number: number;
  user_id: string;
  flat_number: string;
  user_name: string;
  message_id?: string;
  raw_text: string;
  status: 'reserved' | 'confirmed' | 'failed' | 'pending' | 'parsed' | string;
  reserved_at?: string;
  confirmed_at?: string;
  created_at: string;
}
