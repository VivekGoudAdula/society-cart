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

export type ApiGroceryCategory =
  | 'grains_rice'
  | 'pulses'
  | 'vegetables'
  | 'fruits'
  | 'dairy'
  | 'cooking_oils'
  | 'spices'
  | 'household_essentials'
  | 'personal_care'
  | 'other';

export type ApiOrderStatus =
  | 'processing'
  | 'pending_review'
  | 'awaiting_confirmation'
  | 'needs_clarification'
  | 'confirmed'
  | 'rejected'
  | 'failed';

export interface ApiGroceryOrderItem {
  id: string;
  original_name: string;
  normalized_name: string;
  quantity: number | null;
  unit: string | null;
  category: ApiGroceryCategory | string;
  brand?: string | null;
  variant?: string | null;
  confidence: number;
  needs_clarification: boolean;
  clarification_reason?: string | null;
}

export interface ClarificationHistoryItem {
  prompt: string;
  resident_response: string;
  timestamp: string;
}

export interface ApiGroceryOrder {
  id: string;
  society_id: string;
  round_id: string;
  round_number: number;
  submission_id: string;
  message_id: string;
  user_id: string;
  flat_number: string;
  user_name: string;
  raw_text: string;
  detected_language: string;
  items: ApiGroceryOrderItem[];
  status: ApiOrderStatus;
  clarification_prompt?: string | null;
  clarification_history: ClarificationHistoryItem[];
  ai_model: string;
  prompt_version: string;
  created_at: string;
  updated_at: string;
  confirmed_at?: string | null;
}

// =============================================================================
// Phase 6 — Volunteer Shopping Dashboard & Manifest Types
// =============================================================================

export interface ApiContributingFlat {
  flat_number: string;
  user_id: string;
  user_name: string;
  order_id: string;
  quantity: number;
  unit?: string | null;
  notes?: string | null;
}

export interface ApiConsolidatedItem {
  item_key: string;
  normalized_name: string;
  brand?: string | null;
  variant?: string | null;
  category: string;
  total_quantity: number;
  unit: string;
  contributing_flats: ApiContributingFlat[];
  contributing_flats_count: number;
  original_names: string[];
  has_unspecified_quantity?: boolean;
  is_purchased?: boolean;
}

export interface ApiCategoryGroup {
  category: string;
  category_name: string;
  items: ApiConsolidatedItem[];
  item_count: number;
}

export interface ApiPackingFlatItem {
  item_id: string;
  original_name: string;
  normalized_name: string;
  brand?: string | null;
  variant?: string | null;
  quantity?: number | null;
  unit?: string | null;
  category: string;
  is_packed?: boolean;
}

export interface ApiFlatPackingBreakdown {
  flat_number: string;
  user_id: string;
  user_name: string;
  order_id: string;
  items: ApiPackingFlatItem[];
  total_items: number;
}

export interface ApiUnresolvedOrderInfo {
  order_id: string;
  flat_number: string;
  user_id: string;
  user_name: string;
  status: ApiOrderStatus | string;
  clarification_prompt?: string | null;
  error_message?: string | null;
  raw_text: string;
  updated_at: string;
}

export interface ApiShoppingListSummary {
  total_confirmed_flats: number;
  total_confirmed_orders: number;
  total_distinct_items: number;
  total_items_count: number;
  total_unresolved_flats: number;
  total_unresolved_orders: number;
  has_unresolved_orders: boolean;
  rejected_orders_count: number;
}

export interface ApiCompiledShoppingList {
  id: string;
  society_id: string;
  round_id: string;
  round_number: number;
  round_title?: string | null;
  shopping_date?: string | null;
  version: number;
  compiled_at: string;
  source_snapshot_at?: string | null;
  compiled_by_user_id: string;
  summary: ApiShoppingListSummary;
  categories: ApiCategoryGroup[];
  packing_breakdown: ApiFlatPackingBreakdown[];
  unresolved_orders: ApiUnresolvedOrderInfo[];
}

