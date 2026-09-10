#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIRECTORY=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIRECTORY/.." && pwd)
PROMPTS_DIR="$ROOT_DIR/documentation/prompts"
CURSOR_COMMANDS_DIR="$ROOT_DIR/.cursor/commands"
CLAUDE_COMMANDS_DIR="$ROOT_DIR/.claude/commands"
OPENCODE_COMMANDS_DIR="$ROOT_DIR/.opencode/commands"
SKILLS_DIR="$ROOT_DIR/.agents/skills"

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

relative_path() {
  printf '%s\n' "$1" | sed "s#^$ROOT_DIR/##"
}

read_generated_prompt_source() {
  sed -nE \
    's/^<!-- Auto-generated from (documentation\/prompts\/[^ ]+)( \(symlink not available\))? -->$/\1/p' \
    "$1" | head -n 1
}

remove_if_generated() {
  local file_path=$1 source=$2 reason=$3
  rm -f "$file_path"
  printf 'removed: %s (%s: %s)\n' "$(relative_path "$file_path")" "$reason" "$source"
}

cleanup_stale_generated_artifacts() {
  local directory entry source skill_entry skill_file
  for directory in "$CURSOR_COMMANDS_DIR" "$CLAUDE_COMMANDS_DIR" "$OPENCODE_COMMANDS_DIR"; do
    [[ -d $directory ]] || continue
    while IFS= read -r -d '' entry; do
      [[ $(basename "$entry") == *.md ]] || continue
      if [[ -L $entry ]]; then
        source=$(readlink "$entry")
        if [[ $source =~ ^../../documentation/prompts/[^/]+\.md$ && ! -e $entry ]]; then
          remove_if_generated "$entry" "$source" 'missing source'
        fi
        continue
      fi
      source=$(read_generated_prompt_source "$entry")
      if [[ -n $source && ! -e "$ROOT_DIR/$source" ]]; then
        remove_if_generated "$entry" "$source" 'missing source'
      fi
    done < <(find "$directory" -maxdepth 1 \( -type f -o -type l \) -print0)
  done

  [[ -d $SKILLS_DIR ]] || return 0
  for skill_entry in "$SKILLS_DIR"/*; do
    [[ -d $skill_entry ]] || continue
    skill_file="$skill_entry/SKILL.md"
    [[ -f $skill_file ]] || continue
    source=$(read_generated_prompt_source "$skill_file")
    [[ -n $source && ! -e "$ROOT_DIR/$source" ]] || continue
    rm -f "$skill_file"
    rmdir "$skill_entry" 2>/dev/null || true
    printf 'removed: %s (missing source)\n' "$(relative_path "$skill_entry")"
  done
}

link_or_copy() {
  local source=$1 destination=$2 relative_source
  relative_source="../../$(relative_path "$source")"
  rm -f "$destination"
  if ln -s "$relative_source" "$destination" 2>/dev/null; then
    printf 'linked:  %s -> %s\n' "$(relative_path "$destination")" "$relative_source"
  else
    {
      printf '<!-- Auto-generated from %s (symlink not available) -->\n\n' "$(relative_path "$source")"
      cat "$source"
    } > "$destination"
    printf 'copied:  %s <- %s\n' "$(relative_path "$destination")" "$(relative_path "$source")"
  fi
}

extract_description() {
  local description
  description=$(sed -nE 's/^description:[[:space:]]*(.*)$/\1/p' "$1" | head -n 1)
  [[ -n $description ]] || fail "Missing description in '$(relative_path "$1")'"
  printf '%s' "$description"
}

sync_skill() {
  local source=$1 name=$2 description=$3 skill_directory="$SKILLS_DIR/$2"
  mkdir -p "$skill_directory"
  {
    printf '%s\n' '---'
    printf 'name: %s\n' "$name"
    printf 'description: %s\n' "$description"
    printf '%s\n\n' '---'
    printf '<!-- Auto-generated from %s -->\n\n' "$(relative_path "$source")"
    cat "$source"
  } > "$skill_directory/SKILL.md"
  printf 'synced:  %s <- %s\n' "$(relative_path "$skill_directory/SKILL.md")" "$(relative_path "$source")"
}

[[ -d $PROMPTS_DIR ]] || fail "Prompts directory not found: $PROMPTS_DIR"
prompt_files=$(find "$PROMPTS_DIR" -maxdepth 1 -type f -name '*.md' ! -name 'README.md' -print | sort)
[[ -n $prompt_files ]] || fail "No prompts found in 'documentation/prompts/*.md'"

mkdir -p "$CURSOR_COMMANDS_DIR" "$CLAUDE_COMMANDS_DIR" "$OPENCODE_COMMANDS_DIR" "$SKILLS_DIR"
cleanup_stale_generated_artifacts

while IFS= read -r source; do
  name=$(basename "$source" .md)
  name=$(printf '%s' "$name" | sed 's/-prompt$//')
  description=$(extract_description "$source")
  link_or_copy "$source" "$CURSOR_COMMANDS_DIR/$name.md"
  link_or_copy "$source" "$CLAUDE_COMMANDS_DIR/$name.md"
  link_or_copy "$source" "$OPENCODE_COMMANDS_DIR/$name.md"
  sync_skill "$source" "$name" "$description"
done <<< "$prompt_files"
