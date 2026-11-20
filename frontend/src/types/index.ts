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

// =============================================================================
// Phase 7 — Billing, Allocations, Benchmarks & Savings Types
// =============================================================================

export type ApiBillStatus = 'draft' | 'finalized' | 'published' | 'corrected' | 'cancelled';

export interface ApiPurchaseRecord {
  id: string;
  society_id: string;
  round_id: string;
  item_name: string;
  normalized_name: string;
  category: string;
  brand?: string | null;
  variant?: string | null;
  actual_quantity: number;
  unit: string;
  total_price: number;
  unit_price: number;
  shop_name: string;
  purchase_date: string;
  invoice_ref?: string | null;
  notes?: string | null;
  is_substitution: boolean;
  substitute_for_item_name?: string | null;
  substitute_for_brand?: string | null;
  substitute_for_variant?: string | null;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
}

export interface ApiRecordPurchaseRequest {
  item_name: string;
  category: string;
  brand?: string | null;
  variant?: string | null;
  actual_quantity: number;
  unit: string;
  total_price: number;
  shop_name: string;
  purchase_date?: string | null;
  invoice_ref?: string | null;
  notes?: string | null;
  is_substitution?: boolean;
  substitute_for_item_name?: string | null;
}

export interface ApiUpdatePurchaseRequest {
  item_name?: string | null;
  category?: string | null;
  brand?: string | null;
  variant?: string | null;
  actual_quantity?: number | null;
  unit?: string | null;
  total_price?: number | null;
  shop_name?: string | null;
  invoice_ref?: string | null;
  notes?: string | null;
  is_substitution?: boolean | null;
  substitute_for_item_name?: string | null;
}

export interface ApiItemAllocationDetail {
  item_name: string;
  normalized_name: string;
  brand?: string | null;
  variant?: string | null;
  category: string;
  requested_quantity: number;
  allocated_quantity: number;
  unit: string;
  unit_price: number;
  item_total: number;
  is_substituted: boolean;
  substitute_notes?: string | null;
  is_unfulfilled: boolean;
  unfulfilled_quantity: number;
}

export interface ApiFlatAllocationPreview {
  flat_number: string;
  resident_name: string;
  user_id: string;
  order_id: string;
  items: ApiItemAllocationDetail[];
  items_subtotal: number;
  shared_costs_allocated: number;
  rounding_adjustment: number;
  final_amount_payable: number;
}

export interface ApiPurchasedItemMatchingSummary {
  item_key: string;
  item_name: string;
  brand?: string | null;
  variant?: string | null;
  category: string;
  unit: string;
  requested_quantity: number;
  purchased_quantity: number;
  fulfilled_quantity: number;
  unfulfilled_quantity: number;
  is_substituted: boolean;
  substitute_item_name?: string | null;
  effective_unit_cost: number;
  total_cost: number;
}

export interface ApiAllocationPreviewResponse {
  society_id: string;
  round_id: string;
  round_number: number;
  matching_summaries: ApiPurchasedItemMatchingSummary[];
  flat_allocations: ApiFlatAllocationPreview[];
  total_actual_purchase_cost: number;
  total_allocated_flats_cost: number;
  total_shared_costs: number;
  unallocated_cost: number;
  is_reconciled: boolean;
  reconciliation_message: string;
  can_finalize: boolean;
}

export interface ApiSharedCostEntry {
  name: string;
  amount: number;
  notes?: string | null;
}

export interface ApiFinalizeBillsRequest {
  shared_costs?: ApiSharedCostEntry[];
  rounding_policy?: string;
}

export interface ApiGroceryBill {
  id: string;
  society_id: string;
  round_id: string;
  round_number: number;
  society_name: string;
  user_id: string;
  flat_number: string;
  resident_name: string;
  order_id: string;
  status: ApiBillStatus;
  bill_version: number;
  items: ApiItemAllocationDetail[];
  shared_costs: ApiSharedCostEntry[];
  items_subtotal: number;
  shared_costs_total: number;
  rounding_adjustment: number;
  total_amount: number;
  is_reconciled: boolean;
  created_at: string;
  updated_at: string;
  finalized_at?: string | null;
  published_at?: string | null;
  previous_version_bill_id?: string | null;
  correction_notes?: string | null;
}

export interface ApiPublishBillsAnnouncementResponse {
  society_id: string;
  round_id: string;
  round_number: number;
  group_id: string;
  message_text: string;
  sent: boolean;
  delivery_status: string;
  attempts: number;
  published_at: string;
}

export interface ApiSocietySpendingSummary {
  society_id: string;
  round_id: string;
  round_number: number;
  total_actual_purchase_cost: number;
  total_allocated_bill_costs: number;
  total_shared_costs: number;
  total_unallocated_cost: number;
  is_reconciled: boolean;
  reconciliation_equation: string;
  total_purchased_items_count: number;
  total_flats_billed: number;
  total_finalized_bills: number;
  total_unfulfilled_items_count: number;
  total_substituted_items_count: number;
  unresolved_discrepancies: string[];
}

export interface ApiRetailBenchmark {
  id: string;
  society_id: string;
  product_name: string;
  brand?: string | null;
  variant?: string | null;
  package_size: number;
  package_unit: string;
  benchmark_price: number;
  benchmark_unit_price: number;
  store_name: string;
  source_type: string;
  evidence_ref?: string | null;
  evidence_url?: string | null;
  evidence_date: string;
  location: string;
  verification_status: string;
  verified_by?: string | null;
  verified_at?: string | null;
  created_at: string;
}

export interface ApiRecordBenchmarkRequest {
  product_name: string;
  brand?: string | null;
  variant?: string | null;
  package_size: number;
  package_unit: string;
  benchmark_price: number;
  store_name: string;
  source_type: string;
  evidence_ref?: string | null;
  evidence_url?: string | null;
  evidence_date: string;
  location: string;
}

export interface ApiItemSavingsDetail {
  item_name: string;
  brand?: string | null;
  variant?: string | null;
  quantity: number;
  unit: string;
  bulk_cost: number;
  bulk_unit_price: number;
  has_benchmark: boolean;
  benchmark_price?: number | null;
  benchmark_unit_price?: number | null;
  benchmark_store?: string | null;
  benchmark_date?: string | null;
  benchmark_cost?: number | null;
  savings_amount?: number | null;
  savings_percentage?: number | null;
  status_label: string;
  unavailability_reason?: string | null;
}

export interface ApiSocietySavingsSummary {
  society_id: string;
  round_id: string;
  round_number: number;
  total_bulk_cost_comparable_items: number;
  total_individual_benchmark_cost: number;
  verified_savings_amount: number;
  verified_savings_percentage: number;
  total_items_evaluated: number;
  items_with_verified_benchmarks: number;
  items_excluded_count: number;
  is_partial_coverage: boolean;
  label: string;
  items: ApiItemSavingsDetail[];
}

