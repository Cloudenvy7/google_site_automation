# SETUP

Getting this repo running on a machine that is not the one it was built on.

Everything below is required before a build. Nothing here has a default in the
code — if a value is missing, the code raises and names every location it looked
in, rather than guessing. A wrong-but-plausible path is worse than a missing one:
it fails later, somewhere less obvious.

---

## 1. Prerequisites

- **Python 3.9+** (proven on 3.13.5)
- **Google Chrome or Chromium** — the Site write path is the Chrome DevTools
  Protocol. Google Sites has no public content API; this is the sanctioned
  surface, not a workaround.
- A Google account that can **edit the target Site**.

## 2. Install

```bash
git clone https://github.com/Cloudenvy7/google_site_automation.git
cd google_site_automation
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
git config core.hooksPath .githooks     # runs the evals before each commit
```

## 3. Google credentials

The indexers read Drive and read/write Sheets through a **service account**. You
need your own; the one this was built with is not in the repo and would not work
for you anyway.

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project
   (or pick one).
2. **APIs & Services → Enable APIs** → enable **Google Drive API** and
   **Google Sheets API**.
3. **IAM & Admin → Service Accounts → Create**. No project roles are needed — its
   access comes from Drive sharing, not IAM.
4. On the new account: **Keys → Add key → JSON**. Download it.
5. Put it somewhere outside the repo and point at it:

   ```bash
   cp .env.example .env        # then edit
   export GOOGLE_SERVICE_ACCOUNT_JSON=/absolute/path/to/service_account.json
   ```

   If unset, the code looks in `./service_account.json` then
   `~/.advisor_os/service_account.json`.

6. **Share with it.** Copy the service account's email (it ends
   `.iam.gserviceaccount.com`) and share, as **Editor**:
   - the client's Drive folder you are indexing
   - the per-site catalogue spreadsheet (step 5)

   > **Link-sharing does not grant service accounts.** "Anyone with the link"
   > covers people; a service account still gets HTTP 404. Share with its address
   > explicitly. This cost a working session to discover.

`service_account.json` and `.env` are gitignored. Keep it that way — and note
that `.claude/settings.json` also denies reading them from inside a session.

## 4. Chrome

Run this **from your own terminal**, inside your desktop session:

```bash
./scripts/launch_chrome.sh
```

> Chrome started from a non-desktop shell — an agent, or ssh — cannot reach the
> system keyring. It then presents as signed out even though the profile holds a
> valid session, and the failure looks like expired credentials. If
> `DBUS_SESSION_BUS_ADDRESS` is unset, you are in that situation. The launcher
> warns you.

It opens a window on a profile separate from your everyday Chrome. Sign in to the
Google account that can edit the Site; it persists after that.

## 5. The catalogue

Every site gets its own **Visual Knowledge Catalogue** spreadsheet.

**Copy the Sheet from the template — do not hand-assemble it from
`catalogue_template/`.** Those CSVs are there so the schema is readable and
diffable in git. A catalogue missing a tab is not a smaller catalogue, it is a
broken one: later stages read columns by name and fail silently when a name
moves.

Then set `ADVISOR_CATALOGUE_ID` in `.env` to the new spreadsheet's id.

## 6. Verify before you build

```bash
bash evals/run.sh                                   # 40 coverage + 35 hook cases
python scripts/site_survey.py <site_id> <u_index>   # read-only; prints the account
```

`site_survey.py` never mutates a site. Check the account it prints is the one you
expect **before** building — the `<u_index>` is the `/u/N/` in the editor URL, and
getting it wrong points the build at a different signed-in account.

Before an actual build:

```bash
python scripts/harness.py preflight <catalogue_id> <site_id>
```

This applies STAGE 0, `00_HARNESS`, GATE 1 and GATE 5, and leaves a stamp. It
does **not** decide ratification — a human records that in the catalogue — it
only checks it was done. The build hook refuses to open the door without a fresh
stamp reading `RATIFIED`.

## 7. Optional — make the session tools available everywhere

`.claude/skills/session-export/` works as soon as you open this repo. To use it
in *every* project on the machine, link it into the global skills directory:

```bash
mkdir -p ~/.claude/skills
ln -s "$PWD/.claude/skills/session-export" ~/.claude/skills/session-export
```

A symlink rather than a copy, deliberately: a copy is a second version that
drifts, and a drifted tool still runs.

Set `SESSION_EXPORT_USER` in `.env` if you want your own name as the speaker
label instead of `$USER`.

> **On session exports and client data.** `session-export` writes to
> `~/.advisor_os/session_exports/` by default, deliberately outside any
> repository. Transcripts are not work product — they are a record of everything
> discussed, and they belong on the machine that made them or in the client's own
> Drive. Never commit one. `.gitignore` covers the usual paths and the tools warn
> when aimed at a working tree, but neither substitutes for the judgement.

## 8. Known limits, stated plainly

**Credentials are a service account, not the user.** The ratified direction is
*"OAuth as the user"* (DEVLOG, 2026-09-07) so a client runs against their own
Google identity. **That is not built.** Today, running this on a client machine
means creating a service account as above and sharing folders with it. The
indexers will not work any other way yet.

**The hook reads command text, not the DOM.** It stops an agent from drifting; it
is not a sandbox.

**On a client's own account, `.claude/settings.json` is editable by that human.**
That is intended. It governs the agent, not the person.

**Google changes the editor.** Aria-labels and cell layouts move — a layout tile
was renamed mid-2026 and every insert failed with a bare timeout. When something
stops working, probe the live DOM before assuming the code is wrong.
