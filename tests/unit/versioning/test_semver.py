"""Tests for semver module."""

from __future__ import annotations

import pytest

from pymelos.versioning.semver import (
    BumpType,
    Version,
    compare_versions,
    is_valid_semver,
)


class TestBumpType:
    """Tests for BumpType enum."""

    def test_bump_type_ordering(self) -> None:
        """MAJOR > MINOR > PATCH > NONE."""
        assert BumpType.MAJOR > BumpType.MINOR
        assert BumpType.MINOR > BumpType.PATCH
        assert BumpType.PATCH > BumpType.NONE

    def test_bump_type_less_than(self) -> None:
        """Test less than comparison."""
        assert BumpType.NONE < BumpType.PATCH
        assert BumpType.PATCH < BumpType.MINOR
        assert BumpType.MINOR < BumpType.MAJOR

    def test_bump_type_equality(self) -> None:
        """Same bump types are equal."""
        assert BumpType.MAJOR == BumpType.MAJOR
        assert not (BumpType.MAJOR > BumpType.MAJOR)
        assert not (BumpType.MAJOR < BumpType.MAJOR)


class TestVersionParsing:
    """Tests for Version.parse()."""

    def test_parse_simple_version(self) -> None:
        """Parse basic X.Y.Z version."""
        v = Version.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.prerelease is None
        assert v.build is None

    def test_parse_version_with_v_prefix(self) -> None:
        """Strip leading 'v' prefix."""
        v = Version.parse("v2.0.0")
        assert v.major == 2
        assert v.minor == 0
        assert v.patch == 0

    def test_parse_prerelease_version(self) -> None:
        """Parse version with prerelease tag."""
        v = Version.parse("1.0.0-alpha.1")
        assert v.major == 1
        assert v.minor == 0
        assert v.patch == 0
        assert v.prerelease == "alpha.1"

    def test_parse_build_metadata(self) -> None:
        """Parse version with build metadata."""
        v = Version.parse("1.0.0+build.123")
        assert v.major == 1
        assert v.build == "build.123"

    def test_parse_full_version(self) -> None:
        """Parse version with prerelease and build."""
        v = Version.parse("2.1.3-beta.2+sha.abc123")
        assert v.major == 2
        assert v.minor == 1
        assert v.patch == 3
        assert v.prerelease == "beta.2"
        assert v.build == "sha.abc123"

    def test_parse_invalid_version_raises(self) -> None:
        """Invalid versions raise ValueError."""
        with pytest.raises(ValueError, match="Invalid semantic version"):
            Version.parse("not-a-version")

    def test_parse_empty_string_raises(self) -> None:
        """Empty string raises ValueError."""
        with pytest.raises(ValueError):
            Version.parse("")

    def test_parse_leading_zeros(self) -> None:
        """Leading zeros in major version are invalid."""
        with pytest.raises(ValueError):
            Version.parse("01.2.3")


class TestVersionBumping:
    """Tests for Version.bump()."""

    def test_bump_major(self) -> None:
        """Major bump resets minor and patch."""
        v = Version.parse("1.2.3")
        bumped = v.bump(BumpType.MAJOR)
        assert bumped == Version(2, 0, 0)

    def test_bump_minor(self) -> None:
        """Minor bump resets patch."""
        v = Version.parse("1.2.3")
        bumped = v.bump(BumpType.MINOR)
        assert bumped == Version(1, 3, 0)

    def test_bump_patch(self) -> None:
        """Patch bump only increments patch."""
        v = Version.parse("1.2.3")
        bumped = v.bump(BumpType.PATCH)
        assert bumped == Version(1, 2, 4)

    def test_bump_none_returns_same(self) -> None:
        """NONE bump returns the same version."""
        v = Version.parse("1.2.3")
        bumped = v.bump(BumpType.NONE)
        assert bumped == v

    def test_bump_with_prerelease_tag(self) -> None:
        """Bump with prerelease creates prerelease version."""
        v = Version.parse("1.0.0")
        bumped = v.bump(BumpType.MINOR, prerelease_tag="alpha")
        assert str(bumped) == "1.1.0-alpha.1"


class TestVersionPrerelease:
    """Tests for prerelease version handling."""

    def test_bump_prerelease_increments(self) -> None:
        """Bumping prerelease increments the number."""
        v = Version.parse("1.0.0-alpha.1")
        bumped = v.bump_prerelease()
        assert str(bumped) == "1.0.0-alpha.2"

    def test_bump_prerelease_with_new_tag(self) -> None:
        """Add prerelease tag to non-prerelease version."""
        v = Version.parse("1.0.0")
        bumped = v.bump_prerelease("beta")
        assert str(bumped) == "1.0.0-beta.1"

    def test_is_prerelease(self) -> None:
        """Check is_prerelease property."""
        assert Version.parse("1.0.0-alpha.1").is_prerelease
        assert not Version.parse("1.0.0").is_prerelease

    def test_base_version(self) -> None:
        """Get version without prerelease or build."""
        v = Version.parse("1.2.3-alpha.1+build.123")
        assert v.base_version == Version(1, 2, 3)


class TestVersionComparison:
    """Tests for version comparison."""

    def test_compare_major(self) -> None:
        """Higher major version is greater."""
        assert Version.parse("2.0.0") > Version.parse("1.9.9")

    def test_compare_minor(self) -> None:
        """Higher minor version is greater."""
        assert Version.parse("1.2.0") > Version.parse("1.1.9")

    def test_compare_patch(self) -> None:
        """Higher patch version is greater."""
        assert Version.parse("1.0.2") > Version.parse("1.0.1")

    def test_prerelease_lower_than_release(self) -> None:
        """Prerelease version is lower than release."""
        assert Version.parse("1.0.0-alpha.1") < Version.parse("1.0.0")

    def test_compare_prerelease_versions(self) -> None:
        """Compare prerelease versions correctly."""
        assert Version.parse("1.0.0-alpha.1") < Version.parse("1.0.0-alpha.2")
        assert Version.parse("1.0.0-alpha.2") < Version.parse("1.0.0-beta.1")

    def test_equal_versions(self) -> None:
        """Equal versions compare correctly."""
        v1 = Version.parse("1.2.3")
        v2 = Version.parse("1.2.3")
        assert v1 == v2
        assert not v1 < v2
        assert not v1 > v2


class TestVersionString:
    """Tests for Version.__str__()."""

    def test_str_simple(self) -> None:
        """Simple version to string."""
        assert str(Version(1, 2, 3)) == "1.2.3"

    def test_str_with_prerelease(self) -> None:
        """Prerelease version to string."""
        v = Version(1, 0, 0, prerelease="rc.1")
        assert str(v) == "1.0.0-rc.1"

    def test_str_with_build(self) -> None:
        """Build metadata in string."""
        v = Version(1, 0, 0, build="20230101")
        assert str(v) == "1.0.0+20230101"

    def test_str_full(self) -> None:
        """Full version string."""
        v = Version(1, 0, 0, prerelease="beta.1", build="sha.abc")
        assert str(v) == "1.0.0-beta.1+sha.abc"


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_is_valid_semver_true(self) -> None:
        """Valid semver returns True."""
        assert is_valid_semver("1.0.0")
        assert is_valid_semver("v1.0.0")
        assert is_valid_semver("1.0.0-alpha")

    def test_is_valid_semver_false(self) -> None:
        """Invalid semver returns False."""
        assert not is_valid_semver("not-valid")
        assert not is_valid_semver("1.0")
        assert not is_valid_semver("")

    def test_compare_versions(self) -> None:
        """Compare version strings."""
        assert compare_versions("1.0.0", "2.0.0") == -1
        assert compare_versions("2.0.0", "1.0.0") == 1
        assert compare_versions("1.0.0", "1.0.0") == 0
