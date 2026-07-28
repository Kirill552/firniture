export const EMPTY_AI_RESPONSE_TEXT = 'Уточните параметры изделия.';

export interface ParsedAiResponse {
  cleanText: string;
  buttons: string[];
}

function extractButtonLabels(markerContent: string): string[] {
  return markerContent
    .split(',')
    .map((label) => label.trim().replace(/^['"]|['"]$/g, ''))
    .map((label) => label.replace(/\s*\([A-Za-z][A-Za-z0-9_-]*\)\s*$/, '').trim())
    .filter(Boolean);
}

function removeInternalBlocks(text: string): string {
  return text
    .replace(/<think>[\s\S]*?(?:<\/think>|$)/gi, '')
    .replace(/\[(?:TOOL_CALL|FUNCTION_CALL)\b[^\]]*\]/gi, '')
    .replace(/```\s*\{[\s\S]*?"(?:name|function)"[\s\S]*?\}\s*```/gi, '')
    .replace(/\{\s*"name"\s*:\s*"[^\"]+"\s*,\s*"arguments"\s*:\s*\{[^}]*\}\s*\}/gi, '')
    .replace(/`?function_call\s*:\s*[^`\n.]+`?\.?\s*/gi, '')
    .replace(/^function_call\s*:[^\n]*\n?/gim, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export function parseAiResponse(response: string): ParsedAiResponse {
  const buttons: string[] = [];
  const withoutBlocks = removeInternalBlocks(response);
  const markerPattern = /\[BUTTONS:\s*([\s\S]*?)\]/gi;
  const cleanText = withoutBlocks
    .replace(markerPattern, (_marker, content: string) => {
      buttons.push(...extractButtonLabels(content));
      return '';
    })
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

  return {
    cleanText: cleanText || EMPTY_AI_RESPONSE_TEXT,
    buttons,
  };
}
