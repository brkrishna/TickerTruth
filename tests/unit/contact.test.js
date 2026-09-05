import { env, createExecutionContext, waitOnExecutionContext } from "cloudflare:test";
import { describe, it, expect, vi, afterEach } from "vitest";
import worker from "../../src/index.js";

function postContact(body, contentType = "application/json") {
  const init =
    contentType === "application/json"
      ? { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) }
      : { method: "POST", body: new URLSearchParams(body) };
  return new Request("https://tickertruth.com/api/contact", init);
}

async function run(request) {
  const ctx = createExecutionContext();
  const res = await worker.fetch(request, env, ctx);
  await waitOnExecutionContext(ctx);
  return res;
}

describe("POST /api/contact", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("rejects a submission missing name and email", async () => {
    const res = await run(postContact({ notes: "hi" }));
    expect(res.status).toBe(400);
    const json = await res.json();
    expect(json.success).toBe(false);
    expect(json.message).toMatch(/required/i);
  });

  it("rejects an invalid email address", async () => {
    const res = await run(postContact({ name: "Jane", email: "not-an-email" }));
    expect(res.status).toBe(400);
    const json = await res.json();
    expect(json.success).toBe(false);
    expect(json.message).toMatch(/valid email/i);
  });

  it("short-circuits honeypot submissions without calling Resend", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const res = await run(postContact({ name: "Bot", email: "bot@example.com", botcheck: "1" }));

    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.success).toBe(true);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("sends a valid submission to Resend and returns success", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "abc" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    const res = await run(postContact({ name: "Jane Doe", email: "jane@example.com", notes: "Backtesting question" }));

    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.success).toBe(true);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [requestedUrl, options] = fetchSpy.mock.calls[0];
    expect(requestedUrl).toBe("https://api.resend.com/emails");
    const sentBody = JSON.parse(options.body);
    expect(sentBody.text).toContain("Jane Doe");
    expect(sentBody.text).toContain("jane@example.com");
  });

  it("returns a 500 with a fallback message when Resend fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ message: "bad" }), { status: 502 })));

    const res = await run(postContact({ name: "Jane", email: "jane@example.com" }));

    expect(res.status).toBe(500);
    const json = await res.json();
    expect(json.success).toBe(false);
    expect(json.message).toMatch(/connect@tickertruth\.com/);
  });

  it("accepts form-encoded submissions, not just JSON", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "abc" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchSpy);

    const res = await run(postContact({ name: "Jane", email: "jane@example.com" }, "form"));

    expect(res.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });
});
