from helpers import TestSources, PreviewSinks
from exception import RangeError
import pytest
from mock import Mock, patch


class TestTestSourcesVideoPort(object):

    def test_blank(self):
        tests = ['', None, [], {}]
        for test in tests:
            with pytest.raises(ValueError):
                TestSources(video_port=test) 

    def test_range(self):
        tests = [-100, 1e7, 65536]
        for test in tests:
            with pytest.raises(RangeError):
                TestSources(video_port=test)

    def test_invalid(self):
        tests = [[1, 2, 3, 4], {1: 2, 2: 3}, '1e10']
        for test in tests:
            with pytest.raises(TypeError):
                TestSources(video_port=test)

    def test_normal(self):
        tests = [1, 65535, 1000]
        for test in tests:
            src = TestSources(video_port=test)
            assert src.video_port == test
