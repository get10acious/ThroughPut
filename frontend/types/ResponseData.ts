import { ChatMessage } from "./ChatMessage";

export interface ResponseData {
  type: string;
  sessionId?: string;
  id?: string;
  textResponse?: string;
  isComplete?: boolean;
  chatHistory?: ChatMessage[];
  inputTokenCount?: number;
  outputTokenCount?: number;
  elapsedTime?: number;
}
