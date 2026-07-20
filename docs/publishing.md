# Blog Publishing Guide

Two people are involved in getting a blog post live:

- **Content Creator** — writes the post, saves it to a shared space, and
  submits it for review. No git commands, no terminal.
- **Approver** — reviews the submission and is the only person who can make
  it go live. This is enforced by GitHub itself, not just by convention
  (Section 0, and verified live in Section 0.1).

If you're the Content Creator, you need **Section 1** only. Everything
after that is the Approver's job.

---

## 0. The Gate

This repo's `main` branch is configured so that **no post can go live
without the Approver's explicit approval** — even though the Content
Creator has push access to GitHub.

- A shared branch called `drafts` is where the Content Creator's posts
  land. Nothing on `drafts` is public; it never touches the live site by
  itself.
- Publishing a post means merging `drafts` into `main` through a Pull
  Request (PR). GitHub branch protection on `main` requires **at least one
  approving review from someone other than whoever opened the PR** before
  the merge button will work.
- The Approver is exempt from needing a *second* approver, so once they've
  reviewed a PR, they can merge it solo.

### 0.1 Verified behavior (not just configuration — actually tested)

Two things were tested directly against this repo before writing this doc,
because they're easy to get backwards:

1. **A PR author cannot approve their own PR.** GitHub rejects it outright
   with `Can not approve your own pull request`. This means **the Content
   Creator must be the one who opens the PR** (Section 1, Step 3) — if the
   Approver opens it instead, the Approver becomes the "author" and can't
   approve their own submission either, and would need to force an override.
2. **Without an approval, the merge is flatly refused:**
   `Pull request #2 is not mergeable: the base branch policy prohibits the
   merge.` Even a repo admin needs to explicitly pass an override flag to
   bypass it — a normal merge attempt just fails.

Both were confirmed with a real throwaway PR against this repo, then
cleaned up (closed unmerged, test file removed) before writing this guide.

---

## 1. For the Content Creator

### 1.1 One-time setup

You'll do this once, together with the Approver, before writing your first post.

**Step 1 — Get a GitHub account.**
If you don't already have one, go to [github.com/join](https://github.com/join)
and create a free account with your email. You won't need to learn GitHub
itself — this account is just your login.

**Step 2 — Accept the collaborator invite.**
The Approver will send you an invitation by email (from GitHub) to join
the `TickerTruth` repository. Open the email and click **Accept invitation**.

**Step 3 — Sign in to StackEdit with that GitHub account.**
1. Go to [stackedit.io/app](https://stackedit.io/app).
2. Open the menu (☰ icon, top-left).
3. Click **Synchronize → Sign in with GitHub**.
4. GitHub will ask you to authorize "StackEdit" to access your account —
   click **Authorize**. This is the same one-click consent screen you'd see
   for any app that connects to GitHub.

**Step 4 — Connect the shared posts folder (do this together with the Approver).**
1. In the StackEdit sidebar, click the workspace icon — a `#` symbol,
   top-right of the sidebar.
2. Click **Add a workspace**.
3. Choose **GitHub**.
4. Fill in:
   - **Repository:** `brkrishna/TickerTruth`
   - **Branch:** `drafts`
   - **Folder / path:** `website/blog/content/posts`
5. Confirm. The StackEdit sidebar will now show a folder containing the
   two posts that already exist (`welcome-to-the-tickertruth-blog.md` and
   an index file) — if you see those, it's connected correctly.

That's the entire one-time setup. From now on, every time you open
[stackedit.io/app](https://stackedit.io/app), this folder is already there.

> If any menu names above look slightly different (StackEdit updates its
> UI from time to time), look for **Synchronize** and **workspace** in the
> main menu — the underlying idea (pick a GitHub repo, branch, and folder)
> doesn't change.

### 1.2 Writing and submitting a post (every time)

**Step 1 — Open a new file.**
1. Go to [stackedit.io/app](https://stackedit.io/app) — the shared folder
   from setup should already be open in the sidebar.
2. Click **New file** (a `+` icon at the top of the sidebar, inside that
   folder — make sure you're creating it *inside* the shared folder, not
   elsewhere).
3. Name it after your post title: all lowercase, words separated by
   dashes, ending in `.md`. Example: a post titled "Why Corporate Actions
   Matter" becomes `why-corporate-actions-matter.md`.

**Step 2 — Fill in the template.**
Copy this block into the very top of the file, and fill in the four lines
marked `REPLACE`. Don't change anything else about this block, including
the `---` lines:

```
---
title: "REPLACE WITH YOUR POST TITLE"
date: 2026-07-20
description: "REPLACE: one sentence describing what the post is about"
tags: ["REPLACE-topic-one", "REPLACE-topic-two"]
---
```

- **date** — always use **today's date**, format `YYYY-MM-DD`, even if the
  post discusses something from the past or something planned for later.
  A future date makes the post invisible once published — no error, it
  just silently doesn't appear. The Approver double-checks this too, but
  getting it right the first time saves a round trip.
- **tags** — one or two short topic words, lowercase, in quotes, separated
  by a comma. Example: `["dividends", "data-quality"]`.

**Step 3 — Write the post.**
Below that block, write in plain text:
- Leave a blank line between paragraphs.
- Put `##` and a space before a line to make it a section heading.
- Wrap a word in `**two asterisks**` to make it **bold**.
- That's all that's required — plain sentences and paragraphs work fine.

**Step 4 — Save it to the shared folder.**
StackEdit auto-saves your work in your browser as you type, but that's
*local only* — it isn't shared with anyone yet. To actually put it in the
shared folder on GitHub:
1. Open the menu (☰) → **Synchronize → Synchronize now**.
   (StackEdit also does this automatically about once a minute, but don't
   rely on the wait — click it yourself when you're ready to submit.)
2. You should see a brief confirmation with no error message. If you see a
   conflict or error message, stop and message the Approver — don't retry
   repeatedly.

**Step 5 — Submit it for review.**
This is the only GitHub-flavored step, and it's a single click:
1. Open this link: **[github.com/brkrishna/TickerTruth/pull/new/drafts](https://github.com/brkrishna/TickerTruth/pull/new/drafts)**
2. GitHub will show you a page comparing `drafts` against `main` — you'll
   see your new post listed as an added file. You don't need to check
   anything here.
3. Type a short title in the box, for example: `blog: <your post title>`.
4. Click the green **Create pull request** button.
5. Message the Approver: *"PR is up for `<your post title>`."*

That's the entire submission — you're done. The Approver takes it from
here (Section 2). Nothing you've done so far makes the post public.

**A few things to avoid:**
- Don't rename or delete other files in the shared folder.
- Don't edit a post that's still awaiting review from someone else.
- If you're revising a post you started earlier, open that same file again
  rather than creating a new one — and repeat Steps 4–5 to submit the update.

---

## 2. For the Approver — Reviewing, Approving, Publishing

You'll get a message from the Content Creator with a PR title (or a direct
link). Everything below happens on that PR.

### Step 1 — Find the PR

```bash
gh pr list --state open
```

Or open `https://github.com/brkrishna/TickerTruth/pulls` in a browser.

### Step 2 — Wait for the checks

Four automated checks run on every PR and must all go green before you
review the content:

| Check | What it verifies |
|---|---|
| `Lint` | Python pipeline lint (unaffected by blog-only posts, runs anyway) |
| `Blog Build Check` | The post's front matter and Markdown build without error |
| `Unit Tests` | Full pipeline test suite (unaffected, runs anyway) |
| `Cloudflare Pages` | Full site build + a live preview deployment |

```bash
gh pr checks <pr-number>
```

### Step 3 — Review the live preview

A Cloudflare bot comments on the PR with a **Preview URL**
(`https://<hash>.tickertruth.pages.dev`) within ~30–60 seconds of the checks
finishing. Open it and check:

- [ ] Post renders at `/blog/posts/<slug>/` with the right title, date, tags
- [ ] `date` is today or earlier — not in the future
- [ ] No broken links, obvious typos, or formatting issues
- [ ] Post shows up on the blog home page and its tag pages
- [ ] Existing site pages (pricing, methodology, etc.) are unaffected

### Step 4 — Approve

```bash
gh pr review <pr-number> --approve
```

Or on the PR page: **Files changed** tab → **Review changes** → select
**Approve** → **Submit review**.

This only works because the Content Creator opened the PR (Section 0.1) —
if you try to approve a PR you opened yourself, GitHub refuses.

### Step 5 — Merge (this is the publish step)

```bash
gh pr merge <pr-number> --squash
```

Or click the green **Squash and merge** button on the PR page. This is the
gate from Section 0: without Step 4's approval, this button/command is
blocked. Merging triggers an automatic Cloudflare Pages production deploy,
usually live within a minute.

### Step 6 — Confirm it's live

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://tickertruth.com/blog/posts/<slug>/
```

Expect `200`.

### Step 7 — Hand off for cross-posting

Send the Content Creator the live URL. Section 3 covers cross-posting to
Substack, Medium, and LinkedIn — the Content Creator can do this
themselves (it's just copy-pasting text into each platform), or you can.

---

## 3. Cross-Posting: Substack, Medium, LinkedIn

Once a post is live, every cross-post should link back to it — this
protects SEO and drives traffic back to the main site.

### Blurb template

```
<Hook — one sentence, the specific problem or interesting fact>
<One sentence of context or what the post covers>
Read the full post: <live post URL>
<3–5 hashtags>
```

### Substack

1. **New post** → paste the intro blurb as the opening, then either stop
   there and add "Read the full post on the TickerTruth blog →
   `<live post URL>`", or paste the full post text and set the official
   link under **Settings → SEO → Canonical URL**.
2. Add 2–3 relevant topics in the post settings. Substack doesn't use
   `#hashtags` in the post body itself.

### Medium

1. From your Medium profile, use **Import a story**:
   [medium.com/p/import](https://medium.com/p/import).
2. Paste the live post URL — Medium pulls in the title, text, and images,
   and automatically links back to the source.
3. Add a short intro line and 3–5 tags in Medium's tag field.

### LinkedIn

1. **Start a post** (a normal feed post, not a LinkedIn Article).
2. Paste the blurb — keep it under ~1,300 characters so it doesn't get
   truncated behind "see more."
3. Paste the live URL on its own line at the end — LinkedIn will show a
   preview card for it automatically.
4. Add 3–5 hashtags at the very end, e.g.
   `#QuantFinance #AlgoTrading #NSEIndia #BacktestData #FinTech`.

---

## 4. Worked Example: "The Silent Symbol Swap"

### 4.1 — Content Creator writes and submits the post

File created in StackEdit: `why-corporate-actions-matter.md` → renamed in
this example to match its content, `silent-symbol-swap.md`:

```markdown
---
title: "The Silent Symbol Swap: When NSE Reuses a Ticker"
date: 2026-07-20
description: "NSE has reused ticker symbols across unrelated companies more than once. Here's how that breaks a naive backtest, and how symbol lineage catches it."
tags: ["symbol-lineage", "data-quality"]
---

Most backtesting code joins price history to a strategy signal on the ticker
symbol. That works fine — right up until NSE reuses a symbol for a
completely unrelated company after the original one delists.

It's rarer than a rename, but it happens: a company delists, and years
later NSE issues the same alphanumeric symbol to a new, unrelated listing.
If your price history is keyed on symbol alone, your backtest silently
splices two different companies' price series together at the boundary
date. The join succeeds. The numbers look plausible. Nothing errors.

## How lineage catches it

TickerTruth resolves every price row to a `security_id` — a surrogate key
tied to a specific listing, not a symbol string — before any adjustment or
backtest logic runs. Symbol reuse shows up as two separate lineage events
with a gap between them, and our lineage rules flag it explicitly rather
than silently treating it as one continuous history.

## The takeaway

If you're joining on raw ticker strings anywhere in your pipeline, a symbol
reuse event will corrupt that join without raising an error. Use a stable
surrogate ID, and treat the symbol as a time-bound alias, not an identity.
```

Then, in StackEdit: menu → **Synchronize → Synchronize now**.

Then, in a browser: open
[github.com/brkrishna/TickerTruth/pull/new/drafts](https://github.com/brkrishna/TickerTruth/pull/new/drafts),
title it `blog: the silent symbol swap`, click **Create pull request**.

Message to Approver: *"PR is up for The Silent Symbol Swap."*

### 4.2 — Approver publishes it

```bash
gh pr list --state open
# find the PR number

gh pr checks <pr-number>
# wait for all 4 to go green

# open the Cloudflare preview URL from the bot comment, confirm it renders
# and the date isn't in the future

gh pr review <pr-number> --approve
gh pr merge <pr-number> --squash

curl -s -o /dev/null -w "%{http_code}\n" \
  https://tickertruth.com/blog/posts/silent-symbol-swap/
# 200
```

### 4.3 — Cross-post blurb

Live URL: `https://tickertruth.com/blog/posts/silent-symbol-swap/`

**Substack:**
> NSE has reused a ticker symbol for a completely unrelated company before — and if your backtest joins price history on the raw symbol string, that reuse silently splices two companies' price series together at the boundary. No error, no warning, just a wrong number that looks plausible.
>
> We walk through how symbol lineage resolution catches this, and why the fix is never keying on the ticker string in the first place.
>
> Read the full post on the TickerTruth blog → https://tickertruth.com/blog/posts/silent-symbol-swap/

**Medium:** import via `https://tickertruth.com/blog/posts/silent-symbol-swap/`, tags: `Quantitative Finance`, `Backtesting`, `Data Engineering`, `Indian Stock Market`, `Fintech`.

**LinkedIn:**
> NSE has reused a ticker symbol for a completely unrelated company before.
>
> If your backtest pipeline joins price history on the raw symbol string — not a stable security ID — that kind of reuse silently splices two unrelated companies' price series together at the boundary date. The join succeeds. The Sharpe ratio looks fine. Nothing throws an error.
>
> https://tickertruth.com/blog/posts/silent-symbol-swap/
>
> #QuantFinance #AlgoTrading #NSEIndia #BacktestData #FinTech

---

## 5. Approver Setup Reference (one-time, already done)

For reference — this has already been configured on this repo:

- **Branch protection on `main`:** required PR, 1 approval from a
  non-author, admins exempt from the approval requirement (so the Approver
  can still merge solo). Force-pushes and branch deletion on `main` are
  blocked. Verified live (Section 0.1) — an unapproved merge attempt is
  flatly refused, and self-approval is rejected by GitHub itself.
- **`drafts` branch:** created off `main`, pushed to origin, and left
  permanently in place — the Content Creator's StackEdit workspace always
  points here. It's reused post after post; you don't need to recreate it.
- **Adding the Content Creator as a collaborator:** GitHub repo → Settings
  → Collaborators → **Add people** → enter their GitHub username or email →
  role **Write** → send invite. They accept it via the emailed link
  (Section 1.1, Step 2). Write access lets them push to `drafts`; branch
  protection still blocks them from merging into `main` without your
  approval.
- **Connecting their StackEdit workspace:** done together, in person or on
  a call — Section 1.1, Step 4 walks through the exact fields (repository
  `brkrishna/TickerTruth`, branch `drafts`, folder
  `website/blog/content/posts`).

---

## 6. Checklist (Approver)

- [ ] PR was opened by the Content Creator (not you) — required for your approval to count
- [ ] All 4 checks green (`Lint`, `Blog Build Check`, `Unit Tests`, `Cloudflare Pages`)
- [ ] Preview URL checked — renders correctly, date isn't in the future
- [ ] PR approved and merged
- [ ] Production URL returns `200`
- [ ] Live URL sent to the Content Creator for cross-posting
- [ ] Substack / Medium / LinkedIn posted with backlinks

---

## 7. Troubleshooting

**Post isn't in the preview / production build, and everything looked
fine.** Almost always one of two silent causes — Hugo doesn't error on
either, it just produces no page:
- The `date:` field is in the future.
- The front matter has a stray `draft: true` line (the template in this
  doc doesn't include one, so this only happens if someone copied an older
  template or added it by hand).

**`Blog Build Check` fails.** Usually a broken front-matter block — most
often a stray unescaped `"` inside `title` or `description`. Reproduce
locally:

```bash
hugo --source website/blog --destination /tmp/hugo-check --minify
```

**No Cloudflare bot comment on the PR.** Check the PR's checks tab directly
— the deployment may still be running or may have failed
(`gh pr checks <pr-number>` links straight to the build log).

**"Review can not approve your own pull request."** You (the Approver)
opened the PR yourself instead of the Content Creator. Close it, have the
Content Creator open a fresh one from `drafts` (Section 1.2, Step 5), and
review that one instead.

**Merge button is greyed out / blocked, even after approving.** Confirm
the approval actually came from an account other than the PR's author —
see the note above. If it's genuinely approved by someone else and still
blocked, check `gh pr checks <pr-number>` for a failing required check.

**Content Creator says they can't push to `drafts`.** Confirm they
accepted the collaborator invite (Section 1.1, Step 2) and are signed into
StackEdit with the correct GitHub account.
