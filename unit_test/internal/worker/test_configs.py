import unittest

from omotes_sdk.internal.worker.configs import WorkerConfig


class TestWorkerConfigConfig(unittest.TestCase):
    def test__init__no_errors(self) -> None:
        # Act / Assert
        WorkerConfig()
