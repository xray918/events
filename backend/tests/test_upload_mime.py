"""Tests for upload image MIME type detection from magic bytes."""

import pytest

from app.api.v1.upload import _detect_mime


class TestDetectMime:
    def test_png_magic_bytes(self):
        header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        assert _detect_mime(header) == "image/png"

    def test_jpeg_magic_bytes(self):
        header = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        assert _detect_mime(header) == "image/jpeg"

    def test_gif87a_magic_bytes(self):
        header = b"GIF87a" + b"\x00" * 100
        assert _detect_mime(header) == "image/gif"

    def test_gif89a_magic_bytes(self):
        header = b"GIF89a" + b"\x00" * 100
        assert _detect_mime(header) == "image/gif"

    def test_webp_magic_bytes(self):
        header = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100
        assert _detect_mime(header) == "image/webp"

    def test_riff_non_webp_returns_none(self):
        header = b"RIFF\x00\x00\x00\x00AVI " + b"\x00" * 100
        assert _detect_mime(header) is None

    def test_unknown_format_returns_none(self):
        header = b"\x00\x01\x02\x03\x04\x05" + b"\x00" * 100
        assert _detect_mime(header) is None

    def test_empty_data_returns_none(self):
        assert _detect_mime(b"") is None

    def test_short_data_returns_none(self):
        assert _detect_mime(b"\xff\xd8") is None

    def test_png_file_declared_as_jpeg_gets_corrected(self):
        """The exact scenario from the bug: PNG content with wrong declared type."""
        png_header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        detected = _detect_mime(png_header)
        assert detected == "image/png"
        assert detected != "image/jpeg"
