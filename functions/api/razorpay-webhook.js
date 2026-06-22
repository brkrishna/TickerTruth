/**
 * Razorpay webhook handler — payment_link.paid
 *
 * Env vars required (set in Cloudflare Pages → Settings → Environment variables):
 *   RAZORPAY_WEBHOOK_SECRET  — from Razorpay Dashboard → Settings → Webhooks
 *   RESEND_API_KEY           — already configured for contact form
 *
 * On a successful payment this handler emails connect@tickertruth.com so
 * you can manually run AccessManager.create_buyer() and send the signed R2 URL.
 */

export async function onRequestPost({ request, env }) {
  const rawBody = await request.text();
  const signature = request.headers.get("X-Razorpay-Signature") || "";

  if (!env.RAZORPAY_WEBHOOK_SECRET) {
    return Response.json({ error: "webhook secret not configured" }, { status: 500 });
  }

  const valid = await verifySignature(rawBody, signature, env.RAZORPAY_WEBHOOK_SECRET);
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

  await sendNotification(env, {
    tier,
    email,
    contact,
    amountInr,
    paymentId,
    paymentLinkId,
  });

  return Response.json({ received: true });
}

async function verifySignature(body, signature, secret) {
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

async function sendNotification(env, { tier, email, contact, amountInr, paymentId, paymentLinkId }) {
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
