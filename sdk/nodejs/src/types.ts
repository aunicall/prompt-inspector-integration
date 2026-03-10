/**
 * Data types for the Prompt Inspector SDK.
 */

/**
 * Configuration options for the PromptInspector client.
 */
export interface PromptInspectorOptions {
  /** API key for authentication. Falls back to PMTINSP_API_KEY env var. */
  apiKey?: string;
  /** API server base URL. Defaults to https://promptinspector.io. */
  baseUrl?: string;
  /** Default request timeout in seconds. Defaults to 30. */
  timeout?: number;
}

/**
 * Options for a single detect() call.
 */
export interface DetectOptions {
  /** Per-request timeout override in seconds. */
  timeout?: number;
}

/**
 * Result of a prompt injection detection.
 */
export interface DetectionResult {
  /** Unique identifier for this detection request. */
  requestId: string;
  /** Whether the input text is considered safe. */
  isSafe: boolean;
  /** Risk score (0-1). null when no threat is detected. */
  score: number | null;
  /** List of detected threat categories. */
  category: string[];
  /** Server-side processing time in milliseconds. */
  latencyMs: number;
}
