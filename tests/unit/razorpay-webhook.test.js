import { env, createExecutionContext, waitOnExecutionContext } from "cloudflare:test";
import { describe, it, expect, vi, afterEach } from "vitest";
import worker from "../../src/index.js";

const WEBHOOK_SECRET = "test-secret";

async function sign(body, secret) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(body));
  return Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function postWebhook(rawBody, signature) {
  return new Request("https://tickertruth.com/api/razorpay-webhook", {
    method: "POST",
    headers: { "X-Razorpay-Signature": signature ?? "" },
    body: rawBody,
  });
}

async function run(request) {
  const ctx = createExecutionContext();
  const res = await worker.fetch(request, { ...env, RAZORPAY_WEBHOOK_SECRET: WEBHOOK_SECRET }, ctx);
  await waitOnExecutionContext(ctx);
  return res;
}

describe("POST /api/razorpay-webhook", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("rejects a request with an invalid signature", async () => {
    const res = await run(postWebhook(JSON.stringify({ event: "payment_link.paid" }), "bogus"));
    expect(res.status).toBe(400);
    const json = await res.json();
    expect(json.error).toMatch(/invalid signature/i);
  });

  it("ignores events other than payment_link.paid", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const body = JSON.stringify({ event: "payment.captured" });
    const res = await run(postWebhook(body, await sign(body, WEBHOOK_SECRET)));

    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.received).toBe(true);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("notifies via Resend on a paid payment link", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "abc" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    const body = JSON.stringify({
      event: "payment_link.paid",
      payload: {
        payment_link: { entity: { id: "plink_1", description: "TickerTruth Professional plan" } },
        payment: { entity: { id: "pay_1", email: "buyer@example.com", contact: "+919999999999", amount: 500000 } },
      },
    });

    const res = await run(postWebhook(body, await sign(body, WEBHOOK_SECRET)));

    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.received).toBe(true);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [requestedUrl, options] = fetchSpy.mock.calls[0];
    expect(requestedUrl).toBe("https://api.resend.com/emails");
    const sentBody = JSON.parse(options.body);
    expect(sentBody.text).toContain("professional");
    expect(sentBody.text).toContain("buyer@example.com");
  });
});
