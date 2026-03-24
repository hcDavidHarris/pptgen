"""Tests for the retry policy module."""

import pytest
from pptgen.jobs.retry import get_backoff_seconds, is_retryable


class TestIsRetryable:
    def test_ai_provider_is_retryable(self):
        assert is_retryable("ai_provider") is True

    def test_system_is_retryable(self):
        assert is_retryable("system") is True

    def test_validation_not_retryable(self):
        assert is_retryable("validation") is False

    def test_configuration_not_retryable(self):
        assert is_retryable("configuration") is False

    def test_rendering_not_retryable(self):
        assert is_retryable("rendering") is False

    def test_connector_not_retryable(self):
        assert is_retryable("connector") is False

    def test_planning_not_retryable(self):
        assert is_retryable("planning") is False

    def test_workspace_not_retryable(self):
        assert is_retryable("workspace") is False


class TestGetBackoffSeconds:
    def test_first_retry_one_second(self):
        assert get_backoff_seconds(0) == 1

    def test_second_retry_two_seconds(self):
        assert get_backoff_seconds(1) == 2

    def test_third_retry_four_seconds(self):
        assert get_backoff_seconds(2) == 4

    def test_fourth_retry_eight_seconds(self):
        assert get_backoff_seconds(3) == 8

    def test_high_retry_count_capped_at_60(self):
        assert get_backoff_seconds(10) == 60

    def test_cap_is_exactly_60(self):
        assert get_backoff_seconds(100) == 60
