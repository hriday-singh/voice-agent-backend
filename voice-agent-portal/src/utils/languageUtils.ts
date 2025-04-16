// Language code to full name mapping
const languageCodeMap: Record<string, string> = {
  "en-US": "English (US)",
  "en-GB": "English (UK)",
  "en-IN": "English",
  "hi-IN": "Hindi",
  "es-ES": "Spanish",
  "fr-FR": "French",
  "de-DE": "German",
  "it-IT": "Italian",
  "pt-BR": "Portuguese (Brazil)",
  "ja-JP": "Japanese",
  "ko-KR": "Korean",
  "zh-CN": "Chinese (Simplified)",
  "zh-TW": "Chinese (Traditional)",
  "ru-RU": "Russian",
  "ar-XA": "Arabic",
  "nl-NL": "Dutch",
  "pl-PL": "Polish",
  "sv-SE": "Swedish",
  "tr-TR": "Turkish",
  "da-DK": "Danish",
  "fi-FI": "Finnish",
  "no-NO": "Norwegian",
  "cs-CZ": "Czech",
  "el-GR": "Greek",
  "hu-HU": "Hungarian",
  "ro-RO": "Romanian",
  "sk-SK": "Slovak",
  "uk-UA": "Ukrainian",
  "id-ID": "Indonesian",
  "ms-MY": "Malay",
  "th-TH": "Thai",
  "vi-VN": "Vietnamese",
  "ta-IN": "Tamil",
  "bn-IN": "Bengali",
  "gu-IN": "Gujarati",
  "kn-IN": "Kannada",
  "ml-IN": "Malayalam",
  "mr-IN": "Marathi",
  "te-IN": "Telugu",
  "ur-PK": "Urdu",
  "fa-IR": "Persian",
};

// Full language name to code mapping (reverse of above)
const languageNameMap: Record<string, string> = Object.entries(
  languageCodeMap
).reduce((acc, [code, name]) => {
  acc[name] = code;
  return acc;
}, {} as Record<string, string>);

/**
 * Get the full language name for a given language code
 * @param code The ISO language code (e.g., 'en-US', 'hi-IN')
 * @returns The full language name or the original code if not found
 */
export const getLanguageName = (code: string): string => {
  return languageCodeMap[code] || code;
};

/**
 * Get the language code for a given language name
 * @param name The language name (e.g., 'English', 'Hindi')
 * @returns The language code or the original name if not found
 */
export const getLanguageCode = (name: string): string => {
  return languageNameMap[name] || name;
};

/**
 * Get the full language name with code in parentheses
 * @param code The ISO language code (e.g., 'en-US', 'hi-IN')
 * @returns The formatted language name with code, e.g., "English (en-IN)"
 */
export const getFormattedLanguageName = (code: string): string => {
  return `${getLanguageName(code)} (${code})`;
};
