import { env, createExecutionContext, waitOnExecutionContext } from "cloudflare:test";
import { describe, it, expect, vi, afterEach } from "vitest";
import worker from "../../src/index.js";

function postContact(body, contentType = "application/json") {
  const fullBody = { "cf-turnstile-response": "test-token", ...body };
  const init =
    contentType === "application/json"
      ? { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(fullBody) }
      : { method: "POST", body: new URLSearchParams(fullBody) };
  return new Request("https://tickertruth.com/api/contact", init);
}

async function run(request) {
  const ctx = createExecutionContext();
  const res = await worker.fetch(request, env, ctx);
  await waitOnExecutionContext(ctx);
  return res;
}

const SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify";

function stubFetch({ turnstileSuccess = true, resendImpl } = {}) {
  const resendSpy =
    resendImpl || vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "abc" }), { status: 200 }));

  const fetchSpy = vi.fn((url, ...rest) => {
    if (String(url) === SITEVERIFY_URL) {
      return Promise.resolve(
        Response.json(
          turnstileSuccess
            ? { success: true, action: "contact", hostname: (env.TURNSTILE_HOSTNAMES || "").split(",")[0].trim() }
            : { success: false, "error-codes": ["invalid-input-response"] }
        )
      );
    }
    return resendSpy(url, ...rest);
  });

  vi.stubGlobal("fetch", fetchSpy);
  return { fetchSpy, resendSpy };
}

describe("POST /api/contact", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("rejects a submission missing name and email", async () => {
    stubFetch();
    const res = await run(postContact({ notes: "hi" }));
    expect(res.status).toBe(400);
    const json = await res.json();
    expect(json.success).toBe(false);
    expect(json.message).toMatch(/required/i);
  });

  it("rejects an invalid email address", async () => {
    stubFetch();
    const res = await run(postContact({ name: "Jane", email: "not-an-email" }));
    expect(res.status).toBe(400);
    const json = await res.json();
    expect(json.success).toBe(false);
    expect(json.message).toMatch(/valid email/i);
  });

  it("short-circuits honeypot submissions without calling Resend", async () => {
    const { resendSpy } = stubFetch({ resendImpl: vi.fn() });

    const res = await run(postContact({ name: "Bot", email: "bot@example.com", botcheck: "1" }));

    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.success).toBe(true);
    expect(resendSpy).not.toHaveBeenCalled();
  });

  it("sends a valid submission to Resend and returns success", async () => {
    const { resendSpy } = stubFetch();

    const res = await run(postContact({ name: "Jane Doe", email: "jane@example.com", notes: "Backtesting question" }));

    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.success).toBe(true);
    expect(resendSpy).toHaveBeenCalledTimes(1);
    const [requestedUrl, options] = resendSpy.mock.calls[0];
    expect(requestedUrl).toBe("https://api.resend.com/emails");
    const sentBody = JSON.parse(options.body);
    expect(sentBody.text).toContain("Jane Doe");
    expect(sentBody.text).toContain("jane@example.com");
  });

  it("returns a 500 with a fallback message when Resend fails", async () => {
    stubFetch({
      resendImpl: vi.fn().mockResolvedValue(new Response(JSON.stringify({ message: "bad" }), { status: 502 })),
    });

    const res = await run(postContact({ name: "Jane", email: "jane@example.com" }));

    expect(res.status).toBe(500);
    const json = await res.json();
    expect(json.success).toBe(false);
    expect(json.message).toMatch(/connect@tickertruth\.com/);
  });

  it("accepts form-encoded submissions, not just JSON", async () => {
    const { resendSpy } = stubFetch();

    const res = await run(postContact({ name: "Jane", email: "jane@example.com" }, "form"));

    expect(res.status).toBe(200);
    expect(resendSpy).toHaveBeenCalledTimes(1);
  });

  it("returns 403 and skips Resend when Turnstile verification fails", async () => {
    const { resendSpy } = stubFetch({ turnstileSuccess: false, resendImpl: vi.fn() });

    const res = await run(postContact({ name: "Jane", email: "jane@example.com" }));

    expect(res.status).toBe(403);
    const json = await res.json();
    expect(json.success).toBe(false);
    expect(resendSpy).not.toHaveBeenCalled();
  });

  it("returns 403 when the cf-turnstile-response token is missing", async () => {
    const { resendSpy } = stubFetch({ resendImpl: vi.fn() });

    const res = await run(postContact({ name: "Jane", email: "jane@example.com", "cf-turnstile-response": "" }));

    expect(res.status).toBe(403);
    expect(resendSpy).not.toHaveBeenCalled();
  });
});
