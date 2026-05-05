---
schema: action_item
scope: line
applies_when: line =~ ^- \[[ x]\]
shape: ^- \[(?P<status>[ x])\] (?P<key>[A-Z0-9]{5})(?: \((?P<assignee>[^)]+)\))? (?P<text>.+)$
---

# Action item

A single checkbox action item line within a note body. Indexed and managed by the `actions` command.

## Fields

| name     | required | type   | constraint                              |
|----------|----------|--------|-----------------------------------------|
| status   | yes      | enum   | " ", x                                  |
| key      | yes      | string | regex=[A-Z0-9]{5}; must_contain_digit   |
| assignee | no       | string |                                         |
| text     | yes      | string | min=1                                   |

## Examples

```
- [ ] AB12C Send the invite
- [x] 7H3K9 (Riaz) Approve the design doc
```
