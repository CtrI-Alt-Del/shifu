from datetime import UTC, datetime, timedelta

import pytest

import shifu.shared.messaging.agentos.agentos_handoff_store as handoff_module
from shifu.shared.messaging.agentos.agentos_handoff_store import AgentOSHandoffStore

_NOW = datetime(2026, 2, 3, 4, 5, tzinfo=UTC)


class _FrozenDatetime(datetime):
    current = _NOW

    @classmethod
    def now(cls, tz: object = None) -> datetime:
        del tz
        return cls.current


class TestAgentOSHandoffStore:
    def test_handoff_is_capability_scoped_and_consumes_private_values(self) -> None:
        store = AgentOSHandoffStore()
        private_input = {'prompt': 'private attachment context'}
        private_result = {'answer': 'private generated response'}
        reference = store.create(
            capability='mentor-response', input_value=private_input
        )

        assert (
            store.read_input(reference, capability='mentor-response') is private_input
        )
        assert store.read_input(reference, capability='mentor-response') is None
        with pytest.raises(KeyError, match='unavailable'):
            store.read_input(reference, capability='other-capability')

        assert (
            store.complete(
                reference,
                capability='mentor-response',
                result_value=private_result,
            )
            is True
        )
        assert (
            store.take_result(reference, capability='mentor-response') is private_result
        )
        with pytest.raises(KeyError, match='unavailable'):
            store.take_result(reference, capability='mentor-response')

    def test_expired_handoffs_are_removed_before_new_values_are_stored(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(handoff_module, 'datetime', _FrozenDatetime)
        _FrozenDatetime.current = _NOW
        store = AgentOSHandoffStore()
        reference = store.create(
            capability='mentor-response',
            input_value={'prompt': 'private'},
            ttl=timedelta(seconds=1),
        )

        _FrozenDatetime.current = _NOW + timedelta(seconds=2)
        store.create(capability='mentor-response', input_value={'prompt': 'next'})

        with pytest.raises(KeyError, match='unavailable'):
            store.read_input(reference, capability='mentor-response')

    @pytest.mark.parametrize(
        ('capability', 'ttl'),
        [
            ('', None),
            ('mentor-response', timedelta(0)),
            ('mentor-response', timedelta(-1)),
        ],
    )
    def test_create_rejects_missing_capabilities_and_nonpositive_lifetimes(
        self,
        capability: str,
        ttl: timedelta | None,
    ) -> None:
        with pytest.raises(ValueError):
            AgentOSHandoffStore().create(
                capability=capability,
                input_value={'prompt': 'private'},
                ttl=ttl,
            )

    def test_discard_and_clear_remove_handoffs(self) -> None:
        store = AgentOSHandoffStore()
        discarded = store.create(capability='one', input_value='discard')
        cleared = store.create(capability='two', input_value='clear')

        store.discard(discarded)
        with pytest.raises(KeyError, match='unavailable'):
            store.read_input(discarded, capability='one')
        store.clear()
        with pytest.raises(KeyError, match='unavailable'):
            store.read_input(cleared, capability='two')
