import asyncio

import pytest

from shifu.identity.providers.account_activity.sqlalchemy_account_activity_provider import (
    _wait_for_completion,  # pyright: ignore[reportPrivateUsage]
)


class TestWaitForCompletion:
    def test_should_return_the_result_when_not_cancelled(self) -> None:
        async def scenario() -> str:
            future: asyncio.Future[str] = asyncio.get_running_loop().create_future()
            future.set_result('done')
            return await _wait_for_completion(future)

        assert asyncio.run(scenario()) == 'done'

    @pytest.mark.parametrize('cancellations', [1, 3])
    def test_should_finish_the_work_before_re_raising_a_cancellation(
        self, cancellations: int
    ) -> None:
        async def scenario() -> asyncio.Future[str]:
            future: asyncio.Future[str] = asyncio.get_running_loop().create_future()
            task = asyncio.create_task(_wait_for_completion(future))
            for _ in range(cancellations):
                await asyncio.sleep(0)
                task.cancel()
            await asyncio.sleep(0)
            assert not task.done()
            future.set_result('done')
            with pytest.raises(asyncio.CancelledError):
                await task
            return future

        future = asyncio.run(scenario())
        assert future.result() == 'done'

    def test_should_raise_the_work_error_after_a_cancellation(self) -> None:
        async def scenario() -> None:
            future: asyncio.Future[str] = asyncio.get_running_loop().create_future()
            task = asyncio.create_task(_wait_for_completion(future))
            await asyncio.sleep(0)
            task.cancel()
            await asyncio.sleep(0)
            future.set_exception(ValueError('failed'))
            with pytest.raises(ValueError, match='failed'):
                await task

        asyncio.run(scenario())
