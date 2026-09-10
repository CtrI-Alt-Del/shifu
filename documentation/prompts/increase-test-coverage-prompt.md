---
name: increase-test-coverage
description: Improve meaningful Shifu test coverage without changing behavior.
---

# Increase test coverage

This is maintenance only while behavior is unchanged. Read selected test/layer
rules, manifests/configuration, code, and tests. If a gap requires behavior or
contract changes, stop and use SDD.

Establish a baseline using commands that exist. Build scenarios for observable
success, validation, authorization, failure, state transition, persistence, and
recovery. Use the smallest permitted boundary and repository fixtures.

Never lower thresholds, weaken tests, assert private details, add sleeps or
meaningless assertions, commit coverage output, or change production behavior
to inflate metrics. Follow widget/accessibility rules for web tests.

Run focused then applicable broader gates. Report commands, before/after metrics
when available, behavior proven, remaining gaps, and defects needing SDD/Jira.

