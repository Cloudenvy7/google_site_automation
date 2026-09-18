# SETUP

Getting this running on a machine that has never run it before.

**Written to be followed by someone who has not done this and has nobody sitting
next to them.** If a step here assumes something it did not tell you, that is a
bug in this document — please say so.

**The short version:**

```bash
git clone https://github.com/Cloudenvy7/google_site_automation.git
cd google_site_automation
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/doctor.py          # tells you what is still missing
```

`doctor.py` checks everything below and prints the exact fix for each thing that
is wrong. **Run it whenever you are stuck.** It reads only — it never writes,
uploads, or touches a Site.

---

## 0. What you are setting up, in plain words

Three separate things have to be true before this works:

1. **The code** is on your machine, with Python and a couple of libraries.
2. **A robot Google account** — a *service account* — exists, and you have its
   key file. This is what reads the Drive folder and fills in the spreadsheet.
3. **You have shared your folder and spreadsheet with that robot**, by its email
   address. This is the step people miss.

There is also a fourth, only needed later when you build the actual Site:
Chrome running in a special mode. Indexing does not need it.

**Roughly 30–45 minutes the first time**, most of it in the Google Cloud console.

---

## 1. Prerequisites

| Need | Check | If missing (macOS) |
|---|---|---|
| **Python 3.9+** (proven on 3.13.5) | `python3 --version` | `brew install python@3.12` |
| **Node.js / npm** | `npm --version` | `brew install node` |
| **Claude Code CLI** | `claude --version` | `npm install -g @anthropic-ai/claude-code` |
| **Git** | `git --version` | ships with Xcode tools |
| **Google Chrome** | — | only needed to build a Site |

> **The Claude Code CLI install takes several minutes and prints almost nothing
> while it runs.** That is normal — do not cancel it. `indexer_v3.py` shells out
> to `claude`, so without it Stage 1 cannot run at all. This was missing from the
> first version of this document and cost a client session about ten minutes of
> confusion.

If `pip` nags you to upgrade itself, do that **first**, then install:

```bash
python3 -m pip install --upgrade pip
```

## 2. Get the code

```bash
git clone https://github.com/Cloudenvy7/google_site_automation.git
cd google_site_automation
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
git config core.hooksPath .githooks
```

That last line turns on a pre-commit hook that **refuses to commit a credential**
and runs the test suite when agent-steering files change.

> **If an AI assistant is helping you: have it READ the repository before it
> judges it.** On 2026-09-18 a session called this code "questionable" without
> opening it, and had to be told to read it first. Caution about running code
> from the internet is right; *concluding* before reading is not.

## 3. The service account — what it is and why

A **service account** is a Google account for software rather than a person. It
has an email address like `sites-indexer@your-project.iam.gserviceaccount.com`,
and it can be given access to Drive files exactly like a colleague would be.

You need one because the indexer reads your Drive folder and writes rows into a
spreadsheet. It cannot use *your* login — that would mean handing it your
password. Instead you create a limited robot and share only what it needs.

**In [console.cloud.google.com](https://console.cloud.google.com), signed in as
the Google account that owns the Drive folder:**

1. **Create a project** (or pick one). Top bar → project dropdown → NEW PROJECT.
   Any name. Note the **project ID** — you will see it again.

2. **Enable two APIs.** ☰ → *APIs & Services* → *Library*. Search and ENABLE:
   - **Google Drive API**
   - **Google Sheets API**

   > **Enable BOTH. This is the single most expensive mistake in this document.**
   > On 2026-09-18 only Drive got enabled. The missing Sheets API surfaced
   > **75 minutes later** as a confusing permissions error, long after everything
   > else was done. `doctor.py` now catches it in about two seconds.

3. **Create the service account.** ☰ → *IAM & Admin* → *Service Accounts* →
   **+ CREATE SERVICE ACCOUNT**.
   - **Name:** anything descriptive — `sites-indexer`. 6–30 characters,
     lowercase letters, digits and hyphens, starting with a letter.
   - **Step 2, "Grant this service account access to the project": SKIP IT.**
     Click CONTINUE. **No role is needed.** IAM roles govern Google *Cloud*
     resources; they have nothing to do with Drive. Access to your files comes
     from sharing, in section 5.
   - **Step 3:** skip as well. Click DONE.

   > If you click back mid-flow you can create a second account by accident —
   > that happened on 2026-09-18 and caused real confusion about which was which.
   > If you end up with two, delete the spare.

## 4. The key

1. On the *Service Accounts* list, **click the account's email** — the blue link
   itself. **"Keys" is a tab inside the account, not an item in the left menu.**
   This is the step people hunt for.
2. **KEYS** tab → **ADD KEY** → **Create new key** → **JSON** → **CREATE**.
3. It downloads instantly. **That is the only copy** — Google does not keep it.
   Lose it and you delete that key and make another.

**Now move it out of Downloads.** Do this in the terminal — dragging from
Downloads in Finder failed repeatedly during a real setup and burned about nine
minutes:

```bash
mkdir -p ~/.advisor_os
mv ~/Downloads/<the-file-that-just-downloaded>.json ~/.advisor_os/service_account.json
chmod 600 ~/.advisor_os/service_account.json
export GOOGLE_SERVICE_ACCOUNT_JSON=~/.advisor_os/service_account.json
```

> **Keep the key OUTSIDE this repository.** Google names it
> `<project>-<hash>.json`, which no obvious `.gitignore` rule matches — a real
> setup was told to put it in a `secrets/` folder inside the project, where it
> would have been committable. The pre-commit hook now refuses credentials by
> content, but outside the repo is the safe place.

**The filename will not look like anything you expect.** Do not guess whether it
is the right key — check what is inside it:

```bash
python3 scripts/doctor.py
```

It prints the `client_email` and `project_id` the file actually contains.

Add the export to `~/.zshrc` so it survives a new terminal.

## 5. Sharing — the step that actually grants access

Everything so far created a robot. **Nothing has given it access to anything.**

Copy the `client_email` that `doctor.py` printed, then in Google Drive:

| Share this | With | As |
|---|---|---|
| The **Drive folder** you want indexed | that email | **Viewer** |
| Your **catalogue Sheet** (section 6) | that email | **Editor** |

Untick **"Notify people"** — it is a robot and the mail bounces.

> **"Anyone with the link" does NOT work.** Link-sharing grants *people*; a
> service account still gets a bare 404 that explains nothing. You must paste the
> address in. This has now cost time in two separate sessions.

Viewer is enough on the folder because the indexer only ever *reads* it. It
writes to the Sheet, never to your files.

## 6. The catalogue

Every site gets its own **Visual Knowledge Catalogue** spreadsheet — the index
the system builds and then reads back.

**Make a copy of the template Sheet** (File → Make a copy). Copy the **whole
spreadsheet**, not individual tabs, and do not rebuild it from the CSVs in
`catalogue_template/` — those exist so the schema is readable in git.

> A catalogue missing a tab is not a smaller catalogue, it is a broken one.
> Later stages read columns by name and fail silently when a name moves.

Then:

```bash
export ADVISOR_CATALOGUE_ID=<the id of YOUR copy>
```

The id is the long string in the URL between `/d/` and `/edit`.

**Share your copy with the service account as Editor** — this is separate from
sharing the folder, and it was missed at 1h18m on 2026-09-18.

## 7. Chrome — only for building a Site

Indexing does not need this. Skip it until you are ready to build pages.

```bash
./scripts/launch_chrome.sh
```

**Quit Chrome completely first** (⌘Q on macOS — closing windows is not enough).
A Chrome already running ignores the debugging flag, so the port never appears
and nothing explains why.

Run it **from your own terminal**, not through an agent: Chrome started from a
shell with no desktop session cannot reach the keyring, and then presents as
signed out when it is not.

## 8. Verify before you trust it

```bash
python3 scripts/doctor.py --folder <folder-id> --catalogue <sheet-id>
bash evals/run.sh
```

`doctor.py` should show no FAIL lines. `evals/run.sh` should print **ALL PASS**
(40 coverage checks + 35 hook cases).

Then confirm the safety hook is actually loaded:

```bash
python3 -c "import sites_automation as S; S.insert_layout('x','Image and caption')"
```

**This must be REFUSED** with a "SITE BUILD GATE -- refused" message. If it runs
instead, the hook is not active and nothing is protecting your Sites — stop and
say so.

## 9. Known limits, stated plainly

**Cost: there is no metered API billing.** Every model call is the Claude Code
CLI on your flat subscription. The subscription has a token allowance per rolling
window; hitting it pauses work and does not generate a bill. Indexing logs to the
Sheet and resumes, so a pause costs time, not money or progress. *(A session once
told a client their usage was metered. It was wrong.)*

**Credentials are a service account, not you.** The ratified direction is *"OAuth
as the user"* so a client runs against their own identity. **That is not built.**

**A service account has no My Drive storage.** It can read your folder and fill a
Sheet you own, but it cannot create new Drive files. That is why you copy the
catalogue template by hand.

**The Site-build hook reads command text, not the page.** It stops an agent from
drifting; it is not a sandbox.

**Google changes the editor.** Labels and layouts move — a layout tile was
renamed mid-2026 and every insert failed with a bare timeout. When something
stops working, probe the live page before assuming the code is wrong.
