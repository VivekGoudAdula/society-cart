/**
 * Utility helper to automatically detect whether a chat message is a grocery request.
 * Supports English, Telugu, Hindi, and colloquial code-switching (Hinglish/Tenglish).
 */

const CONVERSATIONAL_GREETINGS = /^(hi|hello|hey|good\s+morning|good\s+evening|good\s+afternoon|namaste|thanks|thank\s+you|ok|okay|yes|no|sure|got\s+it|noted|bye|see\s+you|congrats|welcome)\b[!.\s]*$/i;

const QUANTITY_UNIT_REGEX = /\b\d+(\.\d+)?\s*(kg|kgs|kilo|kilos|g|gm|gms|gram|grams|l|lt|ltr|ltrs|liter|liters|litre|litres|ml|packet|packets|pkt|pkts|pouch|pouches|bag|bags|box|boxes|bottle|bottles|can|cans|piece|pieces|pcs|dozen|doz|bunch|bunches|bundle|bundles|కిలో|కేజీ|లీటర్|ప్యాకెట్|గ్రాములు|किलो|लीटर|पैकेट|ग्राम)\b/i;

const GROCERY_KEYWORDS = [
  // Staples & Grains
  'rice', 'atta', 'wheat', 'flour', 'maida', 'sooji', 'rava', 'poha', 'sugar', 'salt', 'oil', 'ghee',
  // Pulses & Dals
  'dal', 'daal', 'toor', 'kandi', 'kandipappu', 'chana', 'senaga', 'pesara', 'moong', 'urad', 'rajma', 'pappu',
  // Vegetables & Fruits
  'onion', 'onions', 'potato', 'potatoes', 'tomato', 'tomatoes', 'chilli', 'mirchi', 'ginger', 'garlic', 'coriander', 'lemon', 'banana', 'apple',
  // Dairy & Household
  'milk', 'curd', 'paneer', 'butter', 'cheese', 'tea', 'coffee', 'bread', 'eggs', 'egg', 'soap', 'detergent', 'surf',
  // Telugu grocery vocabulary
  'కందిపప్పు', 'బియ్యం', 'పాలు', 'నూనె', 'పంచదార', 'ఉల్లిపాయలు', 'టమోటాలు', 'ఆటా', 'చక్కెర', 'కావాలి', 'kavali', 'ivvandi', 'teesukondi',
  // Hindi grocery vocabulary
  'चावल', 'दूध', 'तेल', 'चीनी', 'प्याज', 'टमाटर', 'आटा', 'चाहिए', 'chahiye', 'dena', 'bhejo', 'lana',
];

/**
 * Returns true if the message text looks like an apartment grocery order request.
 */
export function isLikelyGroceryMessage(text: string): boolean {
  if (!text) return false;
  const trimmed = text.trim();
  if (trimmed.length < 3) return false;

  // If purely a conversational greeting/acknowledgement, do not parse as grocery
  if (CONVERSATIONAL_GREETINGS.test(trimmed)) {
    return false;
  }

  // Pure logistical questions (e.g. "When will volunteer go?") without items
  if (/^(when|what time|who is|where|how is|are we)\b/i.test(trimmed) && trimmed.endsWith('?')) {
    return false;
  }

  // Matches numeric quantity with measurement units (e.g., "5 kg", "2L", "1 packet")
  if (QUANTITY_UNIT_REGEX.test(trimmed)) {
    return true;
  }

  // Matches common grocery keywords or Indic grocery terms
  const lower = trimmed.toLowerCase();
  for (const kw of GROCERY_KEYWORDS) {
    if (/^[a-z]+$/.test(kw)) {
      if (new RegExp(`\\b${kw}\\b`, 'i').test(lower)) {
        return true;
      }
    } else {
      if (trimmed.includes(kw)) {
        return true;
      }
    }
  }

  return false;
}
