#  Copyright (c) 2023. {cookiecutter.cookiecutter.maintainer_name}}
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Test script for python template."""
import uuid
from datetime import datetime
import unittest
from unittest.mock import Mock

from omotes_sdk_protocol.job_pb2 import JobResult

from omotes_sdk.job import Job
from omotes_sdk.omotes_interface import JobSubmissionCallbackHandler
from omotes_sdk.workflow_type import WorkflowType


class JobSubmissionCallbackHandlerTest(unittest.TestCase):
    def test__callback_on_finished_wrapped__is_correct(self) -> None:
        # Arrange
        job_id = uuid.uuid4()
        job = Job(
            id=job_id,
            workflow_type=WorkflowType(
                workflow_type_name="some-name", workflow_type_description_name="some-descr"
            ),
        )
        callback_on_finished = Mock()
        handler = JobSubmissionCallbackHandler(job, callback_on_finished, None, None)
        result_msg = JobResult(
            uuid=str(job_id),
            result_type=JobResult.ResultType.SUCCEEDED,
            output_esdl=b"esdl",
            logs="logs",
        )

        # Act
        handler.callback_on_finished_wrapped(result_msg.SerializeToString())

        # Assert
        callback_on_finished.assert_called_once_with(job, result_msg)
