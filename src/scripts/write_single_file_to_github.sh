#!/usr/bin/env bash

# Script: Use curl to write a single file to github repo

# export ORG=$1
# export REPO=$2
# export SOURCEFILE=$3
# export UPDATEDFILE=$4
# export APPS=environments/versions.json

echo "debug:"
echo "ORG: ${ORG}"
echo "REPO: ${REPO}"
echo "SOURCEFILE: ${SOURCEFILE}"
echo "UPDATEDFILE: ${UPDATEDFILE}"

# response=$(curl -L \
#     -H "Accept: application/vnd.github+json" \
#     -H "Authorization: Bearer $GITHUB_TOKEN" \
#     -H "X-GitHub-Api-Version: 2022-11-28" \
#     https://api.github.com/repos/${ORG}/${REPO}/contents/${SOURCEFILE})

# sha=$(echo $response | jq -r .sha)
# newcontents=$(cat $UPDATEDFILE | base64)

# response=$(curl -L \
#     -X PUT \
#     -H "Accept: application/vnd.github+json" \
#     -H "Authorization: Bearer $GITHUB_TOKEN" \
#     -H "X-GitHub-Api-Version: 2022-11-28" \
#     https://api.github.com/repos/${ORG}/${REPO}/contents/${SOURCEFILE} \
#     --data @- <<EOF
# {
#   "message": "push from di-global-service-metrics-server build ${CIRCLE_BUILD_NUM}",
#   "sha": "${sha}",
#   "content": "${newcontents}"
# }
# EOF)
