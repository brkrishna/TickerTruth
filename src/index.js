const CANONICAL_HOST = "tickertruth.com";

async function handleContact(request, env) {
  try {
    let body;
    const ct = request.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      body = await request.json();
    } else {
      const fd = await request.formData();
      body = Object.fromEntries(fd);
    }

    // Honeypot — bots fill this
    if (body.botcheck) {
      return Response.json({ success: true });
    }

    const name = (body.name || "").trim();
    const email = (body.email || "").trim();
    const phone = (body.phone || "").trim();
    const interest = (body.interest || "").trim();
    const notes = (body.notes || "").trim();

    if (!name || !email) {
      return Response.json(
        { success: false, message: "Name and email are required." },
        { status: 400 }
      );
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return Response.json(
        { success: false, message: "Please enter a valid email address." },
        { status: 400 }
      );
    }

    const lines = [
      "New inquiry from the TickerTruth contact form",
      "",
      `Name:     ${name}`,
      `Email:    ${email}`,
    ];
    if (phone) lines.push(`Phone:    ${phone}`);
    if (interest) lines.push(`Interest: ${interest}`);
    lines.push("", "Notes:", notes || "(none)");

    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: "TickerTruth Contact <noreply@tickertruth.com>",
        to: ["connect@tickertruth.com"],
        reply_to: `${name} <${email}>`,
        subject: `New Inquiry — TickerTruth (${name})`,
        text: lines.join("\n"),
      }),
    });

    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      console.error("Resend error:", res.status, JSON.stringify(errBody));
      throw new Error(`Resend ${res.status}: ${errBody.message || errBody.name || "unknown"}`);
    }

    return Response.json({ success: true });
  } catch (err) {
    console.error("contact form error:", err);
    return Response.json(
      { success: false, message: "Server error. Please email connect@tickertruth.com directly." },
      { status: 500 }
    );
  }
}

async function verifyRazorpaySignature(body, signature, secret) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(body));
  const hex = Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return hex === signature;
}

function extractTier(description) {
  const lower = description.toLowerCase();
  if (lower.includes("professional")) return "professional";
  if (lower.includes("starter")) return "starter";
  if (lower.includes("explorer")) return "explorer";
  return "unknown";
}

async function sendRazorpayNotification(env, { tier, email, contact, amountInr, paymentId, paymentLinkId }) {
  if (!env.RESEND_API_KEY) return;

  const body = [
    "Razorpay payment received — action required",
    "",
    `Tier:            ${tier}`,
    `Customer email:  ${email}`,
    `Customer phone:  ${contact}`,
    `Amount (INR):    ₹${amountInr}`,
    `Payment ID:      ${paymentId}`,
    `Payment Link ID: ${paymentLinkId}`,
    "",
    "Next steps:",
    "1. Run: python -c \"from pipelines.publish.access_manager import AccessManager; m=AccessManager(); m.create_buyer('<name>', '${email}', '${tier}')\"",
    "2. Generate signed R2 URL for the latest release bundle",
    "3. Email the signed URL to the customer",
  ].join("\n");

  await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: "TickerTruth Payments <noreply@tickertruth.com>",
      to: ["connect@tickertruth.com"],
      subject: `New Razorpay Subscription — ${tier} (${email})`,
      text: body,
    }),
  });
}

async function handleRazorpayWebhook(request, env) {
  const rawBody = await request.text();
  const signature = request.headers.get("X-Razorpay-Signature") || "";

  if (!env.RAZORPAY_WEBHOOK_SECRET) {
    return Response.json({ error: "webhook secret not configured" }, { status: 500 });
  }

  const valid = await verifyRazorpaySignature(rawBody, signature, env.RAZORPAY_WEBHOOK_SECRET);
  if (!valid) {
    return Response.json({ error: "invalid signature" }, { status: 400 });
  }

  let event;
  try {
    event = JSON.parse(rawBody);
  } catch {
    return Response.json({ error: "invalid JSON" }, { status: 400 });
  }

  if (event.event !== "payment_link.paid") {
    return Response.json({ received: true });
  }

  const pl = event.payload?.payment_link?.entity ?? {};
  const pay = event.payload?.payment?.entity ?? {};

  const tier = extractTier(pl.description ?? "");
  const amountInr = ((pay.amount ?? pl.amount ?? 0) / 100).toLocaleString("en-IN");
  const email = pay.email ?? "(not provided)";
  const contact = pay.contact ?? "(not provided)";
  const paymentId = pay.id ?? "—";
  const paymentLinkId = pl.id ?? "—";

  await sendRazorpayNotification(env, {
    tier,
    email,
    contact,
    amountInr,
    paymentId,
    paymentLinkId,
  });

  return Response.json({ received: true });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Canonical-host redirect (formerly a Pages _middleware.js)
    if (url.hostname !== CANONICAL_HOST && url.hostname.endsWith(".workers.dev")) {
      url.hostname = CANONICAL_HOST;
      url.protocol = "https:";
      return Response.redirect(url.toString(), 301);
    }

    if (url.pathname === "/api/contact" && request.method === "POST") {
      return handleContact(request, env);
    }

    if (url.pathname === "/api/razorpay-webhook" && request.method === "POST") {
      return handleRazorpayWebhook(request, env);
    }

    return env.ASSETS.fetch(request);
  },
};
