# Payment Collection Setup

Revenue blocker per `marketing.md` §0 — do not start outreach until this is
done. Two providers: Razorpay for India (INR, UPI), Stripe for
international (USD, card). Both are payment-link based — no checkout page
build needed.

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
  `website/landing-page/pricing.html`, linking to the Razorpay founding
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

- [ ] Razorpay account created, KYC submitted
- [ ] Razorpay KYC approved
- [ ] Razorpay Founding Starter payment link created (INR 10,000/month)
- [ ] Razorpay Standard Starter payment link created (INR 15,000/month)
- [ ] Razorpay test payment confirmed end-to-end
- [ ] Stripe account created
- [ ] Stripe Founding Starter payment link created ($120/month)
- [ ] Stripe Standard Starter payment link created ($180/month)
- [ ] Stripe test payment confirmed end-to-end
- [ ] Buy-now button + founding-slot counter live on `pricing.html`
- [ ] Calendly link confirmed present on pricing page (already live
      elsewhere — verify it's also on `/pricing`, not just LinkedIn/posts)
