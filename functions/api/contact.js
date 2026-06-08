export async function onRequestPost({ request, env }) {
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

    const name     = (body.name     || "").trim();
    const email    = (body.email    || "").trim();
    const phone    = (body.phone    || "").trim();
    const interest = (body.interest || "").trim();
    const notes    = (body.notes    || "").trim();

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
    if (phone)    lines.push(`Phone:    ${phone}`);
    if (interest) lines.push(`Interest: ${interest}`);
    lines.push("", "Notes:", notes || "(none)");

    await env.SEND_EMAIL.send({
      from: "noreply@tickertruth.com",
      to: "connect@tickertruth.com",
      subject: `New Inquiry — TickerTruth (${name})`,
      text: lines.join("\n"),
    });

    return Response.json({ success: true });
  } catch (err) {
    console.error("contact form error:", err);
    return Response.json(
      { success: false, message: "Server error. Please email connect@tickertruth.com directly." },
      { status: 500 }
    );
  }
}
