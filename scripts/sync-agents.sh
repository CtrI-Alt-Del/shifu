#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIRECTORY=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIRECTORY/.." && pwd)
SOURCE_DIR="$ROOT_DIR/documentation/agents"
CODEX_DIR="$ROOT_DIR/.codex"
CODEX_AGENTS_DIR="$CODEX_DIR/agents"
OPENCODE_AGENTS_DIR="$ROOT_DIR/.opencode/agents"
CLAUDE_AGENTS_DIR="$ROOT_DIR/.claude/agents"
CODEX_CONFIG="$CODEX_DIR/config.toml"
CURRENT_BEGIN_MARKER='# BEGIN GENERATED AGENTS - scripts/sync-agents.sh'
CURRENT_END_MARKER='# END GENERATED AGENTS - scripts/sync-agents.sh'
LEGACY_BEGIN_MARKER='# BEGIN GENERATED AGENTS - scripts/sync-agents.mjs'
LEGACY_END_MARKER='# END GENERATED AGENTS - scripts/sync-agents.mjs'

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

relative_path() {
  printf '%s\n' "$1" | sed "s#^$ROOT_DIR/##"
}

trim() {
  printf '%s' "$1" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//'
}

toml_string() {
  local value
  value=$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')
  printf '"%s"' "$value"
}

parse_agent() {
  local agent_path=$1 relative_agent_path first_line expected_name body
  relative_agent_path=$(relative_path "$agent_path")
  first_line=$(head -n 1 "$agent_path" | trim)
  [[ $first_line == '---' ]] || fail "Missing YAML frontmatter in $relative_agent_path"
  grep -q -m 2 -E '^[[:space:]]*---[[:space:]]*$' "$agent_path" || \
    fail "Unclosed YAML frontmatter in $relative_agent_path"

  AGENT_NAME=$(awk '
    BEGIN { blocks = 0 }
    /^[[:space:]]*---[[:space:]]*$/ {
      blocks++
      if (blocks == 2) exit
      next
    }
    blocks == 1 && /^name:/ {
      sub(/^name:[[:space:]]*/, "")
      print
      exit
    }
  ' "$agent_path" | trim)
  AGENT_DESCRIPTION=$(awk '
    BEGIN { blocks = 0 }
    /^[[:space:]]*---[[:space:]]*$/ {
      blocks++
      if (blocks == 2) exit
      next
    }
    blocks == 1 && /^description:/ {
      sub(/^description:[[:space:]]*/, "")
      print
      exit
    }
  ' "$agent_path" | trim | sed -E 's/^"(.*)"$/\1/; s/^'\''(.*)'\''$/\1/')

  [[ -n $AGENT_NAME ]] || fail "Missing name in $relative_agent_path"
  [[ -n $AGENT_DESCRIPTION ]] || fail "Missing description in $relative_agent_path"
  expected_name=$(basename "$agent_path" .md)
  [[ $AGENT_NAME == "$expected_name" ]] || fail \
    "Agent name '$AGENT_NAME' must match filename '$expected_name' in $relative_agent_path"
  [[ $AGENT_NAME =~ ^[a-z0-9]+([a-z0-9-]*[a-z0-9])?$ ]] || \
    fail "Invalid agent name '$AGENT_NAME' in $relative_agent_path"

  body=$(awk '
    BEGIN { blocks = 0 }
    /^[[:space:]]*---[[:space:]]*$/ && blocks < 2 {
      blocks++
      next
    }
    blocks == 2 { lines[NR] = $0; count = NR }
    END {
      first = 1
      while (first <= count && lines[first] ~ /^[[:space:]]*$/) first++
      last = count
      while (last >= first && lines[last] ~ /^[[:space:]]*$/) last--
      for (i = first; i <= last; i++) print lines[i]
    }
  ' "$agent_path")
  [[ -n $(printf '%s' "$body" | tr -d '[:space:]') ]] || \
    fail "Missing agent instructions in $relative_agent_path"
  AGENT_BODY="$body"$'\n'
}

write_if_changed() {
  local file_path=$1 content=$2 managed_token=$3 temp_file
  temp_file=$(mktemp)
  printf '%s' "$content" > "$temp_file"
  if [[ -f $file_path ]]; then
    if cmp -s "$temp_file" "$file_path"; then
      rm -f "$temp_file"
      printf 'unchanged: %s\n' "$(relative_path "$file_path")"
      return
    fi
    if [[ -n $managed_token ]] && ! grep -Fq -- "$managed_token" "$file_path"; then
      rm -f "$temp_file"
      fail "Refusing to overwrite unmanaged file: $(relative_path "$file_path")"
    fi
  fi
  mkdir -p "$(dirname "$file_path")"
  mv "$temp_file" "$file_path"
  printf 'synced:    %s\n' "$(relative_path "$file_path")"
}

cleanup_stale() {
  local directory=$1 suffix=$2 valid_names=$3 entry filename name sample
  [[ -d $directory ]] || return 0
  while IFS= read -r -d '' entry; do
    filename=$(basename "$entry")
    [[ $filename == *"$suffix" ]] || continue
    name=$(basename "$filename" "$suffix")
    [[ $valid_names == *"|$name|"* ]] && continue
    sample=$(head -c 2048 "$entry" || true)
    [[ $sample == *'Auto-generated from documentation/agents/'* ]] || continue
    rm -f "$entry"
    printf 'removed:   %s\n' "$(relative_path "$entry")"
  done < <(find "$directory" -maxdepth 1 -type f -print0)
}

remove_generated_block() {
  local config=$1 begin_marker=$2 end_marker=$3 begin_count end_count
  begin_count=$(grep -oF "$begin_marker" <<< "$config" | wc -l | tr -d ' ')
  end_count=$(grep -oF "$end_marker" <<< "$config" | wc -l | tr -d ' ')
  [[ $begin_count == "$end_count" ]] || \
    fail "Unbalanced generated-agent markers in $(relative_path "$CODEX_CONFIG")"
  if [[ $begin_count == 0 ]]; then
    printf '%s' "$config"
    return
  fi
  awk -v begin="$begin_marker" -v end="$end_marker" '
    index($0, begin) { inside = 1; next }
    inside && index($0, end) { inside = 0; next }
    !inside { print }
  ' <<< "$config"
}

[[ -d $SOURCE_DIR ]] || fail "Agent source directory not found: $SOURCE_DIR"
mkdir -p "$CODEX_AGENTS_DIR" "$OPENCODE_AGENTS_DIR" "$CLAUDE_AGENTS_DIR"

agent_files=$(find "$SOURCE_DIR" -maxdepth 1 -type f -name '*-agent.md' -print | sort)
[[ -n $agent_files ]] || fail 'No agent definitions found in documentation/agents/*-agent.md'

valid_names='|'
while IFS= read -r agent_path; do
  parse_agent "$agent_path"
  valid_names="$valid_names$AGENT_NAME|"
done <<< "$agent_files"
cleanup_stale "$CODEX_AGENTS_DIR" '.toml' "$valid_names"
cleanup_stale "$OPENCODE_AGENTS_DIR" '.md' "$valid_names"
cleanup_stale "$CLAUDE_AGENTS_DIR" '.md' "$valid_names"

codex_roles=$CURRENT_BEGIN_MARKER
while IFS= read -r agent_path; do
  parse_agent "$agent_path"
  name=$AGENT_NAME
  description=$AGENT_DESCRIPTION
  body=$AGENT_BODY
  source_relative=$(relative_path "$agent_path")
  sandbox_mode='workspace-write'
  [[ $name == judge-* || $name == *-reviewer-agent ]] && sandbox_mode='read-only'

  codex_role=$(printf '# Auto-generated from %s\nmodel_instructions_file = %s\nsandbox_mode = %s\n' \
    "$source_relative" "$(toml_string "../../$source_relative")" "$(toml_string "$sandbox_mode")")
  write_if_changed "$CODEX_AGENTS_DIR/$name.toml" "$codex_role" \
    'Auto-generated from documentation/agents/'

  codex_roles="$codex_roles"$'\n\n'"[agents.$(toml_string "$name")]"$'\n'"description = $(toml_string "$description")"$'\n'"config_file = $(toml_string "agents/$name.toml")"

  if [[ $name == orchestrator-agent ]]; then
    opencode_mode='primary'
    opencode_permissions=$'  edit: allow\n  bash: allow\n  task: allow'
  elif [[ $name == judge-* ]]; then
    opencode_mode='subagent'
    opencode_permissions=$'  edit: deny\n  bash: deny\n  task: deny'
  elif [[ $name == *-reviewer-agent ]]; then
    opencode_mode='subagent'
    opencode_permissions=$'  edit: deny\n  bash: allow\n  task: deny'
  elif [[ $name == builder-agent ]]; then
    opencode_mode='subagent'
    opencode_permissions=$'  edit: allow\n  bash: allow\n  task: deny'
  else
    opencode_mode='subagent'
    opencode_permissions=$'  edit: allow\n  bash: allow\n  task: allow'
  fi

  opencode_agent=$(printf '%s\ndescription: %s\nmode: %s\npermission:\n%s\n---\n\n<!-- Auto-generated from %s -->\n\n%s' \
    '---' "$(toml_string "$description")" "$opencode_mode" "$opencode_permissions" \
    "$source_relative" "$body")
  write_if_changed "$OPENCODE_AGENTS_DIR/$name.md" "$opencode_agent" \
    'Auto-generated from documentation/agents/'

  claude_fields=$(printf '%s\nname: %s\ndescription: %s\n' \
    '---' "$name" "$(toml_string "$description")")
  if [[ $name == judge-* ]]; then
    claude_fields+=$'tools: Read, Glob, Grep\npermissionMode: plan\n'
  elif [[ $name == *-reviewer-agent ]]; then
    claude_fields+=$'disallowedTools: Write, Edit, Agent\n'
  elif [[ $name == builder-agent ]]; then
    claude_fields+=$'disallowedTools: Agent\n'
  fi
  claude_fields+="---"$'\n\n'"<!-- Auto-generated from $source_relative -->"$'\n\n'"$body"
  write_if_changed "$CLAUDE_AGENTS_DIR/$name.md" "$claude_fields" \
    'Auto-generated from documentation/agents/'
done <<< "$agent_files"

codex_roles="$codex_roles"$'\n\n'"$CURRENT_END_MARKER"$'\n'
existing_config=''
[[ -f $CODEX_CONFIG ]] && existing_config=$(<"$CODEX_CONFIG")
existing_config=$(remove_generated_block "$existing_config" "$LEGACY_BEGIN_MARKER" "$LEGACY_END_MARKER")
existing_config=$(remove_generated_block "$existing_config" "$CURRENT_BEGIN_MARKER" "$CURRENT_END_MARKER")
existing_config=$(printf '%s' "$existing_config" | sed -E ':a;N;$!ba;s/[[:space:]]+$//')
[[ -n $existing_config ]] && existing_config="$existing_config"$'\n\n'
write_if_changed "$CODEX_CONFIG" "$existing_config$codex_roles" ''
printf '%s\n' 'Configured agents for Codex, OpenCode and Claude Code.'
