#!/usr/bin/env python3
"""
Test artifact collection and storage utility.

This script collects test results, logs, and diagnostic information
from various test runs and organizes them for storage and analysis.
"""

import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TestArtifact:
    """Represents a test artifact."""

    name: str
    path: str
    type: str  # 'log', 'report', 'diagnostic', 'screenshot', 'data'
    size: int
    timestamp: float
    checksum: str
    metadata: dict[str, Any] | None = None


@dataclass
class ArtifactCollection:
    """Collection of test artifacts."""

    collection_id: str
    timestamp: float
    test_run_info: dict[str, Any]
    artifacts: list[TestArtifact]
    total_size: int


class TestArtifactCollector:
    """Collects and organizes test artifacts."""

    def __init__(self, output_dir: str = "test-artifacts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Setup logging
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def collect_artifacts(self, test_run_id: str | None = None) -> ArtifactCollection:
        """Collect all test artifacts from various sources."""
        if not test_run_id:
            test_run_id = f"test_run_{int(time.time())}"

        self.logger.info(f"Collecting test artifacts for run: {test_run_id}")

        # Create collection directory
        collection_dir = self.output_dir / test_run_id
        collection_dir.mkdir(exist_ok=True)

        artifacts = []

        # Collect different types of artifacts
        artifacts.extend(self._collect_test_results())
        artifacts.extend(self._collect_log_files())
        artifacts.extend(self._collect_diagnostic_files())
        artifacts.extend(self._collect_build_artifacts())
        artifacts.extend(self._collect_coverage_reports())
        artifacts.extend(self._collect_performance_data())

        # Copy artifacts to collection directory
        copied_artifacts = []
        for artifact in artifacts:
            copied_artifact = self._copy_artifact(artifact, collection_dir)
            if copied_artifact:
                copied_artifacts.append(copied_artifact)

        # Get test run information
        test_run_info = self._get_test_run_info()

        # Create collection metadata
        collection = ArtifactCollection(
            collection_id=test_run_id,
            timestamp=time.time(),
            test_run_info=test_run_info,
            artifacts=copied_artifacts,
            total_size=sum(a.size for a in copied_artifacts),
        )

        # Save collection metadata
        self._save_collection_metadata(collection, collection_dir)

        # Create archive
        archive_path = self._create_archive(collection, collection_dir)

        self.logger.info(
            f"Collected {len(copied_artifacts)} artifacts ({collection.total_size} bytes)"
        )
        self.logger.info(f"Archive created: {archive_path}")

        return collection

    def _collect_test_results(self) -> list[TestArtifact]:
        """Collect test result files."""
        artifacts = []

        # Look for test result files in common locations
        result_patterns = [
            "test-results/**/*.xml",
            "test-results/**/*.json",
            "test-results/**/*.html",
            "deployment-test-results/**/*",
            "temp/integration_tests/**/*.json",
            "*.junit.xml",
            "coverage.xml",
            "test_results.xml",
        ]

        project_root = Path.cwd()

        for pattern in result_patterns:
            for file_path in project_root.glob(pattern):
                if file_path.is_file():
                    artifact = self._create_artifact(file_path, "report")
                    if artifact:
                        artifacts.append(artifact)

        return artifacts

    def _collect_log_files(self) -> list[TestArtifact]:
        """Collect log files."""
        artifacts = []

        log_patterns = [
            "logs/**/*.log",
            "logs/**/*.json",
            "*.log",
            "npm-debug.log*",
            "yarn-debug.log*",
            "yarn-error.log*",
        ]

        project_root = Path.cwd()

        for pattern in log_patterns:
            for file_path in project_root.glob(pattern):
                if file_path.is_file():
                    artifact = self._create_artifact(file_path, "log")
                    if artifact:
                        artifacts.append(artifact)

        return artifacts

    def _collect_diagnostic_files(self) -> list[TestArtifact]:
        """Collect diagnostic and debug files."""
        artifacts = []

        diagnostic_patterns = [
            "temp/**/*.json",
            "temp/**/*.log",
            "diagnostics_*.json",
            "debug_*.json",
            "core.*",
            "*.dmp",
        ]

        project_root = Path.cwd()

        for pattern in diagnostic_patterns:
            for file_path in project_root.glob(pattern):
                if file_path.is_file():
                    artifact = self._create_artifact(file_path, "diagnostic")
                    if artifact:
                        artifacts.append(artifact)

        return artifacts

    def _collect_build_artifacts(self) -> list[TestArtifact]:
        """Collect build-related artifacts."""
        artifacts = []

        # Collect build info
        build_files = [
            "dist/manifest.json",
            "dist/stats.json",
            "build/static/js/*.map",
            "package-lock.json",
            "uv.lock",
        ]

        project_root = Path.cwd()

        for pattern in build_files:
            for file_path in project_root.glob(pattern):
                if file_path.is_file():
                    artifact = self._create_artifact(file_path, "data")
                    if artifact:
                        artifacts.append(artifact)

        return artifacts

    def _collect_coverage_reports(self) -> list[TestArtifact]:
        """Collect code coverage reports."""
        artifacts = []

        coverage_patterns = [
            "coverage/**/*",
            ".coverage",
            "htmlcov/**/*",
            "coverage.xml",
            "coverage.json",
        ]

        project_root = Path.cwd()

        for pattern in coverage_patterns:
            for file_path in project_root.glob(pattern):
                if file_path.is_file():
                    artifact = self._create_artifact(file_path, "report")
                    if artifact:
                        artifacts.append(artifact)

        return artifacts

    def _collect_performance_data(self) -> list[TestArtifact]:
        """Collect performance monitoring data."""
        artifacts = []

        perf_patterns = [
            "logs/performance.log",
            "perf_*.json",
            "benchmark_*.json",
            "profile_*.json",
        ]

        project_root = Path.cwd()

        for pattern in perf_patterns:
            for file_path in project_root.glob(pattern):
                if file_path.is_file():
                    artifact = self._create_artifact(file_path, "data")
                    if artifact:
                        artifacts.append(artifact)

        return artifacts

    def _create_artifact(
        self, file_path: Path, artifact_type: str
    ) -> TestArtifact | None:
        """Create artifact metadata for a file."""
        try:
            if not file_path.exists():
                return None

            stat = file_path.stat()

            # Calculate checksum
            checksum = self._calculate_checksum(file_path)

            # Get metadata based on file type
            metadata = self._get_file_metadata(file_path, artifact_type)

            return TestArtifact(
                name=file_path.name,
                path=str(file_path.relative_to(Path.cwd())),
                type=artifact_type,
                size=stat.st_size,
                timestamp=stat.st_mtime,
                checksum=checksum,
                metadata=metadata,
            )

        except Exception as e:
            self.logger.warning(f"Failed to create artifact for {file_path}: {e}")
            return None

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file."""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return "unknown"

    def _get_file_metadata(self, file_path: Path, artifact_type: str) -> dict[str, Any]:
        """Get additional metadata for a file."""
        metadata = {"extension": file_path.suffix, "parent_dir": file_path.parent.name}

        # Add type-specific metadata
        if artifact_type == "report" and file_path.suffix == ".json":
            try:
                with open(file_path) as f:
                    data = json.load(f)
                    if "summary" in data:
                        metadata["test_summary"] = data["summary"]
            except Exception:
                pass

        elif artifact_type == "log":
            try:
                # Get log file size and line count
                with open(file_path) as f:
                    lines = sum(1 for _ in f)
                metadata["line_count"] = lines
            except Exception:
                pass

        return metadata

    def _copy_artifact(
        self, artifact: TestArtifact, collection_dir: Path
    ) -> TestArtifact | None:
        """Copy artifact to collection directory."""
        try:
            source_path = Path(artifact.path)
            if not source_path.exists():
                self.logger.warning(f"Artifact not found: {source_path}")
                return None

            # Create subdirectory based on artifact type
            type_dir = collection_dir / artifact.type
            type_dir.mkdir(exist_ok=True)

            # Copy file
            dest_path = type_dir / artifact.name

            # Handle name conflicts
            counter = 1
            while dest_path.exists():
                name_parts = artifact.name.rsplit(".", 1)
                if len(name_parts) == 2:
                    dest_path = type_dir / f"{name_parts[0]}_{counter}.{name_parts[1]}"
                else:
                    dest_path = type_dir / f"{artifact.name}_{counter}"
                counter += 1

            shutil.copy2(source_path, dest_path)

            # Update artifact path
            copied_artifact = TestArtifact(
                name=dest_path.name,
                path=str(dest_path.relative_to(collection_dir)),
                type=artifact.type,
                size=artifact.size,
                timestamp=artifact.timestamp,
                checksum=artifact.checksum,
                metadata=artifact.metadata,
            )

            return copied_artifact

        except Exception as e:
            self.logger.error(f"Failed to copy artifact {artifact.name}: {e}")
            return None

    def _get_test_run_info(self) -> dict[str, Any]:
        """Get information about the test run environment."""
        info = {
            "timestamp": time.time(),
            "hostname": os.uname().nodename if hasattr(os, "uname") else "unknown",
            "platform": sys.platform,
            "python_version": sys.version,
            "working_directory": str(Path.cwd()),
        }

        # Get Git information if available
        try:
            git_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            info["git_commit"] = git_commit

            git_branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            info["git_branch"] = git_branch

        except Exception:
            pass

        # Get CI environment info
        ci_vars = ["CI", "GITHUB_ACTIONS", "GITHUB_RUN_ID", "GITHUB_SHA"]
        for var in ci_vars:
            if var in os.environ:
                info[var.lower()] = os.environ[var]

        return info

    def _save_collection_metadata(
        self, collection: ArtifactCollection, collection_dir: Path
    ):
        """Save collection metadata to JSON file."""
        metadata_file = collection_dir / "collection_metadata.json"

        with open(metadata_file, "w") as f:
            json.dump(asdict(collection), f, indent=2, default=str)

    def _create_archive(
        self, collection: ArtifactCollection, collection_dir: Path
    ) -> Path:
        """Create compressed archive of the collection."""
        archive_path = self.output_dir / f"{collection.collection_id}.zip"

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _dirs, files in os.walk(collection_dir):
                for file in files:
                    file_path = Path(root) / file
                    arc_path = file_path.relative_to(collection_dir)
                    zipf.write(file_path, arc_path)

        return archive_path

    def cleanup_old_artifacts(self, days: int = 30):
        """Clean up old artifact collections."""
        cutoff_time = time.time() - (days * 24 * 60 * 60)

        for item in self.output_dir.iterdir():
            if item.is_dir() and item.stat().st_mtime < cutoff_time:
                self.logger.info(f"Removing old artifact collection: {item}")
                shutil.rmtree(item)
            elif (
                item.is_file()
                and item.suffix == ".zip"
                and item.stat().st_mtime < cutoff_time
            ):
                self.logger.info(f"Removing old artifact archive: {item}")
                item.unlink()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Collect test artifacts")
    parser.add_argument(
        "--output-dir", default="test-artifacts", help="Output directory for artifacts"
    )
    parser.add_argument("--test-run-id", help="Test run identifier")
    parser.add_argument(
        "--cleanup-days",
        type=int,
        default=30,
        help="Clean up artifacts older than N days",
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Only perform cleanup, don't collect artifacts",
    )

    args = parser.parse_args()

    collector = TestArtifactCollector(args.output_dir)

    if args.cleanup_only:
        collector.cleanup_old_artifacts(args.cleanup_days)
    else:
        collection = collector.collect_artifacts(args.test_run_id)
        print(f"Collected {len(collection.artifacts)} artifacts")
        print(f"Total size: {collection.total_size} bytes")

        # Cleanup old artifacts
        collector.cleanup_old_artifacts(args.cleanup_days)


if __name__ == "__main__":
    main()
