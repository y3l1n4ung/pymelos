"""Semantic versioning utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto


class BumpType(Enum):
    """Version bump types."""

    MAJOR = auto()
    MINOR = auto()
    PATCH = auto()
    NONE = auto()

    def __gt__(self, other: BumpType) -> bool:
        if not isinstance(other, BumpType):
            return NotImplemented
        # MAJOR > MINOR > PATCH > NONE
        order = {BumpType.MAJOR: 3, BumpType.MINOR: 2, BumpType.PATCH: 1, BumpType.NONE: 0}
        return order[self] > order[other]

    def __lt__(self, other: BumpType) -> bool:
        if not isinstance(other, BumpType):
            return NotImplemented
        return not (self > other or self == other)


# SemVer regex pattern
SEMVER_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


@dataclass(frozen=True, slots=True)
class Version:
    """Semantic version representation.

    Follows the Semantic Versioning 2.0.0 specification.
    """

    major: int
    minor: int
    patch: int
    prerelease: str | None = None
    build: str | None = None

    @classmethod
    def parse(cls, version_str: str) -> Version:
        """Parse a version string.

        Args:
            version_str: Version string like "1.2.3" or "1.2.3-alpha.1+build.123".

        Returns:
            Parsed Version.

        Raises:
            ValueError: If the version string is invalid.
        """
        # Strip leading 'v' if present
        if version_str.startswith("v"):
            version_str = version_str[1:]

        match = SEMVER_PATTERN.match(version_str)
        if not match:
            raise ValueError(f"Invalid semantic version: {version_str}")

        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=match.group("prerelease"),
            build=match.group("build"),
        )

    @classmethod
    def from_parts(
        cls,
        major: int = 0,
        minor: int = 0,
        patch: int = 0,
        prerelease: str | None = None,
    ) -> Version:
        """Create a version from parts."""
        return cls(major=major, minor=minor, patch=patch, prerelease=prerelease)

    def bump(
        self,
        bump_type: BumpType,
        prerelease_tag: str | None = None,
    ) -> Version:
        """Return a new version with the specified bump applied.

        Args:
            bump_type: Type of version bump.
            prerelease_tag: Prerelease identifier (e.g., "alpha", "beta", "rc").

        Returns:
            New bumped version.
        """
        if bump_type == BumpType.NONE:
            return self

        if bump_type == BumpType.MAJOR:
            new_version = Version(self.major + 1, 0, 0)
        elif bump_type == BumpType.MINOR:
            new_version = Version(self.major, self.minor + 1, 0)
        else:  # PATCH
            new_version = Version(self.major, self.minor, self.patch + 1)

        if prerelease_tag:
            return Version(
                new_version.major,
                new_version.minor,
                new_version.patch,
                prerelease=f"{prerelease_tag}.1",
            )

        return new_version

    def bump_prerelease(self, tag: str | None = None) -> Version:
        """Bump the prerelease version.

        Args:
            tag: Prerelease tag (uses existing if not provided).

        Returns:
            New version with bumped prerelease.
        """
        if self.prerelease:
            # Parse existing prerelease: "alpha.1" -> "alpha.2"
            parts = self.prerelease.rsplit(".", 1)
            if len(parts) == 2 and parts[1].isdigit():
                new_pre = f"{parts[0]}.{int(parts[1]) + 1}"
            else:
                new_pre = f"{self.prerelease}.1"
            return Version(self.major, self.minor, self.patch, prerelease=new_pre)
        elif tag:
            return Version(self.major, self.minor, self.patch, prerelease=f"{tag}.1")
        else:
            return self

    @property
    def is_prerelease(self) -> bool:
        """Check if this is a prerelease version."""
        return self.prerelease is not None

    @property
    def base_version(self) -> Version:
        """Get the version without prerelease or build metadata."""
        return Version(self.major, self.minor, self.patch)

    def __str__(self) -> str:
        """Convert to version string."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __lt__(self, other: Version) -> bool:
        """Compare versions for sorting."""
        if not isinstance(other, Version):
            return NotImplemented

        # Compare major.minor.patch
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

        # Prerelease versions have lower precedence
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        if self.prerelease and other.prerelease:
            return self._compare_prerelease(self.prerelease, other.prerelease) < 0

        return False

    @staticmethod
    def _compare_prerelease(a: str, b: str) -> int:
        """Compare prerelease identifiers."""
        a_parts = a.split(".")
        b_parts = b.split(".")

        for a_part, b_part in zip(a_parts, b_parts, strict=False):
            # Numeric identifiers have lower precedence than alphanumeric
            a_is_num = a_part.isdigit()
            b_is_num = b_part.isdigit()

            if a_is_num and b_is_num:
                diff = int(a_part) - int(b_part)
                if diff != 0:
                    return diff
            elif a_is_num:
                return -1
            elif b_is_num:
                return 1
            else:
                if a_part < b_part:
                    return -1
                if a_part > b_part:
                    return 1

        # Shorter prerelease has lower precedence
        return len(a_parts) - len(b_parts)


def is_valid_semver(version_str: str) -> bool:
    """Check if a string is a valid semantic version.

    Args:
        version_str: Version string to check.

    Returns:
        True if valid semver.
    """
    try:
        Version.parse(version_str)
        return True
    except ValueError:
        return False


def compare_versions(v1: str, v2: str) -> int:
    """Compare two version strings.

    Args:
        v1: First version.
        v2: Second version.

    Returns:
        -1 if v1 < v2, 0 if equal, 1 if v1 > v2.
    """
    ver1 = Version.parse(v1)
    ver2 = Version.parse(v2)

    if ver1 < ver2:
        return -1
    if ver2 < ver1:
        return 1
    return 0
