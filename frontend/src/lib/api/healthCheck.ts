/**
 * Health check utility to verify backend connectivity
 */

export async function checkBackendHealth(
  baseUrl: string = "http://localhost:8000",
): Promise<{
  reachable: boolean;
  error?: string;
  status?: number;
}> {
  try {
    const response = await fetch(`${baseUrl}/docs`, {
      method: "GET",
      credentials: "include",
      // Add timeout
      signal: AbortSignal.timeout(5000),
    });

    return {
      reachable: response.ok || response.status < 500,
      status: response.status,
    };
  } catch (error) {
    return {
      reachable: false,
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}

/**
 * Check backend health and log results (for debugging)
 */
export async function debugBackendConnection(): Promise<void> {
  const urls = [
    "http://localhost:8000",
    "http://backend:8000",
    process.env.NEXT_PUBLIC_API_URL || "not set",
  ];

  console.log("=== Backend Connection Check ===");
  for (const url of urls) {
    if (url === "not set") continue;
    const result = await checkBackendHealth(url);
    console.log(
      `${url}: ${result.reachable ? "✓ Reachable" : "✗ Unreachable"}`,
      result,
    );
  }
  console.log("===============================");
}
