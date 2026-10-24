# intervals-icu-s3-mcp

A connector that lets Claude read your training data from **intervals.icu** and remember its training notes and analysis in your own private storage, so your AI trainer builds up memory over time instead of starting from zero every conversation.

You do **not** need to know how to code, and you will **not** need to open a terminal or install anything on your computer. Everything below happens by clicking around on websites. It takes about 15–20 minutes, plus having a credit card on file with Fly.io (the hosting cost is very low — typically a few dollars a month or less).

---

## What you'll need before you start

- A **GitHub account**.
- A **Fly.io account** — this is where the connector will live, running 24/7. We'll create one below.
- An **intervals.icu account** with some training data in it.

---

## Part 1 — Make your own copy of this project on GitHub

Fly.io deploys directly from a GitHub repository, so you need your own copy of this one to connect it to.

1. Open this project's GitHub page.
2. Click the **Fork** button near the top right of the page.
3. Click **Create fork**. GitHub creates a copy of this project under your own account — you now have your own GitHub link to it, something like `https://github.com/your-name/intervals_icu_s3_mcp`.

---

## Part 2 — Get your intervals.icu credentials

This connector needs two things from intervals.icu: an **API Key** (like a password just for apps) and your **Athlete ID** (a number that identifies your account).

1. Log in to [intervals.icu](https://intervals.icu).
2. Click your name/avatar in the top right, then **Settings**.
3. Scroll down to the **Developer Settings** section.
4. Find your **Athlete ID** — it's shown right there, and it also appears in your browser's address bar whenever you're on your own profile, looking like `i123456`. Write it down somewhere.
5. Click **"Generate API Key"** (or similar wording — if one already exists, you can reuse it). Copy the key and keep it handy — you'll paste it in a later step.

Keep this key private. Anyone who has it can read and change your intervals.icu data.

---

## Part 3 — Create your Fly.io account

1. Go to [fly.io](https://fly.io) and click **Sign Up**.
2. Sign up with your GitHub account (easiest — it also makes Part 4 smoother) or an email address.
3. Fly.io will ask you to add a payment method before you can deploy anything. This app is small and cheap to run, but a card on file is required by Fly.io regardless.

---

## Part 4 — Deploy the app, by pasting your GitHub link

1. Go to the [Fly.io dashboard](https://fly.io/dashboard).
2. Look for a button along the lines of **"Launch an app"** or **"New app"**, then choose the option to **deploy from a GitHub repository** (wording changes occasionally as Fly updates its site — look for anything mentioning GitHub).
3. If asked, authorize Fly.io to access your GitHub account/repositories.
4. Pick the fork you created in Part 1 (`your-name/intervals_icu_s3_mcp`) and the `main` branch.
5. Fly.io reads this project's `Dockerfile` and `fly.toml` automatically — you shouldn't need to change any settings. If it asks for an app name and your first choice is taken, just pick another one (e.g. add your name: `my-trainer-mcp-ulrich`).
6. Click **Deploy** / **Launch**.

Fly.io will now build and start the app. This can take a few minutes the first time — you'll see build logs scrolling by. **Don't worry if it looks unfinished or fails at this point** — it needs the settings from Part 6 before it can fully work; we'll come back and redeploy after that.

Fly.io also sets this app up for **continuous deployment**: from now on, any future update pushed to the `main` branch of your fork will redeploy automatically, with no further clicking needed.

---

## Part 5 — Create your private storage bucket

This is where the trainer's notes and memory will actually live.

1. On the Fly.io dashboard, find your way to **Object Storage** (sometimes listed under your organization's settings, sometimes as its own section in the sidebar — Fly calls this service "Tigris").
2. Click **Create bucket** (or **"Add storage"**).
3. Give it any name you like, e.g. `trainer-memory`.
4. When asked which app to attach it to, choose the app you created in Part 4.

If Fly's dashboard attaches the bucket to your app automatically, it should also add the right secrets for you — check Part 6 below; if you already see entries like `BUCKET_NAME` and `AWS_ACCESS_KEY_ID` listed there, this step is done and you can skip adding them manually.

If instead the bucket's page just shows you connection details (an access key, a secret key, an endpoint address, a bucket name) without attaching anything automatically, that's fine too — just keep that page open, you'll copy those values into secrets manually in the next part.

---

## Part 6 — Add your secrets

"Secrets" are private settings the app reads when it starts — things like your intervals.icu key and a login you make up for Claude to use. They are never written into the project's code and never visible to anyone browsing GitHub.

1. On the Fly.io dashboard, open your app, then find the **Secrets** tab/section.
2. Click **New secret** (or similar) once for each row below, typing the name on the left exactly as shown and your own value on the right.

| Secret name | What to put there |
| --- | --- |
| `PUBLIC_URL` | `https://` + your app's name (from Part 4) + `.fly.dev` — e.g. `https://my-trainer-mcp-ulrich.fly.dev` |
| `OAUTH_USERNAME` | A username **you make up** — you'll use it to connect Claude later |
| `OAUTH_PASSWORD` | A password **you make up** — pick something you'll remember; if you forget it, you just set a new one here later |
| `INTERVALS_ICU_API_KEY` | The API key from [Part 2](#part-2--get-your-intervalsicu-credentials) |
| `INTERVALS_ICU_ATHLETE_ID` | Your Athlete ID from [Part 2](#part-2--get-your-intervalsicu-credentials) |
| `INTERVALS_ICU_DELETE_MODE` | Type `safe` (recommended for most people — see Part 9 for other options) |

If Part 5's bucket wasn't attached automatically, also add these (copied from the bucket's connection details page):

| Secret name | What to put there |
| --- | --- |
| `BUCKET_NAME` | The bucket name you chose in Part 5 |
| `AWS_ACCESS_KEY_ID` | From the bucket's connection details |
| `AWS_SECRET_ACCESS_KEY` | From the bucket's connection details |
| `AWS_ENDPOINT_URL_S3` | From the bucket's connection details |
| `AWS_REGION` | From the bucket's connection details (often just `auto`) |

---

## Part 7 — Redeploy

Adding secrets doesn't automatically restart the app. On your app's Fly.io dashboard page, look for a **Redeploy** or **Restart** button and click it. Give it a minute, then check it worked:

1. Open a new browser tab and go to `https://YOUR-APP-NAME.fly.dev/health` (using your actual app name from Part 4).
2. You should see `{"status":"ok"}`. If you do, it worked! 🎉

---

## Part 8 — Connect it to Claude

1. Go to [claude.ai](https://claude.ai) and open **Settings → Connectors**.
2. Click **Add custom connector**.
3. For the URL, enter your app's address with `/mcp` at the end, e.g.:
   ```
   https://YOUR-APP-NAME.fly.dev/mcp
   ```
4. Claude will open a little sign-in screen. Enter the `OAUTH_USERNAME` and `OAUTH_PASSWORD` you made up in Part 6.
5. That's it — Claude can now read your intervals.icu training data and keep its own training notes, privately, in your storage bucket.

---

## Part 9 — What each secret means

| Secret | Where it comes from | What it's for |
| --- | --- | --- |
| `PUBLIC_URL` | You type it in | Your server's own public web address |
| `OAUTH_USERNAME` / `OAUTH_PASSWORD` | You make these up | The login Claude uses to connect to *your* server — nothing to do with your intervals.icu password |
| `BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ENDPOINT_URL_S3`, `AWS_REGION` | Fly.io's storage dashboard (Part 5) | Where the trainer's notes/memory are stored |
| `INTERVALS_ICU_API_KEY` | intervals.icu → Settings → Developer Settings | Lets the server read/write your intervals.icu data |
| `INTERVALS_ICU_ATHLETE_ID` | intervals.icu → Settings → Developer Settings | Identifies which athlete's data to use |
| `INTERVALS_ICU_DELETE_MODE` | You choose: `safe` (default), `full`, or `none` | Controls whether destructive tools (e.g. deleting an activity) are available at all. `safe` is recommended for most people; `none` disables all delete tools entirely; `full` enables everything |

None of your credentials are ever stored in this project's code — they only exist as Fly.io "secrets," which are encrypted and only readable by your own running app.

---

## Troubleshooting

- **"App name already taken"** when deploying → pick a different name in Part 4, then make sure `PUBLIC_URL` in Part 6 matches whatever name you ended up with.
- **`/health` doesn't show `{"status":"ok"}`** → open your app's **Logs** on the Fly.io dashboard to see what went wrong; the most common cause is a missing or misspelled secret from Part 6, or forgetting to redeploy after adding them (Part 7).
- **Claude says it can't connect** → double check the URL ends in `/mcp` (not `/health` or nothing at all), and that you typed the `OAUTH_USERNAME`/`OAUTH_PASSWORD` from Part 6 correctly on the login screen.
- **Forgot your `OAUTH_PASSWORD`** → go to Secrets on the Fly.io dashboard, edit `OAUTH_PASSWORD` to a new value, redeploy, then reconnect in Claude with the new password.

---

## For developers

The full technical design (architecture, data model, upstream integration strategy, testing approach, trade-offs) lives in [SPECIFICATION.md](SPECIFICATION.md). This README is the non-technical setup guide; that document is the engineering reference.
