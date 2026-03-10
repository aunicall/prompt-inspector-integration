/**
 * Prompt Inspector SDK client.
 *
 * Provides the main PromptInspector class for interacting with the
 * Prompt Inspector API detection service.
 */

import * as http from "http";
import * as https from "https";
import { URL } from "url";

import {
  PromptInspectorError,
  AuthenticationError,
  ValidationError,
  APIError,
  TimeoutError,
  ConnectionError,
} from "./errors";
import {
  PromptInspectorOptions,
  DetectOptions,
  DetectionResult,
} from "./types";

const DEFAULT_BASE_URL = "https://promptinspector.io";
const DEFAULT_TIMEOUT = 30;

/**
 * Client for the Prompt Inspector prompt injection detection service.
 *
 * @example
 * ```typescript
 * import { PromptInspector } from "prompt-inspector";
 *
 * const client = new PromptInspector({
 *   apiKey: "your-api-key",
 * });
 *
 * const result = await client.detect("some user input");
 * console.log(result.isSafe);
 *
 * client.close();
 * ```
 */
export class PromptInspector {
  private readonly apiKey: string;
  private readonly baseUrl: string;
  private readonly timeout: number;
  private readonly detectUrl: string;
  private closed: boolean = false;

  /**
   * Create a new PromptInspector client.
   *
   * @param options - Configuration options.
   * @throws {AuthenticationError} If no API key is found.
   */
  constructor(options: PromptInspectorOptions = {}) {
    // Resolve API key: explicit param > env var
    let resolvedKey = options.apiKey;
    if (!resolvedKey) {
      resolvedKey = process.env.PMTINSP_API_KEY;
    }
    if (!resolvedKey) {
      throw new AuthenticationError(
        "API key is required. Provide it via the 'apiKey' option " +
          "or set the PMTINSP_API_KEY environment variable."
      );
    }

    this.apiKey = resolvedKey;
    this.baseUrl = (options.baseUrl || DEFAULT_BASE_URL).replace(/\/+$/, "");
    this.timeout = options.timeout ?? DEFAULT_TIMEOUT;
    this.detectUrl = `${this.baseUrl}/api/v1/detect/sdk`;
  }

  /**
   * Detect potential prompt injection in the given text.
   *
   * @param text - The text to analyse (required, non-empty string).
   * @param options - Optional per-request settings.
   * @returns A promise that resolves to a DetectionResult.
   * @throws {ValidationError} If the input text is invalid.
   * @throws {AuthenticationError} If the API key is rejected.
   * @throws {APIError} If the API returns an error response.
   * @throws {TimeoutError} If the request exceeds the timeout.
   * @throws {ConnectionError} If a connection cannot be established.
   */
  async detect(
    text: string,
    options?: DetectOptions
  ): Promise<DetectionResult> {
    this.ensureOpen();

    // Validate input
    if (!text || typeof text !== "string" || !text.trim()) {
      throw new ValidationError(
        "Parameter 'text' is required and must be a non-empty string."
      );
    }

    const requestTimeout = options?.timeout ?? this.timeout;
    const body = JSON.stringify({ input_text: text });

    return this.request(body, requestTimeout);
  }

  /**
   * Close the SDK client and release all associated resources.
   * After calling close(), the client instance can no longer be used.
   */
  close(): void {
    this.closed = true;
  }

  // ------------------------------------------------------------------
  // Internal helpers
  // ------------------------------------------------------------------

  private ensureOpen(): void {
    if (this.closed) {
      throw new PromptInspectorError(
        "This PromptInspector client has been closed. " +
          "Create a new instance to continue making requests."
      );
    }
  }

  private request(
    body: string,
    timeoutSec: number
  ): Promise<DetectionResult> {
    return new Promise<DetectionResult>((resolve, reject) => {
      const url = new URL(this.detectUrl);
      const isHttps = url.protocol === "https:";
      const transport = isHttps ? https : http;

      const reqOptions: http.RequestOptions = {
        method: "POST",
        hostname: url.hostname,
        port: url.port || (isHttps ? 443 : 80),
        path: url.pathname + url.search,
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(body),
          "X-App-Key": this.apiKey,
        },
        timeout: timeoutSec * 1000,
      };

      const req = transport.request(reqOptions, (res) => {
        const chunks: Buffer[] = [];

        res.on("data", (chunk: Buffer) => {
          chunks.push(chunk);
        });

        res.on("end", () => {
          const rawBody = Buffer.concat(chunks).toString("utf-8");
          const statusCode = res.statusCode || 0;

          try {
            if (statusCode === 200) {
              const data = JSON.parse(rawBody);
              const result = data.result || {};
              resolve({
                requestId: data.request_id || "",
                isSafe: result.is_safe ?? true,
                score: result.score ?? null,
                category: result.category || [],
                latencyMs: data.latency_ms || 0,
              });
              return;
            }

            // Handle known error codes
            if (statusCode === 401 || statusCode === 403) {
              reject(
                new AuthenticationError(
                  "Authentication failed. Please verify your API key and appId."
                )
              );
              return;
            }

            if (statusCode === 413) {
              reject(
                new ValidationError(
                  "The input text exceeds the maximum allowed length for your plan."
                )
              );
              return;
            }

            if (statusCode === 422) {
              let detail = "";
              try {
                const parsed = JSON.parse(rawBody);
                detail = String(parsed.detail || "");
              } catch {
                // ignore parse error
              }
              reject(
                new ValidationError(
                  `Invalid request parameters. ${detail}`.trim()
                )
              );
              return;
            }

            if (statusCode === 429) {
              reject(
                new APIError(
                  429,
                  "Rate limit exceeded. Please reduce your request frequency."
                )
              );
              return;
            }

            // Generic error
            let detail = "";
            try {
              const parsed = JSON.parse(rawBody);
              detail = String(parsed.detail || "");
            } catch {
              detail = rawBody.slice(0, 200);
            }

            reject(
              new APIError(
                statusCode,
                detail || `Unexpected error (HTTP ${statusCode}).`
              )
            );
          } catch (err) {
            reject(
              new PromptInspectorError(
                `Failed to parse API response: ${String(err)}`
              )
            );
          }
        });
      });

      req.on("timeout", () => {
        req.destroy();
        reject(new TimeoutError(timeoutSec));
      });

      req.on("error", (err: NodeJS.ErrnoException) => {
        if (err.code === "ECONNREFUSED" || err.code === "ENOTFOUND") {
          reject(
            new ConnectionError(
              `Failed to connect to the Prompt Inspector API at ${this.baseUrl}. ` +
                "Please check the baseUrl and your network connection."
            )
          );
        } else if (
          err.message.includes("ETIMEDOUT") ||
          err.message.includes("timeout")
        ) {
          reject(new TimeoutError(timeoutSec));
        } else {
          reject(new ConnectionError(`HTTP error occurred: ${err.message}`));
        }
      });

      req.write(body);
      req.end();
    });
  }
}
