from unittest.mock import Mock

from slack_bolt import Args


def mock_an_args():
    args_mock=Mock(Args)
    respond_mock=Mock()
    say_mock=Mock()
    args_mock.context=dict(user_id="testuserid")
    args_mock.attach_mock(Mock(),"ack")
    args_mock.attach_mock(respond_mock,"respond")
    args_mock.attach_mock(say_mock,"say")
    return args_mock,respond_mock,say_mock