CREATE TABLE IF NOT EXISTS learners (
    learner_id VARCHAR(20) PRIMARY KEY,
    display_name VARCHAR(100) NOT NULL,
    cohort VARCHAR(40) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS learning_events (
    event_id VARCHAR(24) PRIMARY KEY,
    learner_id VARCHAR(20) NOT NULL REFERENCES learners (learner_id),
    event_type VARCHAR(40) NOT NULL,
    resource_id VARCHAR(40) NOT NULL,
    score NUMERIC(5, 2),
    occurred_at TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_learning_events_learner_occurred_at
    ON learning_events (learner_id, occurred_at);

INSERT INTO learners (learner_id, display_name, cohort, created_at)
VALUES
    ('learner-001', 'Ana Lima', 'DSM-2026-A', '2026-09-01T09:00:00Z'),
    ('learner-002', 'Bruno Alves', 'DSM-2026-A', '2026-09-01T09:05:00Z'),
    ('learner-003', 'Caio Souza', 'DSM-2026-A', '2026-09-01T09:10:00Z'),
    ('learner-004', 'Diana Costa', 'DSM-2026-A', '2026-09-01T09:15:00Z'),
    ('learner-005', 'Enzo Santos', 'DSM-2026-A', '2026-09-01T09:20:00Z'),
    ('learner-006', 'Fernanda Rocha', 'DSM-2026-B', '2026-09-02T09:00:00Z'),
    ('learner-007', 'Gustavo Reis', 'DSM-2026-B', '2026-09-02T09:05:00Z'),
    ('learner-008', 'Helena Dias', 'DSM-2026-B', '2026-09-02T09:10:00Z'),
    ('learner-009', 'Igor Martins', 'DSM-2026-B', '2026-09-02T09:15:00Z'),
    ('learner-010', 'Julia Nunes', 'DSM-2026-B', '2026-09-02T09:20:00Z')
ON CONFLICT (learner_id) DO NOTHING;

INSERT INTO learning_events (
    event_id, learner_id, event_type, resource_id, score, occurred_at, metadata
)
VALUES
    ('event-001', 'learner-001', 'activity_submitted', 'activity-logic-01', 88.00, '2026-09-15T10:00:00Z', '{"language":"python","attempt":1}'),
    ('event-002', 'learner-001', 'material_viewed', 'material-loops-01', NULL, '2026-09-15T10:15:00Z', '{"duration_seconds":240}'),
    ('event-003', 'learner-002', 'activity_submitted', 'activity-logic-01', 74.50, '2026-09-15T10:30:00Z', '{"language":"python","attempt":1}'),
    ('event-004', 'learner-002', 'diagnostic_completed', 'diagnostic-logic-01', 80.00, '2026-09-15T10:45:00Z', '{"question_count":10}'),
    ('event-005', 'learner-003', 'activity_submitted', 'activity-logic-02', 92.00, '2026-09-16T09:00:00Z', '{"language":"javascript","attempt":1}'),
    ('event-006', 'learner-003', 'material_viewed', 'material-arrays-01', NULL, '2026-09-16T09:10:00Z', '{"duration_seconds":315}'),
    ('event-007', 'learner-004', 'activity_submitted', 'activity-logic-01', 61.00, '2026-09-16T09:30:00Z', '{"language":"python","attempt":2}'),
    ('event-008', 'learner-004', 'mentor_opened', 'conversation-004', NULL, '2026-09-16T09:45:00Z', '{"channel":"web"}'),
    ('event-009', 'learner-005', 'activity_submitted', 'activity-logic-03', 95.00, '2026-09-17T11:00:00Z', '{"language":"javascript","attempt":1}'),
    ('event-010', 'learner-006', 'diagnostic_completed', 'diagnostic-logic-01', 70.00, '2026-09-17T11:15:00Z', '{"question_count":10}'),
    ('event-011', 'learner-006', 'activity_submitted', 'activity-logic-02', 82.00, '2026-09-17T11:30:00Z', '{"language":"python","attempt":1}'),
    ('event-012', 'learner-007', 'material_viewed', 'material-conditionals-01', NULL, '2026-09-18T08:00:00Z', '{"duration_seconds":180}'),
    ('event-013', 'learner-008', 'activity_submitted', 'activity-logic-01', 77.00, '2026-09-18T08:30:00Z', '{"language":"python","attempt":1}'),
    ('event-014', 'learner-009', 'activity_submitted', 'activity-logic-02', 89.00, '2026-09-18T09:00:00Z', '{"language":"javascript","attempt":2}'),
    ('event-015', 'learner-010', 'diagnostic_completed', 'diagnostic-logic-01', 86.00, '2026-09-18T09:30:00Z', '{"question_count":10}')
ON CONFLICT (event_id) DO NOTHING;
