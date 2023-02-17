
## Coding guidelines

- 4 space indentation. No tab.
- Snake case for variables and methods
- No parenthesis around keywords like if, elif, for, while...
- Spaces around = when used in body and script. No space around = when setting method parameters
- Double quotes for strings used to end_users or logs.
- Single quotes for dict indices and strings for internal purpose.

## Bump new version

- Add details of the news version in CHANGELOG.md. Do not touch changelog.txt. It is here for legacy purpose.
- Set the version Maj.Min.Bug (without v) in addon.xml /addon/@version 
- Optionally update highlight changes in addon.xml /addon/extension[@point="xbmc.addon.metadata"]/news. Ensure it counts less than 1500 chars.
- Create a commit with version bump
    - git add addon.xml CHANGELOG.md && git commit -m "Bump version to Maj.Min.Bug"
- Create and push tag "vMaj.Min.Bug" (with v) in git.
    - git tag -a vMaj.Min.Bug
    - git push origin --tags
- Create a release in GitHub with name Maj.Min.Bug (without v). Reuse CHANGELOG.md details as description.