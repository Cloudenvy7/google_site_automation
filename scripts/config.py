"""Machine-specific paths and ids, resolved once, with no developer's home
directory baked in.

WHY THIS EXISTS (2026-09-13)
Seven files carried "/home/tyler/Projects/Blackfox Studios/..." as a literal
default. On the machine they were written on that works and nothing complains,
which is exactly why it survived: the failure only appears somewhere else.

Two of them -- drive_indexer.py and merge_index_pass_b.py -- had no environment
override at all, so on a clone there was no way to run them without editing the
source. merge_index_pass_b.py additionally hard-coded one client's catalogue id
and wrote to it, which on someone else's machine is not a failure, it is a write
into the wrong spreadsheet.

This repo is meant to be cloned and run on a client's machine against their
Google account. A default naming one person's home directory is not a default;
it is a machine the code silently requires.

Nothing here invents a path. If a value cannot be resolved it raises and names
every location it looked in, because a wrong-but-plausible path is worse than a
missing one -- it fails later, somewhere less obvious.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ConfigError(RuntimeError):
    """Raised when a required path or id cannot be resolved. Never guessed."""


def service_account_path(required=True):
    """Locate the service-account key. Most explicit first.

    The key is never in this repo and never should be -- .gitignore excludes
    service_account.json for that reason. These are the places a human may
    reasonably have put their own.
    """
    env_keys = ("GOOGLE_SERVICE_ACCOUNT_JSON", "ADVISOR_SA")
    for k in env_keys:
        v = os.environ.get(k)
        if v:
            if not os.path.exists(v):
                raise ConfigError(
                    "%s is set to %r but no file is there. Fix the variable or "
                    "unset it to fall back to the searched locations." % (k, v))
            return v

    candidates = [
        os.path.join(REPO_ROOT, "service_account.json"),
        os.path.expanduser("~/.advisor_os/service_account.json"),
        os.path.expanduser("~/.config/advisor_os/service_account.json"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    if not required:
        return None
    raise ConfigError(
        "No service-account key found.\n"
        "Set GOOGLE_SERVICE_ACCOUNT_JSON to its path, or place it at one of:\n"
        + "".join("  %s\n" % c for c in candidates)
        + "See SETUP.md -- 'Google credentials'. The key is deliberately not in "
          "this repo.")


def python_bin():
    """The interpreter to use for subprocesses.

    Default to the one already running: if the caller launched us from a venv,
    the child belongs in the same venv. PYTHON overrides for the odd case where
    it does not.
    """
    return os.environ.get("PYTHON") or sys.executable


def catalogue_id(argv_value=None):
    """The per-site Visual Knowledge Catalogue spreadsheet id.

    There is no default and there must not be one. This id is the site being
    worked on; a stale default writes a client's index into another client's
    catalogue.
    """
    v = argv_value or os.environ.get("ADVISOR_CATALOGUE_ID")
    if not v:
        raise ConfigError(
            "No catalogue id. Pass it as an argument or set "
            "ADVISOR_CATALOGUE_ID.\nThis identifies the site you are working "
            "on -- there is deliberately no default, because a stale one writes "
            "into the wrong client's catalogue.")
    return v


# 2026-11-04: the Site build read its target from /tmp/hl_site.txt, a file that
# existed only on the machine the code was written on, and always opened the
# editor as /u/1/ -- the second signed-in Google account. On a client's Mac the
# first stops the build and the second opens the wrong account. The 2026-09-13
# portability pass fixed the indexer's paths and missed these. The person
# running the build now names the Site.

def _from_sites_url(v):
    """Accept a bare Site id or a pasted editor URL; return (site_id, u_or_None)."""
    v = v.strip()
    if "sites.google.com" not in v:
        return v, None
    u = None
    if "/u/" in v:
        u = v.split("/u/", 1)[1].split("/", 1)[0]
    if "/d/" not in v:
        raise ConfigError(
            "That URL has no /d/<site id>/ in it. Open the Site in the EDITOR "
            "(sites.google.com/u/<N>/d/<id>/edit) and copy that address, or pass "
            "the id alone.")
    return v.split("/d/", 1)[1].split("/", 1)[0], u


def site_id(argv_value=None):
    """The Google Site to build. Argument first, then ADVISOR_SITE_ID.

    No default, for the same reason as catalogue_id: a stale default builds
    onto someone else's Site. A full editor URL is accepted, so the person can
    paste what is in their address bar.
    """
    v = argv_value or os.environ.get("ADVISOR_SITE_ID")
    if not v:
        raise ConfigError(
            "No Site id. Pass the Site (its id, or its editor URL) as an "
            "argument, or set ADVISOR_SITE_ID.\nThe id is in the editor address: "
            "sites.google.com/u/<N>/d/<THIS>/edit. There is deliberately no "
            "default, because a stale one builds onto the wrong Site.")
    return _from_sites_url(v)[0]


def u_index(argv_value=None, site_value=None):
    """Which signed-in Google account opens the editor: the <N> in /u/<N>/.

    Most explicit first: an argument, then the /u/<N>/ in a pasted editor URL,
    then ADVISOR_U_INDEX, then 0 -- the first account, which is the only one on
    a browser signed in once. 0 is a safe default here because a wrong index
    opens the wrong account's editor, where the Site id then fails to load; it
    cannot write into another Site.
    """
    for v in (argv_value,
              _from_sites_url(site_value)[1] if site_value else None,
              os.environ.get("ADVISOR_U_INDEX")):
        if v not in (None, ""):
            if not str(v).isdigit():
                raise ConfigError("Account index must be a number (0, 1, ...); got %r." % (v,))
            return int(v)
    return 0
