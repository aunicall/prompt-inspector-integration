// # 运行测试
// node demo.js --api_key <your-api-key> --base_url <base-url> --text "test input"
 
// # 使用环境变量
// export PMTINSP_API_KEY=your-api-key
// node demo.js --base_url <base-url> --text "test input"

const { PromptInspector } = require("./nodejs/dist/index");

// Parse command line arguments
const args = process.argv.slice(2);
const params = {};

for (let i = 0; i < args.length; i += 2) {
  const key = args[i].replace(/^--/, "");
  const value = args[i + 1];
  params[key] = value;
}

if (!params.text) {
  console.error("Usage: node demo.js --api_key <api_key> --base_url <base_url> --text <text>");
  console.error("\nRequired arguments:");
  console.error("  --text      Text to detect");
  console.error("\nOptional arguments:");
  console.error("  --api_key   API key (or set PMTINSP_API_KEY env var)");
  console.error("  --base_url  Base URL (default: https://promptinspector.io)");
  process.exit(1);
}

async function main() {
  // Initialize the client
  const client = new PromptInspector({
    apiKey: params.api_key,
    baseUrl: params.base_url,
  });

  try {
    // Detect prompt injection
    const result = await client.detect(params.text);
    
    console.log("raw result:", result);
    console.log("-----------------------------------");
    console.log("is_safe:", result.isSafe);
    console.log("score:", result.score);
    console.log("category:", result.category);
    console.log("latency_ms:", result.latencyMs);
  } catch (error) {
    console.error("Error:", error.message);
    process.exit(1);
  } finally {
    // Close the client when done
    client.close();
  }
}

main();
