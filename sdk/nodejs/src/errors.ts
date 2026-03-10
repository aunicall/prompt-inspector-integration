/**
 * Custom error classes for the Prompt Inspector SDK.
 */

/**
 * Base error class for all Prompt Inspector SDK errors.
 */
export class PromptInspectorError extends Error {
  constructor(message: string = "An unexpected error occurred.") {
    super(message);
    this.name = "PromptInspectorError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/**
 * Raised when authentication fails (invalid or missing API key).
 */
export class AuthenticationError extends PromptInspectorError {
  constructor(
    message: string = "Authentication failed. Please check your API key."
  ) {
    super(message);
    this.name = "AuthenticationError";
  }
}

/**
 * Raised when input validation fails.
 */
export class ValidationError extends PromptInspectorError {
  constructor(message: string = "Input validation failed.") {
    super(message);
    this.name = "ValidationError";
  }
}

/**
 * Raised when the API returns an error response.
 */
export class APIError extends PromptInspectorError {
  public readonly statusCode: number;

  constructor(statusCode: number, message: string = "API request failed.") {
    super(`[HTTP ${statusCode}] ${message}`);
    this.name = "APIError";
    this.statusCode = statusCode;
  }
}

/**
 * Raised when a request exceeds the timeout duration.
 */
export class TimeoutError extends PromptInspectorError {
  constructor(timeout: number) {
    super(`Request timed out after ${timeout} seconds.`);
    this.name = "TimeoutError";
  }
}

/**
 * Raised when a connection to the API server cannot be established.
 */
export class ConnectionError extends PromptInspectorError {
  constructor(
    message: string = "Failed to connect to the Prompt Inspector API server."
  ) {
    super(message);
    this.name = "ConnectionError";
  }
}
