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

This copy doesn't go stale forever — see [Part 9](#part-9--keeping-it-up-to-date) for the one-click way to pull in future updates whenever we improve this project.

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

This is where the trainer's notes and memory will actually live. Storage here is Tigris, a service built into Fly.io.

**Important: create the bucket through Fly's own "attach storage to this app" flow, not by creating an access key separately in a Tigris console.** Doing it the first way makes Fly generate a key that already has the correct permissions on your bucket, bundled together automatically. Doing it the second way gives you a key that technically exists and looks right (correct bucket name, correct credentials) but has **zero permissions** on anything — every read and write fails with `AccessDenied`, even though nothing looks obviously wrong. If you hit that exact symptom, skip ahead to [the fix below](#if-everything-returns-access-denied-even-though-your-secrets-look-right).

1. On the Fly.io dashboard, find your way to **Object Storage** (sometimes listed under your organization's settings, sometimes as its own section in the sidebar — Fly calls this service "Tigris").
2. Click **Create bucket** (or **"Add storage"**) — and specifically look for a version of this flow that asks **which app to attach it to**. That app-picker step is what makes Fly wire up the permissions correctly.
3. Give it any name you like, e.g. `trainer-memory`.
4. Choose the app you created in Part 4.

If Fly's dashboard attaches the bucket to your app automatically this way, it should also add the right secrets for you — check Part 6 below; if you already see entries like `BUCKET_NAME` and `AWS_ACCESS_KEY_ID` listed there, this step is done and you can skip adding them manually.

If instead the bucket's page just shows you connection details (an access key, a secret key, an endpoint address, a bucket name) without an app-attach step, that's still fine — just keep that page open, you'll copy those values into secrets manually in the next part. Just be aware that if those values came from a key created *outside* an app-attach flow, you may need the fix in the next section too.

### If everything returns "Access Denied" even though your secrets look right

Symptom: the app runs, `/health` says `"configured":true`, every secret is spelled correctly and points at the right bucket — but every read or write through Claude fails, and Fly's logs show `AccessDenied` on object operations.

This means the access key exists and is genuinely yours, but has no permissions attached to it — a known Tigris behavior when a key is created outside Fly's attach-to-app flow (see Tigris's own docs: [IAM overview](https://tigrisdata.com/docs/iam), [limited access keys](https://www.tigrisdata.com/docs/iam/policies/limited-access-key), [attaching a policy](https://www.tigrisdata.com/docs/iam/policies/attach-iam-policy/)). Fix it by attaching a policy to the key:

1. On Tigris's dashboard, open **IAM Policies** and create a new policy (JSON editor), using your actual bucket name in place of `coachdata`:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "AllowListingBucket",
         "Effect": "Allow",
         "Action": ["s3:ListBucket"],
         "Resource": "arn:aws:s3:::coachdata"
       },
       {
         "Sid": "AllowReadWriteObjects",
         "Effect": "Allow",
         "Action": ["s3:GetObject", "s3:PutObject"],
         "Resource": "arn:aws:s3:::coachdata/*"
       }
     ]
   }
   ```
   (`s3:DeleteObject` is deliberately left out — this app never issues one; `state_delete` only soft-deletes.)
2. Open that policy's details, click **"Manage IAM Policy"** → **"Linked Access Keys"** → **"+ Link"**, and attach it to your access key (the `tid_...` value from your `AWS_ACCESS_KEY_ID` secret).
3. No redeploy needed — this is a Tigris-side permission change, not an app setting. Try again through Claude right away.

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
| `OAUTH_STATE_SECRET` | Another password-like value **you make up** — you'll never type this one in anywhere again, it just protects your saved login sessions (see Part 9) |
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
2. You should see `{"status":"ok","configured":true}`. If you do, it worked! 🎉

If you instead see `"configured":false` and a `"missing"` list, the app is running fine but is still missing one or more secrets — the list names exactly which ones. Go back to Part 6, add those, and redeploy again. You'll see the same thing if you connect it to Claude too early: Claude will only see one tool, called `check_configuration`, which tells you the same thing.

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

## Part 9 — Keeping it up to date

Your fork is its own separate copy, so when this project gets improved, those changes don't reach your fork by themselves. Getting them is a single click, whenever you feel like checking:

1. Open your fork's GitHub page (`https://github.com/your-name/intervals_icu_s3_mcp`).
2. If it's behind, GitHub shows a **"Sync fork"** button (sometimes under a small banner saying "This branch is X commits behind..."). Click it, then click **Update branch**.
3. That's it — this pushes the update into your fork's `main` branch, which Fly.io is already watching (Part 4), so it redeploys automatically within a minute or two. No further clicking needed.

This is a manual check-in, not something that happens on its own — nothing will ping you when an update is available. If you want to be sure you're current, it's worth glancing at your fork's GitHub page every so often.

---

## Part 10 — What each secret means

| Secret | Where it comes from | What it's for |
| --- | --- | --- |
| `PUBLIC_URL` | You type it in | Your server's own public web address |
| `OAUTH_USERNAME` / `OAUTH_PASSWORD` | You make these up | The login Claude uses to connect to *your* server — nothing to do with your intervals.icu password |
| `OAUTH_STATE_SECRET` | You make this up too | Protects your saved Claude login session (stored in your storage bucket) so a machine restart doesn't force you to fully reconnect every time |
| `BUCKET_NAME` | Fly.io's storage dashboard (Part 5) | The bucket name |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Fly.io's storage dashboard (Part 5) | Tigris credentials — must be a key created through the app-attach flow, or one with a policy attached by hand (see Part 5's troubleshooting box) |
| `AWS_ENDPOINT_URL_S3` | Fly.io's storage dashboard (Part 5) | Tigris's S3-compatible API address — currently `https://t3.storage.dev` |
| `AWS_REGION` | Fly.io's storage dashboard (Part 5) | Almost always `auto` for Tigris |
| `INTERVALS_ICU_API_KEY` | intervals.icu → Settings → Developer Settings | Lets the server read/write your intervals.icu data |
| `INTERVALS_ICU_ATHLETE_ID` | intervals.icu → Settings → Developer Settings | Identifies which athlete's data to use |
| `INTERVALS_ICU_DELETE_MODE` | You choose: `safe` (default), `full`, or `none` | Controls whether destructive tools (e.g. deleting an activity) are available at all. `safe` is recommended for most people; `none` disables all delete tools entirely; `full` enables everything |

You may also see an `AWS_ENDPOINT_URL_IAM` secret appear (`https://iam.storage.dev`) when Fly provisions Tigris storage — this app doesn't read or need it; it's only relevant if you end up managing IAM policies by hand (Part 5's troubleshooting box).

None of your credentials are ever stored in this project's code — they only exist as Fly.io "secrets," which are encrypted and only readable by your own running app.

---

## Troubleshooting

- **"App name already taken"** when deploying → pick a different name in Part 4, then make sure `PUBLIC_URL` in Part 6 matches whatever name you ended up with.
- **`/health` doesn't show `{"status":"ok"}`** → open your app's **Logs** on the Fly.io dashboard to see what went wrong; the most common cause is a missing or misspelled secret from Part 6, or forgetting to redeploy after adding them (Part 7).
- **Claude says it can't connect** → double check the URL ends in `/mcp` (not `/health` or nothing at all), and that you typed the `OAUTH_USERNAME`/`OAUTH_PASSWORD` from Part 6 correctly on the login screen.
- **Forgot your `OAUTH_PASSWORD`** → go to Secrets on the Fly.io dashboard, edit `OAUTH_PASSWORD` to a new value, redeploy, then reconnect in Claude with the new password.
- **Claude keeps asking you to log in again** → this should now be rare (your login session is saved in your storage bucket, so a normal restart doesn't clear it), but changing `OAUTH_STATE_SECRET` itself, or recreating your storage bucket, does — in both cases, just reconnect once in Claude's Connectors settings.
- **The trainer says it couldn't read or save its notes ("access denied")** → see [Part 5's troubleshooting box](#if-everything-returns-access-denied-even-though-your-secrets-look-right); this is almost always a Tigris access key with no permissions attached, not a secret that's wrong or missing.

---

## For developers

The full technical design (architecture, data model, upstream integration strategy, testing approach, trade-offs) lives in [SPECIFICATION.md](SPECIFICATION.md). This README is the non-technical setup guide; that document is the engineering reference.
