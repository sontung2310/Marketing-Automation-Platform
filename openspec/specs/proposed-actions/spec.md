# proposed-actions Specification

## Purpose
Lets the Execution agent propose follow-up actions that never run on their
own: a user approves or discards each one, and only an approved action runs,
through a replaceable mock connector.

## Requirements

### Requirement: Agents only propose actions

An `OK` Execution output SHALL carry 0–2 proposed actions of the supported
types (`schedule_social_post`, `create_cms_draft`, `create_email_draft`,
`add_to_content_calendar`). Each SHALL be persisted as `PROPOSED`, linked to
its deliverable, with a payload validated for its type (agents-spec §8). The
payload's content SHALL come from the deliverable it acts on. A
`schedule_social_post` without a user-given time SHALL be scheduled for the
next weekday at 09:00 Australia/Sydney. No action SHALL run during an agent
run. A request for an unsupported action, such as posting to TikTok or
emailing a whole list, SHALL be explained in the message, and only supported
actions SHALL be proposed.

#### Scenario: A social post is proposed for the next weekday

- **GIVEN** a Friday in Sydney
- **WHEN** an Execution run proposes `schedule_social_post` with no time from
  the user
- **THEN** the stored action is `PROPOSED`, and its `scheduled_for` is the
  following Monday at 09:00 Australia/Sydney, with the deliverable's text and
  ID in the payload

#### Scenario: Unsupported action

- **GIVEN** the chat message "Post it to TikTok now" after a deliverable
- **WHEN** it is sent to Execution
- **THEN** the message explains that TikTok posting is not supported, and no
  action other than a supported type is proposed

### Requirement: Approval and discard follow the state machine

`POST /actions/{action_id}/approve` SHALL validate the payload (with any
`payload_overrides`), move the action to `APPROVED`, run the mock connector
for its type, and return `200` with the action `EXECUTED` and its receipt, or
`FAILED` with a message. `POST /actions/{action_id}/discard` SHALL return
`200` with the action `DISCARDED`. Either endpoint SHALL return `409`
(`CONFLICT`) when the action is not `PROPOSED`, and `404` when it does not
exist. Connectors SHALL sit behind one protocol, so a real integration can
replace a mock without changing the agents. Mock receipts SHALL be marked as
mock.

#### Scenario: Approve executes once

- **GIVEN** a `PROPOSED` `create_cms_draft` action
- **WHEN** it is approved
- **THEN** its status becomes `EXECUTED` with a receipt holding a
  `receipt_id`, `status: "DRAFT_CREATED"` and a `preview_url`, and approving
  it again returns `409` with the action unchanged

#### Scenario: A discarded action can't be approved

- **GIVEN** a `PROPOSED` action that has been discarded
- **WHEN** it is approved
- **THEN** the response is `409`, and the action stays `DISCARDED` with no
  receipt

#### Scenario: An approval override is validated

- **GIVEN** a `PROPOSED` `schedule_social_post` action
- **WHEN** it is approved with `payload_overrides.scheduled_for` set to a
  value that is not an ISO datetime with a timezone
- **THEN** the response is `422`, and the action stays `PROPOSED`
