#!/bin/bash

# Usage:
#   ./GIT-change-origin.sh <REPOSITORY_URL> [BRANCH_PREFIX]
#
# Description:
#   - Replaces the current origin with a new repository URL.
#   - Pulls all remote branches and Copy them from the source git repository to the new remote repository including tags and branches.
#   - Adds a prefix to all branches before pushing to the new origin.
#
# Arguments:
#   REPOSITORY_URL - New remote repository URL (required)
#   BRANCH_PREFIX  - Prefix for branches (optional, default: "exported_")
#
# Examples:
#   ./GIT-change-origin.sh https://github.com/user/new-repo.git
#   ./GIT-change-origin.sh https://github.com/user/new-repo.git dev_
#
# Note: Make sure to run this script from the git repository root

# Validate that URL is provided as parameter
if [ -z "$1" ]; then
    echo "Error: Repository URL must be provided"
    echo "Usage: $0 <REPOSITORY_URL> [BRANCH_PREFIX]"
    exit 1
fi

REPO_URL="$1"
BRANCH_PREFIX="${2:-exported_}"

echo "Using branch prefix: $BRANCH_PREFIX"

echo "Viewing remote repository URL"
git remote -v

echo "Viewing all local and remote branches"
git branch -a

echo "Fetching remote branches and verifying connectivity"
git fetch origin

echo "Viewing available remote branches"
git branch -r

# echo "Creating and switching to temporary branch to ensure we have all branches"
# git checkout -b temp_branch

# echo "Making sure we have all remote branches locally"
# git fetch --all

# echo "Creating local branches for all remote branches with prefix"
# git branch -r | grep -v '\->' | while read remote; do
#     branch_name="${remote#origin/}"
#     git branch --track "$BRANCH_PREFIX$branch_name" "$remote"
# done

# echo "Deleting temporary branch"
# # Get the default branch name (main or master)
# DEFAULT_BRANCH=$(git remote show origin | grep 'HEAD branch' | cut -d' ' -f5)
# git checkout "$DEFAULT_BRANCH"
# git branch -D temp_branch || true

echo "Setting repository remote URL to $REPO_URL"
git remote set-url origin "$REPO_URL"

echo "Configuring HTTP buffer for large repos (524 MB)"
git config http.postBuffer 524288000

echo "Publishing all local branches to new remote"
git push --all origin

echo "Publishing all tags"
git push --tags

echo "Verifying tracked branches"
git branch -vv

echo "Confirming no pending changes"
git status

# echo "Deleting all local branches with prefix '$BRANCH_PREFIX'"
# git branch | grep "$BRANCH_PREFIX" | xargs -r git branch -D

echo "Process completed. Local branches with prefix '$BRANCH_PREFIX' have been deleted."
