#!/usr/bin/env bash
# shellcheck disable=SC2086,SC2034,SC2207

: "${TIMEOUT:=10}"
namespace=${NAMESPACE:-flux-system}
flux_source_repo=REPO

[ -z "$APP_NAME" ] && [ -z "$KUSTOMIZATION_NAME" ] && echo "error: APP_NAME and KUSTOMIZATION_NAME are empty" && exit 1
[ -z "$GITHUB_TOKEN" ] && echo "error: GITHUB_TOKEN is empty" && exit 1

kustomization_name=${KUSTOMIZATION_NAME:-$APP_NAME}

if [[ -f "./commit-sha.txt" ]]; then
  sha_from_file="$(cat ./commit-sha.txt)"

  wait_for_commit_sha1=$([ -n "$sha_from_file" ] && echo "$sha_from_file" || echo $DESIRED_RECONCILIATION_COMMIT)
fi

if [[ -z "$wait_for_commit_sha1" ]]; then
  echo "Deployment SHA not set - likely no changes to commit"
  exit 0
else
  echo "wait_for_commit_sha1 is: $wait_for_commit_sha1"
fi

for i in {1..10}; do
  # check if ks exists and condition ready + healthy
  if ! app_kustomization=$(kubectl get kustomization ${kustomization_name} -n $namespace -o json); then
    ready_message="Not found"
    ready_condition="Not found"
    healthy_condition="Not found"
  elif [[ $(echo "${app_kustomization}" | jq '.status.conditions') ==  "null" ]]; then
    echo "error: status.conditions is null"
    ready_message="No status conditions"
    ready_condition="No status conditions"
    healthy_condition="No status conditions"
  else
    ready_condition=$(jq -r '.status.conditions[] | select(.type == "Ready").status' <<<$app_kustomization)
    ready_message=$(jq -r '.status.conditions[] | select(.type == "Ready").message' <<<$app_kustomization)
    healthy_condition=$(jq -r '.status.conditions[] | select(.type == "Healthy").status' <<<$app_kustomization)
  fi

  echo "kustomization ${kustomization_name} in namespace $namespace Condition is Ready: $ready_condition, Healthy: $healthy_condition"
  # if ks ready, check last applied sha1
  if [[ "${ready_condition}" == "True" && "${healthy_condition}" == "True" ]]; then
    last_applied_sha=$(jq -r '.status.lastAppliedRevision | split(":")[1]' <<<$app_kustomization)

    # find out if the commit we are waiting for is ahead or behind the last applied sha
    if ! result=$(curl --fail-with-body -sS -L -H "Accept: application/vnd.github+json" -H "Authorization: Bearer $GITHUB_TOKEN" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "https://api.github.com/repos/$flux_source_repo/compare/$last_applied_sha...$wait_for_commit_sha1"); then
      echo "error: failed to query github apt when comparing commits $last_applied_sha to $wait_for_commit_sha1"
      echo "error: $result"
      exit 1
    fi
    wait_for_commit_sha1_status=$(jq -r '.status' <<<$result)
    echo "deployment sha is: $wait_for_commit_sha1 and is $wait_for_commit_sha1_status compared to last applied sha $last_applied_sha"

    if [[ ${wait_for_commit_sha1_status} != "ahead" ]]; then
      echo "${kustomization_name} is ready"

      success=true
      break
    fi
  fi
  echo "Kustomization status: $ready_message, waiting $TIMEOUT seconds..."
  sleep $TIMEOUT
done

# if flux kustomization status never became READY
if [[ ! $success ]]; then
  echo "error: time-out waiting for ${kustomization_name} STATUS to be deployed"
  kubectl get kustomization ${kustomization_name} -n $namespace
  exit 1
fi
