from typing import Any
from unittest.mock import AsyncMock, MagicMock


class AsyncMagicMock(MagicMock):
    """Like MagicMock, but for patching objects with asynchronous methods.

    For example:

        mock = AsyncMagicMock()
        await mock.do_some_async()

    Or use it together with patch:

        from unittest.mock import patch

        @patch("some.class.with.async.methods", new_callable=AsyncMagicMock)
        def test_something(some_class):
            ...

    """

    def __getattr__(self, name: str) -> Any:
        attr = super().__getattr__(name)

        if isinstance(attr, MagicMock):
            mock = AsyncMock()
            setattr(self, name, mock)
            return mock

        return attr
