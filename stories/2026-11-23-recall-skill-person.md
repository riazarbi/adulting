# recall answers questions about a person

Companion to `2026-11-23-search-person.md`, which added `search --person`
and `search person` and left the agent skill to a separate story.

## What is changing

`recall` routes every question by thread, type, date or text. Asked
"what's been going on with Jordan Blake?", it can only run `search notes
--text` and `search logs --text`: substring matches that can't tell a
meeting Jordan attended from a passing mention, and that miss nothing
but rank nothing either.

The skill gains person rows in its routing table:

| The owner asks | The agent calls |
|---|---|
| "everything with Jordan", "where are we with Jordan Blake" | `search person "Jordan Blake"` |
| "when did I last meet Dana" | `search notes --person "Dana Kim" --type Meeting --limit 1` |
| "what did Jordan and I discuss on Northwind" | `search notes --thread Northwind --person "Jordan Blake"` |
| "what's happened with Priya lately" | `search stream --person Priya` |
| "what is Omar meant to be doing" | not here: `task-workflow`, `tasks list --assignee` |

And a **People** section:

- **Pass the name as given.** `--person` resolves a full name, any case,
  or a unique part of one, such as a first name only one person has.
  Don't call `people list` first.
- **Ambiguous.** The error lists the candidates. If the conversation
  (the thread in question, an earlier message) settles which person,
  use them; otherwise ask, naming the candidates.
- **Not found.** The name has no person file. Say so, then fall back to
  `search notes --text` and `search logs --text`. Don't propose creating
  the person: recall is read-only.
- **Weigh `via`.** `link`, `assignee` and `attendee` mean the record is
  about the person. `text` is a mention of their full name. For "did I
  meet X", only a meeting note that has X as a link or attendee is
  evidence. First names and nicknames alone never match as `text`; when
  the owner's notes might use one, a `--text` search on it can find
  more, and the answer says that it was a looser search.
- **Search, then read** applies unchanged: `search person` returns
  pointers and counts, and content questions still need `read_file`.

The frontmatter `description` mentions people, so the skill loads for
person questions.

No other skill changes. `footguns`, `create-person`, `buffer-workflow`
and `task-workflow` resolve names with `people list` when *writing*,
which is unaffected.

`dev/agent-check` passes: every subcommand and flag named is real.
