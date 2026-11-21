/**
 * Nexconn Web SDK client managing real-time connection lifecycle,
 * channel messaging, and message history for Society Cart.
 */

import {
  NCEngine,
  ConnectionStatusHandler,
  MessageHandler,
  GroupChannel,
  BaseChannel,
  GroupChannelIdentifier,
  SendTextMessageParams,
  AreaCode,
  ConnectionStatus,
  Message,
} from '@nexconn/chat';
import { NexconnConnectionState, NexconnChatMessage } from './nexconnTypes';

type ConnectionStateListener = (state: NexconnConnectionState) => void;
type MessageListener = (message: NexconnChatMessage) => void;

class NexconnClientService {
  private isInitialized = false;
  private currentUserId = '';
  private activeGroupId = '';
  private activeToken = '';
  private connectionState: NexconnConnectionState = 'disconnected';
  private memberLookup: Record<string, { name: string; flatNumber: string; role?: string }> = {};

  private stateListeners = new Set<ConnectionStateListener>();
  private messageListeners = new Set<MessageListener>();

  /**
   * Sets or updates the society member lookup table for resolving sender details.
   */
  public setMemberLookup(lookup: Record<string, { name: string; flatNumber: string; role?: string }>): void {
    this.memberLookup = { ...lookup };
  }

  /**
   * Initializes the Nexconn SDK once during the application lifecycle.
   */
  public initialize(appKey: string): void {
    if (this.isInitialized) return;

    try {
      NCEngine.initialize({
        appKey,
        areaCode: AreaCode.SG,
      });

      // Register connection status handler
      NCEngine.addConnectionStatusHandler(
        'society_cart_connection',
        new ConnectionStatusHandler({
          onConnectionStatusChanged: ({ status }) => {
            let mappedState: NexconnConnectionState = 'disconnected';
            switch (status) {
              case ConnectionStatus.CONNECTED:
                mappedState = 'connected';
                break;
              case ConnectionStatus.CONNECTING:
                mappedState = 'connecting';
                break;
              case ConnectionStatus.DISCONNECTED:
                mappedState = 'disconnected';
                break;
              default:
                mappedState = 'reconnecting';
                break;
            }
            this.setConnectionState(mappedState);
          },
        })
      );

      // Register incoming message event handler
      NCEngine.addMessageHandler(
        'society_cart_messages',
        new MessageHandler({
          onMessageReceived: ({ messages }) => {
            if (!messages || messages.length === 0) return;

            for (const rawMsg of messages) {
              const parsed = this.parseRawMessage(rawMsg, this.memberLookup);
              if (parsed) {
                this.messageListeners.forEach((listener) => listener(parsed));
              }
            }
          },
        })
      );

      this.isInitialized = true;
    } catch (err) {
      console.error('[NexconnClient] Initialization error:', err);
      this.setConnectionState('error');
    }
  }

  /**
   * Connects the authenticated user to the Nexconn network with their server-issued token.
   */
  public async connect(token: string, userId: string, groupId: string): Promise<boolean> {
    if (!token) return false;

    // Avoid reconnecting if already connected with the same session
    if (
      this.connectionState === 'connected' &&
      this.activeToken === token &&
      this.currentUserId === userId &&
      this.activeGroupId === groupId
    ) {
      return true;
    }

    // Always tear down any existing connection before initiating a new one to prevent identity cross-talk
    try {
      await NCEngine.disconnect();
    } catch {
      // Disconnect cleanup error is non-fatal
    }

    this.currentUserId = userId;
    this.activeGroupId = groupId;
    this.activeToken = token;
    this.setConnectionState('connecting');

    for (let attempt = 1; attempt <= 2; attempt++) {
      try {
        const result = await NCEngine.connect({ token });
        if (result && result.isOk) {
          this.setConnectionState('connected');
          return true;
        }
        if (attempt === 2) {
          console.warn('[NexconnClient] Connect returned non-ok result after retry:', result);
          this.setConnectionState('error');
          return false;
        }
      } catch (err) {
        if (attempt === 2) {
          console.error('[NexconnClient] Failed to connect after retry:', err);
          this.setConnectionState('error');
          return false;
        }
        await new Promise((r) => setTimeout(r, 500));
      }
    }
    return false;
  }

  /**
   * Disconnects the user and cleans up the active session.
   */
  public async disconnect(): Promise<void> {
    try {
      await NCEngine.disconnect();
    } catch (err) {
      console.warn('[NexconnClient] Disconnect warning:', err);
    } finally {
      this.currentUserId = '';
      this.activeGroupId = '';
      this.activeToken = '';
      this.memberLookup = {};
      this.setConnectionState('disconnected');
    }
  }

  /**
   * Sends a text message to the society's group channel.
   */
  public async sendMessage(
    groupId: string,
    text: string,
    senderProfile?: { name: string; flatNumber: string; role?: string }
  ): Promise<NexconnChatMessage> {
    if (!text.trim()) {
      throw new Error('Message text cannot be empty');
    }

    const group = new GroupChannel(groupId);
    const params = new SendTextMessageParams({ text: text.trim() });

    const result = await group.sendMessage(params);

    if (!result || !result.isOk || !result.data) {
      const errMsg = (result as any)?.error?.message || 'Failed to send message to Nexconn channel';
      throw new Error(errMsg);
    }

    const sentMessage = result.data;
    const timeString = new Date(sentMessage.sentTime || Date.now()).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });

    const resolvedSenderName = senderProfile?.name || this.memberLookup[this.currentUserId]?.name || 'You';
    const resolvedSenderFlat = senderProfile?.flatNumber || this.memberLookup[this.currentUserId]?.flatNumber;
    const resolvedSenderRole = (senderProfile?.role as any) || (this.memberLookup[this.currentUserId]?.role as any) || 'resident';

    return {
      id: sentMessage.messageId || `msg_${Date.now()}`,
      senderId: this.currentUserId,
      senderName: resolvedSenderName,
      senderFlat: resolvedSenderFlat,
      senderRole: resolvedSenderRole,
      timestamp: timeString,
      sentTime: sentMessage.sentTime || Date.now(),
      text: text.trim(),
      isSelf: true,
      isSystemBot: false,
    };
  }

  /**
   * Loads recent message history from the Nexconn group channel.
   */
  public async fetchMessageHistory(
    groupId: string,
    pageSize = 40,
    memberLookup?: Record<string, { name: string; flatNumber: string; role?: string }>
  ): Promise<NexconnChatMessage[]> {
    try {
      const query = BaseChannel.createMessagesQuery({
        channelIdentifier: new GroupChannelIdentifier(groupId),
        pageSize,
      });

      const result = await query.loadNextPage();

      if (!result || !result.isOk || !result.data) {
        return [];
      }

      const rawList: Array<Message<any>> = result.data.data || [];
      const parsedList: NexconnChatMessage[] = [];

      for (const m of rawList) {
        const parsed = this.parseRawMessage(m, memberLookup);
        if (parsed) {
          parsedList.push(parsed);
        }
      }

      // Sort chronologically ascending
      return parsedList.sort((a, b) => a.sentTime - b.sentTime);
    } catch (err) {
      console.warn('[NexconnClient] Could not fetch channel history:', err);
      return [];
    }
  }

  /**
   * Subscribe to connection status changes.
   */
  public onConnectionStateChange(listener: ConnectionStateListener): () => void {
    this.stateListeners.add(listener);
    listener(this.connectionState);
    return () => this.stateListeners.delete(listener);
  }

  /**
   * Subscribe to real-time incoming messages.
   */
  public onMessage(listener: MessageListener): () => void {
    this.messageListeners.add(listener);
    return () => this.messageListeners.delete(listener);
  }

  public getConnectionState(): NexconnConnectionState {
    return this.connectionState;
  }

  private setConnectionState(newState: NexconnConnectionState) {
    if (this.connectionState === newState) return;
    this.connectionState = newState;
    this.stateListeners.forEach((listener) => listener(newState));
  }

  /**
   * Formats a raw Nexconn Message into Society Cart's message shape.
   */
  private parseRawMessage(
    raw: Message<any>,
    memberLookup?: Record<string, { name: string; flatNumber: string; role?: string }>
  ): NexconnChatMessage | null {
    if (!raw) return null;

    const senderId = raw.senderUserId || '';
    const isSelf = senderId === this.currentUserId;
    const isBot = senderId === 'society_cart_bot';

    const contentText =
      raw.content?.text ||
      raw.content?.content ||
      (typeof raw.content === 'string' ? raw.content : '');

    if (!contentText && !isBot) return null;

    const lookup = memberLookup || this.memberLookup;
    const member = lookup ? lookup[senderId] : undefined;

    const sentTime = raw.sentTime || Date.now();
    const timeString = new Date(sentTime).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });

    const resolvedName = isBot
      ? 'Society Cart Assistant'
      : member?.name || (senderId ? `Resident (${senderId.slice(-4)})` : 'Resident');

    return {
      id: raw.messageId || `msg_${sentTime}_${Math.random()}`,
      senderId,
      senderName: resolvedName,
      senderFlat: member?.flatNumber,
      senderRole: isBot ? 'bot' : (member?.role as any) || 'resident',
      timestamp: timeString,
      sentTime,
      text: contentText,
      isSelf,
      isSystemBot: isBot,
    };
  }
}

export const nexconnClient = new NexconnClientService();
