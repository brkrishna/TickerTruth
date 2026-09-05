# Payment Collection Setup

Revenue blocker per `marketing.md` §0 — do not start outreach until this is
done. Two providers: Razorpay for India (INR, UPI), Stripe for
international (USD, card). Both are payment-link based — no checkout page
build needed.

**Status (2026-08-19): Razorpay is live — account, KYC, payment links, and
test payment all confirmed done by the user, and the buy buttons are wired
into `pricing.html`. Stripe is skipped entirely — Stripe does not support
India-based business signups, so there's no USD path via Stripe. If
international billing is ever needed, revisit with a provider that
supports Indian merchants (e.g. Razorpay's own international payment
methods, or Paddle/Lemon Squeezy as merchant-of-record).**

**Note:** the live `pricing.html` uses a different scheme than §1/§3 below
describe — three tiers (Starter INR 14,999/mo, Professional INR
39,999/mo, Enterprise INR 1.5 lakh+/mo) with a Razorpay "Subscribe" button
per tier, not the "Founding Starter INR 10,000 / Standard INR 15,000"
two-tier founding-slot plan this doc was originally written against. No
founding-slot counter and no Calendly link exist on `pricing.html` today
— see the checklist below.

---

## 1. Razorpay (India — INR + UPI)

1. Create an account at [razorpay.com](https://razorpay.com). Sign up with
   the business email, not a personal one.
2. Complete KYC: PAN card, bank account details (IFSC + account number),
   business category ("Software/SaaS" or "Data Services"). **Submit this
   first** — approval takes 1–2 business days and blocks everything below.
3. While waiting on KYC approval, prepare the payment link details:
   - **Founding Starter** — INR 10,000/month, recurring, 12-month
     commitment note in the description.
   - **Standard Starter** — INR 15,000/month, recurring.
4. Once approved: Dashboard → Payment Links → Create → Recurring.
   - Set billing cycle: monthly.
   - Enable UPI, cards, and netbanking as accepted methods (default is
     usually all three — confirm).
   - Description field: "TickerTruth Starter — founding customer pricing,
     locked 12 months" (or the standard-tier equivalent).
5. Copy both payment link URLs — you'll need them for the pricing page CTA
   (§3 below) and for outreach templates in `marketing.md` §7.
6. **Test end-to-end** with Razorpay's test mode card before going live:
   confirm the link loads, accepts a test payment, and the dashboard shows
   the transaction.

---

## 2. Stripe (international — USD, card)

1. Create an account at [stripe.com](https://stripe.com). No KYC delay for
   basic payment links — you can start immediately, though full payout
   activation may still require identity verification.
2. Dashboard → Payment Links → Create → Recurring.
   - **Founding Starter** — $120/month (USD equivalent of INR 10,000 at
     ~₹83/$; round to a clean number, don't chase the exact FX rate).
   - **Standard Starter** — $180/month.
3. Copy both payment link URLs.
4. **Test end-to-end** using Stripe's test card `4242 4242 4242 4242` in
   test mode before switching to live mode.

---

## 3. Wire Links into the Pricing Page

- Add a "Buy now" button on the Starter tier card in
  `website/public/pricing.html`, linking to the Razorpay founding
  payment link by default (primary INR audience).
- Add a smaller "Paying in USD?" link near it pointing to the Stripe link.
- Add a founding-slot counter next to the button: "X of 5 founding slots
  available at INR 10,000/month" — update this number manually as slots
  fill; there's no automation for it yet.
- Add a secondary "Book a 20-min call first" link below the buy button,
  pointing to the Calendly event (already live:
  https://calendly.com/ramkybodi/30min).

---

## 4. After a Payment Comes In

This isn't automated yet (see `docs/onboarding.md` §3–5 for the manual
buyer-creation and delivery flow). Once a payment lands:

1. Create the buyer record (`AccessManager.create_buyer`, per
   `docs/onboarding.md` §3) with the tier and payment reference.
2. Send `docs/subscriber-onboarding.md` as a PDF, per the first-release
   email flow already documented there.
3. Log the payment reference in the buyer's `notes` field so it's
   reconcilable against the Razorpay/Stripe dashboard later.

**Not built yet, tracked as future work, not a blocker for first
customer:** webhook-based auto-provisioning (`docs/onboarding.md` §4 calls
this out as "Planned: Razorpay webhook integration in Phase 6"). Manual
process is fine for the first 5–10 customers.

---

## Checklist

- [x] Razorpay account created, KYC approved (2026-08-19)
- [x] Razorpay payment links created — live links are per-tier (Starter,
      Professional), not the founding/standard split originally planned
- [x] Razorpay test payment confirmed end-to-end
- [x] Buy-now buttons live on `pricing.html` (`.btn-pay-rzp`, one per tier)
- [x] ~~Stripe~~ — skipped. Stripe does not support India-based business
      signups; no USD path exists via Stripe. Not pursuing an alternative
      unless international demand actually shows up.
- [x] Decided 2026-08-19: revive founding-slot framing — INR 10,000/mo
      (vs INR 14,999 standard Starter rate), 5 slots, on the Starter tier
      only.
- [x] Founding-offer block + slot counter added to `pricing.html`
      (2026-08-19), wired to the real founding-rate Razorpay link:
      https://rzp.io/rzp/u2MmrcZ4 (INR 10,000/mo, 5 slots, expiry set in
      Razorpay per the user).
- [ ] Update the slot counter manually as subscribers come in — no
      automation for this. Remove the founding-offer block entirely once
      5 slots fill or the link's Razorpay expiry date passes, whichever
      comes first.
- [x] Founding link's payment flow verified end-to-end (2026-08-19) —
      recreated the same recurring/amount/description setup as a Test
      Mode link and confirmed a successful test payment. (Test Mode
      cards can't touch a live link directly, so this validates the
      mechanics rather than `u2MmrcZ4` itself; see payment-setup.md
      discussion if a live+refund check is ever wanted instead.)
- [x] Calendly link on `pricing.html` — added 2026-08-19, "Or book a
      20-min call first" under the Starter and Professional buy buttons,
      pointing to https://calendly.com/ramkybodi/30min.
