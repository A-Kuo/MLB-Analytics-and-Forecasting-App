"""Per-team news source configuration for scripts/ingest_team_news.py.

**Source verification record -- read this before adding a source.** Austin
supplied a reference design covering 7 sources (SB Nation, MLB.com, ESPN,
SI, Fox Sports, Yahoo Sports, Twitter). Each was checked live against this
environment before being included here; only two passed:

- **MLB.com** -- works. Per-team RSS feed (macroservice.teams.team_news_rss_url),
  already built and used by the Insights page's earlier per-team news work.
- **SB Nation** -- works. Every team's blog publishes a real, current Atom
  feed at ``{blog_url}/rss/index.xml`` -- confirmed live on 6 different
  team blogs (Pinstripe Alley, Over the Monster, McCovey Chronicles,
  Bluebird Banter, Royals Review, AZ Snake Pit), all returning HTTP 200
  with real dated articles.

Deferred, NOT implemented -- do not re-add without re-verifying first:

- **ESPN** and **SI** -- a plain ``requests.get`` to either team-page URL
  gets a TLS-level connection reset from this environment (``Recv failure:
  Connection was reset``), consistent with bot-blocking a datacenter IP.
  A GitHub Actions runner is very likely to hit the same wall.
- **Fox Sports** -- the team page itself loads fine (HTTP 200, real
  content), but none of the three CSS selectors from the reference script
  (``article-list-item``, ``b-article-card``, plain ``<article>``) appear
  anywhere in its current markup -- would silently upsert zero articles
  on every single run, with no visible failure.
- **Yahoo Sports** -- the reference script's assumed URL pattern
  (``sports.yahoo.com/mlb/teams/{slug}/``) returns 404; the slug format
  has changed since that pattern was written.
- **Twitter** -- the reference script's "fetch" was a static placeholder
  link ("Latest updates from official @handle on X"), not a real fetch of
  any actual tweet content. There is no real source here to defer to; a
  real integration would need to be designed from scratch.
"""
from __future__ import annotations

# team_id -> SB Nation team blog base URL. Reconciled from Austin's
# name-keyed reference dict to this app's team_id-keyed convention (see
# macroservice/teams.py's TEAM_BY_ID) -- his dict used "Oakland Athletics"/
# "oakland-athletics-team", which is stale; this app's teams.json already
# renamed that franchise to "Athletics" (id 133) after the Sacramento
# relocation.
SBNATION_URLS: dict[int, str] = {
    108: "https://www.halosheaven.com",  # Angels
    109: "https://www.azsnakepit.com",  # Diamondbacks
    110: "https://www.camdenchat.com",  # Orioles
    111: "https://www.overthemonster.com",  # Red Sox
    112: "https://www.bleedcubbieblue.com",  # Cubs
    113: "https://www.redreporter.com",  # Reds
    114: "https://www.coveringthecorner.com",  # Guardians
    115: "https://www.purplerow.com",  # Rockies
    116: "https://www.blessyouboys.com",  # Tigers
    117: "https://www.crawfishboxes.com",  # Astros
    118: "https://www.royalsreview.com",  # Royals
    119: "https://www.truebluela.com",  # Dodgers
    120: "https://www.federalbaseball.com",  # Nationals
    121: "https://www.amazinavenue.com",  # Mets
    133: "https://www.athleticsnation.com",  # Athletics
    134: "https://www.bucsdugout.com",  # Pirates
    135: "https://www.gaslampball.com",  # Padres
    136: "https://www.lookoutlanding.com",  # Mariners
    137: "https://www.mccoveychronicles.com",  # Giants
    138: "https://www.vivaelbirdos.com",  # Cardinals
    139: "https://www.draysbay.com",  # Rays
    140: "https://www.lonestarball.com",  # Rangers
    141: "https://www.bluebirdbanter.com",  # Blue Jays
    142: "https://www.twinkietown.com",  # Twins
    143: "https://www.thegoodphight.com",  # Phillies
    144: "https://www.batterypower.com",  # Braves
    145: "https://www.southsidesox.com",  # White Sox
    146: "https://www.fishstripes.com",  # Marlins
    147: "https://www.pinstripealley.com",  # Yankees
    158: "https://www.brewcrewball.com",  # Brewers
}

# Lower number = higher priority, i.e. shown first / kept over a duplicate
# from a lower-priority source (Austin's own ranking -- fan-blog analysis
# outranks MLB.com's own PR-flavored team coverage).
SOURCE_PRIORITY: dict[str, int] = {
    "SBNation": 1,
    "MLB": 2,
}
