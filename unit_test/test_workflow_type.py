import unittest

from omotes_sdk.workflow_type import WorkflowType


class WorkflowTypeTest(unittest.TestCase):
    def test__eq__same_id_but_different_description_should_still_be_same(self) -> None:
        # Arrange
        type_1 = WorkflowType("some-name", "some descript 1")
        type_2 = WorkflowType("some-name", "some descript 2")

        # Act
        is_same = type_1 == type_2

        # Assert
        self.assertTrue(is_same)

    def test__eq__different_id_but_same_description_should_not_be_same(self) -> None:
        # Arrange
        type_1 = WorkflowType("some-name-1", "some descript")
        type_2 = WorkflowType("some-name-2", "some descript")

        # Act
        is_same = type_1 == type_2

        # Assert
        self.assertFalse(is_same)

    def test__hash__same_id_but_different_descript_should_have_same_hash(self) -> None:
        # Arrange
        type_1 = WorkflowType("some-name", "some descript-1")
        type_2 = WorkflowType("some-name", "some descript-2")

        # Act
        hash_1 = hash(type_1)
        hash_2 = hash(type_2)

        # Assert
        self.assertEqual(hash_1, hash_2)

    def test__hash__same_descript_but_different_id_should_have_different_hash(self) -> None:
        # Arrange
        type_1 = WorkflowType("some-name-1", "some descript")
        type_2 = WorkflowType("some-name-2", "some descript")

        # Act
        hash_1 = hash(type_1)
        hash_2 = hash(type_2)

        # Assert
        self.assertNotEqual(hash_1, hash_2)
