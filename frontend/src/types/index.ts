/**
 * Core TypeScript type definitions for Society Cart frontend.
 */

export type UserRole = 'resident' | 'volunteer';

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
  senderRole: 'resident' | 'volunteer' | 'bot';
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
