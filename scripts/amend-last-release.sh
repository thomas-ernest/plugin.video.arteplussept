#!/usr/bin/env bash
set -euo pipefail

REMOTE_ID=origin
RELEASE_BRANCH=master
TAG_PATTERN='^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

echo "=== Amend the latest Arte+7 release ==="

if [ "$#" -ne 0 ]; then
    fail "This script does not accept arguments."
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    fail "Run this script from inside the Git repository."
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "$RELEASE_BRANCH" ]; then
    fail "Releases must be amended from $RELEASE_BRANCH (current branch: $CURRENT_BRANCH)."
fi

git remote get-url "$REMOTE_ID" >/dev/null 2>&1 \
    || fail "Git remote '$REMOTE_ID' does not exist."

echo "Fetching $REMOTE_ID/$RELEASE_BRANCH and remote tags..."
git fetch "$REMOTE_ID" \
    "+refs/heads/$RELEASE_BRANCH:refs/remotes/$REMOTE_ID/$RELEASE_BRANCH" \
    --tags

HEAD_COMMIT=$(git rev-parse HEAD)
REMOTE_MASTER_COMMIT=$(git rev-parse "refs/remotes/$REMOTE_ID/$RELEASE_BRANCH")
if [ "$HEAD_COMMIT" != "$REMOTE_MASTER_COMMIT" ]; then
    fail "Local HEAD must match $REMOTE_ID/$RELEASE_BRANCH before amending a release.
Local:  $HEAD_COMMIT
Remote: $REMOTE_MASTER_COMMIT"
fi

REMOTE_TAG_REFS=$(git ls-remote --tags --refs "$REMOTE_ID") \
    || fail "Unable to list tags from '$REMOTE_ID'."
REMOTE_TAGS=$(printf '%s\n' "$REMOTE_TAG_REFS" \
    | awk '{ sub("refs/tags/", "", $2); print $2 }' \
    | grep -E "$TAG_PATTERN" \
    | sort -V || true)
TAG=$(printf '%s\n' "$REMOTE_TAGS" | tail -n 1)
if [ -z "$TAG" ]; then
    fail "No remote tag matching vMAJOR.MINOR.BUGFIX was found."
fi

REMOTE_TAG_OBJECT=$(printf '%s\n' "$REMOTE_TAG_REFS" \
    | awk -v tag="refs/tags/$TAG" '$2 == tag { print $1; exit }')
if [ -z "$REMOTE_TAG_OBJECT" ]; then
    fail "Unable to determine the remote object for tag '$TAG'."
fi
LOCAL_TAG_OBJECT=$(git rev-parse "refs/tags/$TAG" 2>/dev/null) \
    || fail "Latest remote tag '$TAG' is not available locally after fetching."
if [ "$LOCAL_TAG_OBJECT" != "$REMOTE_TAG_OBJECT" ]; then
    fail "Local tag '$TAG' differs from its remote tag. Resolve the mismatch before continuing."
fi

OLD_COMMIT=$(git rev-parse "$TAG^{commit}")
if [ "$HEAD_COMMIT" = "$OLD_COMMIT" ]; then
   fail "HEAD already points to the latest release tag '$TAG' ($HEAD_COMMIT)."
fi
OLD_COMMIT_DATE=$(git show -s --format=%cI "$OLD_COMMIT")
OLD_COMMIT_SUBJECT=$(git show -s --format=%s "$OLD_COMMIT")
HEAD_COMMIT_DATE=$(git show -s --format=%cI "$HEAD_COMMIT")
HEAD_COMMIT_SUBJECT=$(git show -s --format=%s "$HEAD_COMMIT")

TAG_MESSAGE=$(git for-each-ref --format='%(contents)' "refs/tags/$TAG")
if [ -z "$TAG_MESSAGE" ]; then
    TAG_MESSAGE="Amended release $TAG"
fi

cat <<EOF

The GitHub release and tag '$TAG' will move:
    from: $OLD_COMMIT
        commit date: $OLD_COMMIT_DATE
        subject:     $OLD_COMMIT_SUBJECT
    to:   $HEAD_COMMIT
        commit date: $HEAD_COMMIT_DATE
        subject:     $HEAD_COMMIT_SUBJECT

This deletes the remote release, remote tag, and local tag, then recreates
the same annotated tag at the current HEAD and force-pushes that tag.
Pushing the tag can trigger the release workflow again.
EOF

read -r -p "Proceed? [y/N] " CONFIRM
case "$CONFIRM" in
    [yY]|[yY][eE][sS])
        ;;
    *)
        echo "Cancelled; no release or tag was changed."
        exit 0
        ;;
esac

if ! command -v gh >/dev/null 2>&1; then
    fail "GitHub CLI 'gh' is not installed or is not on PATH."
fi

if ! gh auth status --hostname github.com; then
    fail "GitHub CLI is not authenticated. Run 'gh auth login' and try again."
fi

if ! gh release view "$TAG" >/dev/null 2>&1; then
    fail "GitHub release '$TAG' could not be found or accessed."
fi

echo "Deleting GitHub release '$TAG' and its remote tag..."
REMOTE_URL=$(git remote get-url "$REMOTE_ID")
gh release delete "$TAG" --cleanup-tag --yes --repo "$REMOTE_URL"

echo "Deleting local tag '$TAG'..."
git tag --delete "$TAG"

echo "Recreating annotated tag '$TAG' at $HEAD_COMMIT..."
git tag --annotate --message "$TAG_MESSAGE" "$TAG" "$HEAD_COMMIT"

echo "Force-pushing amended tag '$TAG' to $REMOTE_ID..."
git push --force "$REMOTE_ID" "refs/tags/$TAG"

echo "=== Release '$TAG' now points to $HEAD_COMMIT ==="
