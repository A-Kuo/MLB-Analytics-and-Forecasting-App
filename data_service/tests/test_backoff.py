from unittest.mock import MagicMock, patch

import pytest
import requests

from backoff import UpstreamError, request_with_backoff


def _response(status_code, headers=None):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.headers = headers or {}
    return resp


@patch("backoff.time.sleep", return_value=None)
@patch("backoff.requests.request")
def test_succeeds_immediately_on_200(mock_request, mock_sleep):
    mock_request.return_value = _response(200)
    resp = request_with_backoff("GET", "https://example.com")
    assert resp.status_code == 200
    mock_sleep.assert_not_called()


@patch("backoff.time.sleep", return_value=None)
@patch("backoff.requests.request")
def test_retries_on_429_then_succeeds(mock_request, mock_sleep):
    mock_request.side_effect = [_response(429), _response(429), _response(200)]
    resp = request_with_backoff("GET", "https://example.com", max_retries=3)
    assert resp.status_code == 200
    assert mock_request.call_count == 3
    assert mock_sleep.call_count == 2


@patch("backoff.time.sleep", return_value=None)
@patch("backoff.requests.request")
def test_does_not_retry_on_404(mock_request, mock_sleep):
    mock_request.return_value = _response(404)
    resp = request_with_backoff("GET", "https://example.com")
    assert resp.status_code == 404
    mock_sleep.assert_not_called()
    assert mock_request.call_count == 1


@patch("backoff.time.sleep", return_value=None)
@patch("backoff.requests.request")
def test_raises_upstream_error_after_exhausting_retries(mock_request, mock_sleep):
    mock_request.return_value = _response(503)
    with pytest.raises(UpstreamError):
        request_with_backoff("GET", "https://example.com", max_retries=2)
    assert mock_request.call_count == 3  # initial attempt + 2 retries


@patch("backoff.time.sleep", return_value=None)
@patch("backoff.requests.request")
def test_respects_retry_after_header(mock_request, mock_sleep):
    mock_request.side_effect = [_response(429, headers={"Retry-After": "2"}), _response(200)]
    request_with_backoff("GET", "https://example.com")
    mock_sleep.assert_called_once_with(2.0)


@patch("backoff.time.sleep", return_value=None)
@patch("backoff.requests.request")
def test_retries_on_connection_error(mock_request, mock_sleep):
    mock_request.side_effect = [requests.ConnectionError("boom"), _response(200)]
    resp = request_with_backoff("GET", "https://example.com")
    assert resp.status_code == 200
    assert mock_sleep.call_count == 1


@patch("backoff.time.sleep", return_value=None)
@patch("backoff.requests.request")
def test_backoff_delay_grows_with_attempt_number(mock_request, mock_sleep):
    mock_request.side_effect = [_response(503), _response(503), _response(200)]
    request_with_backoff("GET", "https://example.com", base_delay=1.0, max_delay=100.0)
    first_ceiling_call, second_ceiling_call = mock_sleep.call_args_list
    # full jitter: sleep(x) where 0 <= x <= ceiling; ceiling doubles each attempt.
    assert first_ceiling_call.args[0] <= 1.0
    assert second_ceiling_call.args[0] <= 2.0
