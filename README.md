# intervals-icu-s3-mcp

A connector that lets Claude read your training data from **intervals.icu** and remember its training notes and analysis in your own private storage, so your AI trainer builds up memory over time instead of starting from zero every conversation.

You do **not** need to know how to code to set this up. You do need about 20–30 minutes and a credit card on file with Fly.io (the hosting costs are very low — typically a few dollars a month or less).

This guide walks through every click and every command, in order. Just follow it top to bottom.

---

## What you'll need before you start

- A **GitHub account** with this repository (you already have it, since you're reading this file in it).
- A **Fly.io account** — this is where the connector will live, running 24/7. We'll create one below.
- An **intervals.icu account** with some training data in it.

---

## Part 1 — Get your intervals.icu credentials

This connector needs two things from intervals.icu: an **API Key** (like a password just for apps) and your **Athlete ID** (a number that identifies your account).

1. Log in to [intervals.icu](https://intervals.icu).
2. Click your name/avatar in the top right, then **Settings**.
3. Scroll down to the **Developer Settings** section.
4. Find your **Athlete ID** — it's shown right there, and it also appears in your browser's address bar whenever you're on your own profile, looking like `i123456`. Write it down.
5. Click **"Generate API Key"** (or similar wording — if one already exists, you can reuse it). Copy the key somewhere safe for a moment — you'll paste it in a later step.

Keep this key private. Anyone who has it can read and change your intervals.icu data.

---

## Part 2 — Create your Fly.io account

1. Go to [fly.io](https://fly.io) and click **Sign Up**.
2. Sign up with your GitHub account (easiest) or an email address.
3. Fly.io will ask you to add a payment method before you can deploy anything. This app is small and cheap to run, but a card on file is required by Fly.io regardless.

---

## Part 3 — Install the Fly command-line tool

Fly.io's control panel does most things by clicking, but a couple of one-time setup steps are easiest done with a small command-line tool called `flyctl`. Don't worry — you'll just be copying and pasting the lines below into a terminal window.

**On a Mac:**
Open the **Terminal** app (search for it with Spotlight — the magnifying glass icon, top right of your screen), then paste:

```bash
curl -L https://fly.io/install.sh | sh
```

**On Windows:**
Open **PowerShell** (search for it in the Start menu), then paste:

```powershell
pwsh -Command "iwr https://fly.io/install.ps1 -useb | iex"
```

**On Linux:** same command as the Mac instructions above.

After it finishes, close and reopen your terminal window once, then log in:

```bash
fly auth login
```

This opens your web browser and asks you to confirm — click **Confirm**. You're now connected to your Fly.io account from the command line.

---

## Part 4 — Download this project onto your computer

Still in the same terminal window:

```bash
git clone https://github.com/ulrich-johannes/intervals_icu_s3_mcp.git
cd intervals_icu_s3_mcp
git submodule update --init
```

(If `git` isn't installed, Mac will offer to install it automatically the first time you run a `git` command; on Windows, install [Git for Windows](https://git-scm.com/download/win) first.)

---

## Part 5 — Create the app on Fly.io

Still in the same terminal, inside the `intervals_icu_s3_mcp` folder:

```bash
fly apps create intervals-icu-s3-mcp
```

> If that name is already taken by someone else (Fly.io app names are global), pick a different one, e.g. `fly apps create my-trainer-mcp-2026`, and then edit the `app = "..."` line at the top of the `fly.toml` file in this folder to match, before continuing.

---

## Part 6 — Create your private storage bucket

This is where the trainer's notes and memory will actually live. Run:

```bash
fly storage create
```

It will ask a couple of questions:
- **Which app is this for?** → choose the app you just created.
- **Name for this bucket?** → any name you like, e.g. `trainer-memory`.

When it finishes, it automatically stores the bucket's address and secret keys as secrets on your Fly app — you don't need to copy/paste anything from this step. ✅

---

## Part 7 — Set your remaining secrets

"Secrets" are just private settings the app reads when it starts — things like your intervals.icu key and the password you'll use to connect from Claude. They are never written into the code or visible to anyone browsing this repository.

Run this command, **replacing every `...` with your own values** (keep it all as one command):

```bash
fly secrets set \
  PUBLIC_URL=https://intervals-icu-s3-mcp.fly.dev \
  OAUTH_USERNAME=... \
  OAUTH_PASSWORD=... \
  INTERVALS_ICU_API_KEY=... \
  INTERVALS_ICU_ATHLETE_ID=... \
  INTERVALS_ICU_DELETE_MODE=safe
```

What to put where (see the full table in [Part 10](#part-10--what-each-setting-means) for more detail):

| Setting | What to put there |
| --- | --- |
| `PUBLIC_URL` | `https://` + the app name you picked in Part 5 + `.fly.dev` |
| `OAUTH_USERNAME` | A username **you make up** — you'll use it to log in from Claude later |
| `OAUTH_PASSWORD` | A password **you make up** — pick something you'll remember, there's no recovery option, you'd just set a new one here if forgotten |
| `INTERVALS_ICU_API_KEY` | The API key from [Part 1](#part-1--get-your-intervalsicu-credentials) |
| `INTERVALS_ICU_ATHLETE_ID` | Your Athlete ID from [Part 1](#part-1--get-your-intervalsicu-credentials) |
| `INTERVALS_ICU_DELETE_MODE` | Leave as `safe` unless you know you want something else — see Part 10 |

---

## Part 8 — Deploy it

This is the step that actually builds and starts your app:

```bash
fly deploy
```

This takes a few minutes the first time. When it's done, check that it's alive by opening this address in your browser (replacing the app name if you picked a different one):

```
https://intervals-icu-s3-mcp.fly.dev/health
```

You should see `{"status":"ok"}`. If you do, it worked! 🎉

---

## Part 9 — Connect it to Claude

1. Go to [claude.ai](https://claude.ai) and open **Settings → Connectors**.
2. Click **Add custom connector**.
3. For the URL, enter your app's address with `/mcp` at the end, e.g.:
   ```
   https://intervals-icu-s3-mcp.fly.dev/mcp
   ```
4. Claude will open a little sign-in screen. Enter the `OAUTH_USERNAME` and `OAUTH_PASSWORD` you made up in Part 7.
5. That's it — Claude can now read your intervals.icu training data and keep its own training notes, privately, in your storage bucket.

### Keeping it up to date automatically (optional, one-time setup)

So that improvements to the underlying intervals.icu connector reach your server automatically whenever this repository is updated and pushed to `main`:

1. On [fly.io/dashboard](https://fly.io/dashboard), open your app.
2. Go to **Settings → Source code** (wording may vary slightly as Fly.io updates its dashboard).
3. Click **Connect to GitHub** and pick this repository and the `main` branch.

From then on, pushing a change to `main` on GitHub automatically redeploys your app — no terminal needed.

---

## Part 10 — What each setting means

| Setting | Where it comes from | What it's for |
| --- | --- | --- |
| `PUBLIC_URL` | You type it in | The public web address of your own server |
| `PORT` | Leave unset (defaults to `8080`) | The internal port the app listens on |
| `OAUTH_USERNAME` / `OAUTH_PASSWORD` | You make these up | The login Claude uses to connect to *your* server — nothing to do with your intervals.icu password |
| `BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ENDPOINT_URL_S3`, `AWS_REGION` | Set automatically by `fly storage create` (Part 6) | Where the trainer's notes/memory are stored |
| `INTERVALS_ICU_API_KEY` | intervals.icu → Settings → Developer Settings | Lets the server read/write your intervals.icu data |
| `INTERVALS_ICU_ATHLETE_ID` | intervals.icu → Settings → Developer Settings | Identifies which athlete's data to use |
| `INTERVALS_ICU_DELETE_MODE` | You choose: `safe` (default), `full`, or `none` | Controls whether destructive tools (e.g. deleting an activity) are available at all. `safe` is recommended for most people; `none` disables all delete tools entirely; `full` enables everything |

None of your credentials are ever stored in this repository's code — they only exist as Fly.io "secrets," which are encrypted and only readable by your own running app.

---

## Troubleshooting

- **"App name already taken"** when creating the app → pick a different name everywhere you see it (Part 5 and the `PUBLIC_URL` secret).
- **`/health` doesn't show `{"status":"ok"}`** → run `fly logs` in the terminal to see what went wrong; the most common cause is a missing or misspelled secret from Part 7.
- **Claude says it can't connect** → double check the URL ends in `/mcp` (not `/health` or nothing at all), and that you typed the `OAUTH_USERNAME`/`OAUTH_PASSWORD` from Part 7 correctly on the login screen.
- **Forgot your `OAUTH_PASSWORD`** → just set a new one: `fly secrets set OAUTH_PASSWORD=your-new-password`, then reconnect in Claude.

---

## For developers

The full technical design (architecture, data model, upstream integration strategy, testing approach, trade-offs) lives in [SPECIFICATION.md](SPECIFICATION.md). This README is the non-technical setup guide; that document is the engineering reference.
