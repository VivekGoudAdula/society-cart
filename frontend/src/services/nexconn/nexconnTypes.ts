/**
 * Type definitions for Nexconn Chat Web SDK integration in Society Cart.
 */

export type NexconnConnectionState =
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'reconnecting'
  | 'error';

export interface NexconnChatMessage {
  id: string;
  senderId: string;
  senderName: string;
  senderRole?: 'resident' | 'volunteer' | 'admin' | 'bot';
  senderFlat?: string;
  avatarUrl?: string;
  timestamp: string;
  sentTime: number;
  text: string;
  isSelf: boolean;
  isSystemBot?: boolean;
  structuredItems?: Array<{
    name: string;
    quantity: string;
  }>;
}

export interface NexconnTokenResponse {
  token: string;
  app_key: string;
  user_id: string;
  group_id: string;
  group_name: string;
}
