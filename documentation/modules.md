# Business Modules

Shifu is divided into six cohesive business modules. Each module owns its
domain rules, use cases, persistence adapters, application endpoints, and
user-facing experience. Modules exchange identifiers, explicit contracts, and
business events; they must not import another module's internal entities,
repositories, database models, or implementation details.

The MVP serves one user type: the individual learner. The product is private,
responsive on desktop and mobile, accessible, and presented in pt-BR.

Each module's canonical PRD is maintained as a dedicated page under the [PRD's
Confluence page](https://joaogoliveiragarcia.atlassian.net/wiki/x/AYDvB). The
Google Docs remain origin/reference material; when they disagree, use the current
Confluence page and surface the conflict.

## Identity

Identity owns the user's account and access to Shifu. It is responsible for:

- account creation, e-mail confirmation, sign-in, and password recovery/change;
- authenticated sessions, including signing out of the current or all devices;
- the basic profile, display name, account status, and current time zone; and
- exposing a trusted account identity to protected modules and coordinating
  account deletion across the product.

Only active accounts may use Learning, Intelligence, Gamification, or other
protected areas. Identity is authoritative for who the user is, but each other
module remains responsible for its own user-owned data. Account deletion is
definitive from the user's perspective: dependent modules must make their data
inaccessible before deletion is considered complete.

Identity does not own social login, e-mail changes, two-factor authentication,
roles, advanced device management, or temporary account deactivation in the
MVP.

Identity decides when account communications are required, whether the user is
eligible to receive them, and owns the tokens, validity periods, resend limits,
and account-state changes involved. Communication owns composition and delivery
of the resulting transactional messages.

Canonical PRD: [Confluence page](https://joaogoliveiragarcia.atlassian.net/wiki/x/AYDyB) · Origin: [Google Doc](https://docs.google.com/document/d/1kjAyA7kWU4i9PDEYf7jMuNgyoVVzWrnO0H0-UYa4GN0/edit)

## Communication

Communication owns reliable delivery of transactional messages requested by
authorized Shifu modules. The MVP supports e-mail for Identity's account
confirmation and password-recovery journeys. It is responsible for:

- the controlled catalog and pt-BR composition of transactional messages;
- asynchronous delivery, retry behavior, and idempotent processing;
- delivery-state tracking, permanent-failure reporting, and operational
  metadata; and
- protecting message data and removing active account associations after
  account deletion.

The requesting module remains authoritative for why and when a communication
exists, recipient eligibility, business cooldowns, tokens, link validity, and
the domain state changed by the journey. It supplies the recipient and the
minimum typed data required; Communication does not inspect another module's
internal entities to discover them.

SMS, push notifications, in-product notifications, marketing communication,
user communication preferences, visible message history, arbitrary content,
public sending endpoints, and localization beyond pt-BR are outside the MVP.

Canonical PRD: [Confluence page](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/86114306/Shifu+PRD+Communication)

## Curriculum

Curriculum owns the official content and pedagogical structure that Shifu can
teach and evaluate. It is responsible for:

- the supported Habilidades and their Competências;
- the official order of Competências within each Habilidade;
- support materials;
- diagnostic and learning Atividades; and
- the rules used to evaluate each Atividade.

The MVP uses a fixed curriculum with adaptive practice. Curriculum defines
stable content shared by users; it does not store Objectives, attempts,
evaluations, progress, mastery, released content, recommendations, or
completion state. Learning decides how an individual progresses through the
curriculum, and Intelligence may query authorized curriculum data for the
Mentor and Goal Planner.

The MVP validation case is programming logic with practical programming
activities. Curriculum authoring, versioning, dynamically generated content,
and user-specific reordering are out of scope.

Canonical PRD: [Confluence page](https://joaogoliveiragarcia.atlassian.net/wiki/x/AQDzB) · Origin: [Google Doc](https://docs.google.com/document/d/1gw8l7mUGIEiyb9XGFIL3UdynKHQ-58rHcFD_8zXjWAA/edit)

## Learning

Learning owns each learner's individual learning experience. It is responsible
for:

- creating and maintaining Objectives and their Habilidade experiences;
- diagnosing each Habilidade and establishing the learner's starting point;
- serving theory and practice from the Curriculum sequence;
- recording immutable submitted attempts and producing official evaluations;
- calculating progress, mastery, focus, and available content;
- recommending the next Activity and reinforcement work;
- explaining results and preserving learning history; and
- recognizing Habilidade completion and supporting later review.

Each Habilidade inside an Objective is an independent experience. If the same
Habilidade appears in two Objectives, its diagnosis, progress, mastery,
attempts, released content, and completion are not shared between them.

Learning is the sole authority for individual pedagogical state: Intelligence
may assist with planning or configured AI evaluations, and Gamification may
recognize confirmed learning facts, but neither may change Learning's official
results or decisions.

Canonical PRD: [Confluence page](https://joaogoliveiragarcia.atlassian.net/wiki/x/AYDzB) · Origin: [Google Doc](https://docs.google.com/document/d/1MGJR-hp4oU5OrdrJSDynMfm_nS5BpP1N0jev-A9WnG0/edit)

## Gamification

Gamification owns the learner's global motivational experience across all
Objectives and Habilidades. It is responsible for:

- the global gamification profile;
- XP and level calculation;
- valid practice days and the current streak;
- the activity calendar;
- the fixed achievement catalog and reward eligibility;
- reward and XP history; and
- reward feedback shown to the learner.

Gamification consumes confirmed facts from Learning, such as evaluated
activities, diagnostic completion, mastery, and Habilidade completion. It uses
Identity for the account and current time zone. Its mechanics never change
Learning's grade, progress, mastery, content availability, recommendation, or
completion state, and it does not use AI to decide rewards.

The Mentor may read the current XP, level, streak, and achievements for
motivational context. Rankings, social competition, external rewards,
proactive reminders, and user-configurable reward rules are out of scope.

Canonical PRD: [Confluence page](https://joaogoliveiragarcia.atlassian.net/wiki/x/AgDxB) · Origin: [Google Doc](https://docs.google.com/document/d/1Y8HFrHP9I-7afjNpckUsQt02UROiOMx9EjEKzvMNu5s/edit)

## Intelligence

Intelligence owns Shifu's AI-assisted experiences. The MVP contains two
distinct capabilities:

- Mentor: private, independent, resumable conversations that provide
  contextual guidance during learning; and
- Goal Planner: an assisted flow that turns a free-form intention into a
  proposal composed only of existing Curriculum Habilidades.

The Mentor may consult authorized Learning, Curriculum, and Gamification
context, but it must not modify Objectives, Habilidades, attempts, evaluations,
XP, streaks, achievements, or other product state. During an in-progress
diagnostic it cannot provide help for the diagnostic activity; while a
Habilidade is being learned it gives increasingly specific guidance without
revealing the complete solution. A complete reference solution is allowed
after the Habilidade is concluded.

The Goal Planner may ask structured questions in batches, propose a title,
description, Habilidades, and inclusion rationales, and allow the learner to
adjust the proposal. Only the learner's final confirmation and Learning's own
validation may create the Objective. Intelligence provides the confirmed
proposal to Learning but does not become the authority for learning state.

Mentor and Planner share a monthly AI quota. The Shifu supplies the AI; users
do not configure models, parameters, or credentials in the MVP.

Canonical PRD: [Confluence page](https://joaogoliveiragarcia.atlassian.net/wiki/x/AQD0B) · Origin: [Google Doc](https://docs.google.com/document/d/1dp3XQcj0l68ekad1yk3ns-NVOQWTzEQo8jTylqcpNzw/edit)

## Dependency Graph

The product dependencies are:

- Identity → Learning: trusted user identity and account status.
- Identity → Intelligence: user identity and account status.
- Identity → Gamification: user identity, account status, and time zone.
- Identity → Communication: eligible transactional-message requests,
  recipient, message type, and minimum required data.
- Communication → Identity: known delivery status, permanent failures, and
  rejections for account-confirmation and password-recovery messages.
- Curriculum → Learning: Habilidades, Competências, materials, Atividades,
  and evaluation rules.
- Curriculum → Intelligence: Habilidades and relationships for the Planner,
  plus authorized content for the Mentor.
- Learning → Intelligence: authorized learning context for the Mentor.
- Learning → Gamification: confirmed practice, evaluation, mastery, and
  completion facts.
- Gamification → Intelligence: current XP, level, streak, and achievements
  for motivational context.
- Intelligence → Learning: confirmed Goal Planner proposals and optional AI
  evaluation support.

These dependencies do not transfer ownership. In particular, Learning remains
the authority for individual learning state, Curriculum remains the authority
for official content, and Gamification remains motivational only.

All modules that own user data participate in the Identity account-deletion
flow. Their data must become inaccessible before Identity reports the account
deletion as complete. Communication removes active account associations and
retains only the minimum operational metadata allowed by its product contract.

The complete source set is available in the [Shifu PRD folder](https://drive.google.com/drive/folders/1AuEjLUrJSIl-1YS-1CKuDXzHD5qze0tq).
