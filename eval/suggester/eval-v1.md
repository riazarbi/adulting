# Capture suggester — eval set v1

Raw capture strings + ground-truth structured commands, for evaluating the
`buffer suggest "..."` feature. ~20 in-scope + 5 out-of-scope cases drawn
from real `~/.adulting/logs/` content and reverse-engineered into plausible
"what Riaz would actually type" raw input.

**Edit me freely.** Reject any case that doesn't match how you'd capture in
practice; replace with your own. Each case ships with the *dimensions* it
tests so coverage gaps are visible.

## Today's date for this eval
`2026-05-19` (Tuesday)

## Reference: thread enum

```
Processes/Arbi Family Trust
Processes/Equal Experts
Processes/FAMCO
Processes/Journal
Processes/Personal Finance
Processes/SGB
Processes/Toil
Processes/Wellness
Projects/Agent
Projects/Antirank
Projects/AXA DORA
Projects/Discover Africa Group
Projects/Homephone
Projects/John Lewis Experimentation
Projects/SANA Partners
Projects/Solid Insight
Projects/Syncro EV
Projects/Zeke
Topics/Agentic Engineering
Topics/Data Engineering
Topics/Relationships
```

## Reference: person enum (subset relevant to eval)

`Alec Little, Bern Sellmeyer, Chris Storey, Eddie van der Weide, Lexi Van Kets, Nick Hudson, Ralph van Niekerk, Riaz Arbi, Sylvia Klopper`

(Full list in `~/.adulting/people/`.)

---

## In-scope cases (1–20)

### Case 1 — explicit thread keyword, simple action
- **Raw:** `book caddy service for next week`
- **Expected:** `buffer add-action "Processes/Toil" "Book Caddy Service" --scheduled 2026-05-26`
- **Tests:** thread (unique keyword "Caddy"→Toil per logs), date ("next week"→Monday 2026-05-26 by convention), action verb
- **Notes:** "next week" is ambiguous — could be Monday, end-of-week, etc. Either is defensible; pick the convention you want.

### Case 2 — strong thread signal via rare term
- **Raw:** `Forward Bern email on Symonds Lease`
- **Expected:** `buffer add-action "Processes/SGB" "Forward [[people/Bern Sellmeyer]] email on Symonds Lease"`
- **Tests:** thread (rare term "Symonds" uniquely SGB), person (Bern→Bern Sellmeyer in SGB context), action
- **Notes:** the canonical "hard case" from the design discussion. Without "Symonds", "Bern" alone is ambiguous (see Case 11). Body uses the in-body wikilink form (not assignee-prefix `(...)`) because Bern is the *subject* of the email, not the assignee of the task.

### Case 3 — person fully named, action
- **Raw:** `drop off vacuum switch with Eddie van der Weide`
- **Expected:** `buffer add-action "Projects/Syncro EV" "drop off vacuum switch with [[people/Eddie van der Weide]]"`
- **Tests:** person (exact), thread (Eddie ↔ Syncro EV per logs)

### Case 4 — first name only, unambiguous person
- **Raw:** `drop off vacuum switch with Eddie`
- **Expected:** `buffer add-action "Projects/Syncro EV" "drop off vacuum switch with [[people/Eddie van der Weide]]"`
- **Tests:** person fuzzy (unique first-name match), same thread inference as Case 3

### Case 5 — past-tense observation → TEXT not ACTION
- **Raw:** `Sent Lexi instructions for SIP on Zoiper`
- **Expected:** `buffer add-text "Projects/Homephone" "Sent [[people/Lexi Van Kets]] instructions for SIP on Zoiper"`
- **Tests:** action-vs-text (past-tense ⇒ TEXT), person fuzzy (Lexi→Lexi Van Kets), thread (Zoiper/SIP→Homephone)

### Case 6 — URL capture into topic thread
- **Raw:** `read https://stormatics.tech/blogs/postgresql-is-not-slow-your-queries-are`
- **Expected:** `buffer add-action "Topics/Data Engineering" "Read https://stormatics.tech/blogs/postgresql-is-not-slow-your-queries-are"`
- **Tests:** thread (postgresql→Data Engineering, weak signal), URL preserved verbatim, action verb "read"

### Case 7 — relative date "next tuesday"
- **Raw:** `Take Maya for dinner next tuesday`
- **Expected:** `buffer add-action "Topics/Relationships" "Take Maya for dinner" --scheduled 2026-05-26`
- **Tests:** date parsing ("next tuesday" from 2026-05-19 Tue = 2026-05-26), thread (Maya is family → Relationships, *no keyword match available* — this is hard for rules!)
- **Notes:** "Maya" not in people/ (informal family reference). The thread inference here has no textual hook; this case is intentionally hard and may push to UNKNOWN.

### Case 8 — date "tomorrow"
- **Raw:** `Call mom tomorrow`
- **Expected:** `buffer add-action "Topics/Relationships" "Call mom" --scheduled 2026-05-20`
- **Tests:** date ("tomorrow"), thread (same difficulty as Case 7)

### Case 9 — REF entry
- **Raw:** `link my code review meeting note to SANA`
- **Expected:** `buffer add-ref "Projects/SANA Partners" "notes/2026-05-13-08-29-18" "Code Review Meeting 1"`
- **Tests:** intent classification (REF, not TEXT/ACTION), thread (SANA→SANA Partners), note resolution (would need to grep notes/ for "Code Review Meeting")
- **Notes:** REF is the hardest intent to detect from prose. Verb cues: "link", "see also", "this connects to".

### Case 10 — long observation, no action
- **Raw:** `Had a really bad morning, super overwhelmed and stressed. Took my meds anyway and clawed back.`
- **Expected:** `buffer add-text "Processes/Wellness" "Had a really bad morning, super overwhelmed and stressed. Took my meds anyway and clawed back."`
- **Tests:** thread (wellness keywords "meds", "overwhelmed"), action-vs-text (no imperative → TEXT)

### Case 11 — ambiguous person, weak thread signal
- **Raw:** `Bern called about the fund`
- **Expected:** `buffer add-text "Processes/SGB" "[[people/Bern Sellmeyer]] called about the fund"` *(or)* `buffer add-text "Projects/SANA Partners" ...`
- **Tests:** person resolution (Bern is uniquely Bern Sellmeyer in people/), thread *ambiguity* (Bern appears in both SGB and SANA Partners) — suggester should probably pick the most recent context, or escalate to UNKNOWN
- **Notes:** the "what does a tied thread score do?" case.

### Case 12 — action with explicit assignee marker
- **Raw:** `Ralph: sign the AFS`
- **Expected:** `buffer add-action "Processes/SGB" "(Ralph van Niekerk) sign the AFS"`
- **Tests:** assignee inference (colon syntax), person fuzzy (Ralph→Ralph van Niekerk), thread (AFS→SGB)

### Case 13 — multi-word thread name
- **Raw:** `oreilly ado course - DORA research`
- **Expected:** `buffer add-action "Projects/AXA DORA" "Research DORA via oreilly ado"`
- **Tests:** thread (multi-word "AXA DORA"), body restructuring vs verbatim (this case prefers light cleanup)
- **Notes:** if your preference is verbatim ("don't fix grammar"), the body stays `oreilly ado course - DORA research`.

### Case 14 — short body, imperative
- **Raw:** `Fit aircon`
- **Expected:** `buffer add-action "Projects/Syncro EV" "Fit aircon"`
- **Tests:** thread (aircon→EV context only by prior logs; weak), action verb at start

### Case 15 — content-rich TEXT with embedded link
- **Raw:** `nice HN comment on tool-calling, the conclusion is to move from LLMs at run time to LLMs to write software. https://news.ycombinator.com/item?id=48051916`
- **Expected:** `buffer add-text "Projects/Agent" "nice HN comment on tool-calling, the conclusion is to move from LLMs at run time to LLMs to write software. https://news.ycombinator.com/item?id=48051916"`
- **Tests:** thread (tool-calling/agentic→Agent project), URL preservation, TEXT classification

### Case 16 — explicit due date
- **Raw:** `Sign up for Camps Bay Squash Club by Friday`
- **Expected:** `buffer add-action "Processes/Wellness" "Sign up for Camps Bay Squash Club" --due 2026-05-22`
- **Tests:** thread (Squash→Wellness), date ("Friday" from 2026-05-19 Tue = 2026-05-22), `--due` vs `--scheduled` distinction ("by Friday" ⇒ due)

### Case 17 — action with no thread keyword at all
- **Raw:** `Buy vodacom sim card`
- **Expected:** `buffer add-action "Projects/Agent" "Buy vodacom sim card"`  *(or UNKNOWN)*
- **Tests:** thread (no keyword resolves; recent log was Projects/Agent but that's not in the input itself)
- **Notes:** intentionally underspecified — rules-only will likely fail; we want to see the failure mode.

### Case 18 — quick capture missing both thread cue and person cue
- **Raw:** `pick up dry cleaning`
- **Expected:** `buffer add-action "Processes/Toil" "pick up dry cleaning"`
- **Tests:** thread (Toil is the catch-all errand thread by convention — rules would need to learn this)
- **Notes:** semantically a "Toil" case, but the input has no token that maps to "Toil". Tests the catch-all fallback.

### Case 19 — explicit priority cue
- **Raw:** `URGENT: reach out to Sylvia Klopper on fundraising`
- **Expected:** `buffer add-action "Processes/SGB" "reach out to [[people/Sylvia Klopper]] on fundraising" --priority H`
- **Tests:** priority detection from "URGENT", person fuzzy (Sylvia→Sylvia Klopper), thread (Sylvia + fundraising→SGB per logs)

### Case 20 — first-person observation, technical, into Projects/Agent
- **Raw:** `Refactor tools json so it matches needle format`
- **Expected:** `buffer add-action "Projects/Agent" "refactor tools json for compatibility with needle json format"`
- **Tests:** thread (needle/json/tools→Agent), action vs text (imperative → action)

---

## Out-of-scope cases (21–25)

For these the *correct* suggester behavior is **route to UNKNOWN** (i.e., decline to suggest a structured command). Tests the "don't try to be a hero" guard.

### Case 21 — create-person intent (different command entirely)
- **Raw:** `create a person file for Joel Pfaff at AXA`
- **Expected:** `buffer add "create a person file for Joel Pfaff at AXA"` *(UNKNOWN — out of scope)*
- **Tests:** out-of-scope detection (this is a `people new` intent, not a buffer capture)

### Case 22 — query/read intent
- **Raw:** `show me overdue tasks`
- **Expected:** `buffer add "show me overdue tasks"` *(UNKNOWN — out of scope)*
- **Tests:** out-of-scope (this is `tasks list`, not a capture)

### Case 23 — new thread intent
- **Raw:** `start a new thread for the Discover Africa rebrand`
- **Expected:** `buffer add "start a new thread for the Discover Africa rebrand"` *(UNKNOWN — but "Discover Africa Group" exists; risk of false-positive routing)*
- **Tests:** out-of-scope vs false-positive thread match (rules might happily route to `Projects/Discover Africa Group` — we want to see if it does)

### Case 24 — pure question, no capture intent
- **Raw:** `what's on my schedule today`
- **Expected:** `buffer add "what's on my schedule today"` *(UNKNOWN — out of scope)*
- **Tests:** intent classification (question != capture)

### Case 25 — garbage / empty / single word
- **Raw:** `asdf`
- **Expected:** `buffer add "asdf"` *(UNKNOWN — no structure inferable)*
- **Tests:** graceful degradation on garbage input

---

## Explicit-thread cases (26–27)

When the user types an explicit `Kind/Name` thread directive into the input, it overrides BM25 ranking entirely — no guessing, no confidence guard. This is the reliable escape hatch for any capture the ranker would otherwise get wrong.

### Case 26 — trailing directive, wrong kind, month date
- **Raw:** `Have a date night with Maya before June - processes/relationships`
- **Expected:** `buffer add-action "Topics/Relationships" "Have a date night with Maya" --due 2026-06-01`
- **Tests:** explicit thread honored; **kind correction** (user typed `processes/` but the thread is `Topics/Relationships` — resolution is by name, kind is just a gate); `before June` → `--due 2026-06-01`; directive + ` - ` separator stripped from body
- **Notes:** this is the reverse-engineered fix for a real user-testing failure. Without the directive the ranker sends "date night" to SGB (no keyword hook for Relationships) — that's the rules ceiling, and the explicit directive is the workaround.

### Case 27 — inline wikilink directive
- **Raw:** `fix the rear door [[Projects/Syncro EV]]`
- **Expected:** `buffer add-action "Projects/Syncro EV" "fix the rear door"`
- **Tests:** `[[Kind/Name]]` wikilink form recognised inline; multi-word thread name; wikilink wrapper stripped from body

---

## Scoring rubric

For each case, the suggester output is scored on five dimensions (each pass/fail):

1. **JSON/shape valid** — output parseable as a `buffer <subcmd> ...` invocation
2. **Subcommand correct** — `add` vs `add-text` vs `add-ref` vs `add-action` matches expected
3. **Thread correct** — resolves to the expected thread (or correctly bails to UNKNOWN)
4. **Person correct** — assignee + body wikilinks match expected; absent if no person
5. **Dates correct** — `--due` / `--scheduled` values match expected ISO date; absent if none

Aggregate metrics:
- **Full match rate** = % cases where all 5 dimensions pass
- **Per-dimension accuracy** = each dim individually
- **Out-of-scope precision** = % of cases 21–25 that correctly route to UNKNOWN

Pass bar for Stage 1 (rules-only) → ship:
- Full match ≥ 70% on cases 1–20
- Thread accuracy ≥ 80% on cases 1–20
- Out-of-scope precision ≥ 80% on cases 21–25 (we want to *not* hallucinate routing for non-captures)

Below pass bar → escalate to Stage 2 (needle) per the verification plan.
