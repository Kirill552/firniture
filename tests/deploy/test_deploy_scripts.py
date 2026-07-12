from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "deploy" / "deploy.sh"
ROLLBACK = ROOT / "deploy" / "rollback.sh"
RELEASE_SHA = "a" * 40
TARGET_SHA = "b" * 40
PARSER = ROOT / "deploy" / "release_manifest.py"


def run_manifest_parser(manifest: Path, release_sha: str, compose_images: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PARSER), str(manifest), release_sha],
        input="\n".join(compose_images),
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )




def run_script(script: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    command_env = os.environ.copy()
    if env:
        command_env.update(env)
    # Use relative_to + as_posix() for portable / separators when invoking bash
    # scripts from Windows (via WSL bash.exe) and Linux CI. Matches backup/restore test helper.
    script_rel = script.relative_to(ROOT).as_posix()
    return subprocess.run(
        ["bash", script_rel, *args],
        cwd=ROOT,
        env=command_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def test_deploy_requires_explicit_release_sha_and_manifest() -> None:
    result = run_script(DEPLOY, "--dry-run")

    assert result.returncode != 0
    assert "--release-sha" in result.stderr
    assert "--manifest" in result.stderr


def test_deploy_rejects_non_immutable_release_sha() -> None:
    result = run_script(
        DEPLOY,
        "--release-sha",
        "latest",
        "--manifest",
        "/release/manifest.json",
        "--dry-run",
    )

    assert result.returncode != 0
    assert "sha" in result.stderr.lower()
def write_manifest(path: Path, *, release_sha: str, image_sha: str | None = None, note: str | None = None) -> None:
    image_sha = image_sha or release_sha
    manifest: dict[str, object] = {
        "release_sha": release_sha,
        "images": {
            "api": f"ghcr.io/example/api:{image_sha}",
            "web": f"ghcr.io/example/web:{image_sha}",
            "worker": f"ghcr.io/example/api:{image_sha}",
        },
    }
    if note is not None:
        manifest["note"] = note

    path.write_text(json.dumps(manifest), encoding="utf-8")


def test_deploy_rejects_release_sha_only_in_unrelated_text() -> None:
    manifest = ROOT / "tests" / "deploy" / "release-unrelated-sha.json"
    compose = ROOT / "tests" / "deploy" / "release-unrelated-sha-compose.yml"
    write_manifest(manifest, release_sha="c" * 40, note=RELEASE_SHA)
    compose.write_text("services: {}\n", encoding="utf-8")
    try:
        result = run_script(
            DEPLOY,
            "--release-sha",
            RELEASE_SHA,
            "--manifest",
            manifest.relative_to(ROOT).as_posix(),
            "--compose-file",
            compose.relative_to(ROOT).as_posix(),
        )
    finally:
        manifest.unlink(missing_ok=True)
        compose.unlink(missing_ok=True)

    assert result.returncode != 0
    assert "release_sha" in result.stderr.lower()


@pytest.mark.parametrize("script", [DEPLOY, ROLLBACK])
def test_scripts_reject_malformed_release_manifest(script: Path) -> None:
    manifest = ROOT / "tests" / "deploy" / f"{script.stem}-malformed.json"
    compose = ROOT / "tests" / "deploy" / f"{script.stem}-malformed-compose.yml"
    manifest.write_text('{"release_sha":', encoding="utf-8")
    compose.write_text("services: {}\n", encoding="utf-8")
    try:
        result = run_script(
            script,
            "--release-sha",
            RELEASE_SHA if script == DEPLOY else TARGET_SHA,
            "--manifest",
            manifest.relative_to(ROOT).as_posix(),
            "--compose-file",
            compose.relative_to(ROOT).as_posix(),
            "--backup-command",
            "true",
        )
    finally:
        manifest.unlink(missing_ok=True)
        compose.unlink(missing_ok=True)

    assert result.returncode != 0
    assert "json" in result.stderr.lower() or "manifest" in result.stderr.lower()


@pytest.mark.parametrize("script", [DEPLOY, ROLLBACK])
def test_scripts_reject_release_sha_with_unbound_image_references(script: Path) -> None:
    expected_sha = RELEASE_SHA if script == DEPLOY else TARGET_SHA
    manifest = ROOT / "tests" / "deploy" / f"{script.stem}-image-mismatch.json"
    compose = ROOT / "tests" / "deploy" / f"{script.stem}-image-mismatch-compose.yml"
    write_manifest(manifest, release_sha=expected_sha, image_sha="c" * 40, note=expected_sha)
    compose.write_text("services: {}\n", encoding="utf-8")
    try:
        result = run_script(
            script,
            "--release-sha",
            expected_sha,
            "--manifest",
            manifest.relative_to(ROOT).as_posix(),
            "--compose-file",
            compose.relative_to(ROOT).as_posix(),
            "--backup-command",
            "true",
        )
    finally:
        manifest.unlink(missing_ok=True)
        compose.unlink(missing_ok=True)

    assert result.returncode != 0
    assert "image" in result.stderr.lower()


def test_deploy_rejects_manifest_that_does_not_reference_release_sha() -> None:
    manifest = ROOT / "tests" / "deploy" / "release-mismatch.json"
    manifest.write_text('{"release_sha":"c"}\n', encoding="utf-8")
    try:
        result = run_script(
            DEPLOY,
            "--release-sha",
            RELEASE_SHA,
            "--manifest",
            "tests/deploy/release-mismatch.json",
        )
    finally:
        manifest.unlink(missing_ok=True)

    assert result.returncode != 0
    assert "release_sha" in result.stderr.lower()
def test_rollback_rejects_manifest_that_does_not_reference_target_sha() -> None:
    manifest = ROOT / "tests" / "deploy" / "rollback-mismatch.json"
    manifest.write_text('{"release_sha":"c"}\n', encoding="utf-8")
    try:
        result = run_script(
            ROLLBACK,
            "--release-sha",
            TARGET_SHA,
            "--manifest",
            "tests/deploy/rollback-mismatch.json",
            "--backup-command",
            "true",
        )
    finally:
        manifest.unlink(missing_ok=True)

    assert result.returncode != 0
    assert "release_sha" in result.stderr.lower()



def test_deploy_dry_run_describes_safe_release_flow_without_filesystem_access() -> None:
    result = run_script(
        DEPLOY,
        "--release-sha",
        RELEASE_SHA,
        "--manifest",
        "/release/manifest.json",
        "--compose-file",
        "/release/compose.yml",
        "--backup-command",
        "./deploy/backup.sh --dry-run",
        "--health-command",
        "curl --fail http://localhost/health",
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    assert RELEASE_SHA in result.stdout
    assert "/release/manifest.json" in result.stdout
    assert "/release/compose.yml" in result.stdout
    assert "preflight" in result.stdout.lower()
    assert "backup" in result.stdout.lower()
    assert "migration" in result.stdout.lower()
    assert "health" in result.stdout.lower()
    assert ":latest" not in result.stdout


def test_rollback_requires_explicit_release_sha_and_manifest() -> None:
    result = run_script(ROLLBACK, "--dry-run")

    assert result.returncode != 0
    assert "--release-sha" in result.stderr
    assert "--manifest" in result.stderr


def test_rollback_refuses_destructive_down_migration_without_approval_token() -> None:
    result = run_script(
        ROLLBACK,
        "--release-sha",
        TARGET_SHA,
        "--manifest",
        "/release/manifest.json",
        "--down-migration-command",
        "alembic downgrade -1",
        "--dry-run",
    )

    assert result.returncode != 0
    assert "approval" in result.stderr.lower()
    assert "refus" in result.stderr.lower() or "required" in result.stderr.lower()


def test_rollback_dry_run_requires_approval_and_prints_immutable_target() -> None:
    result = run_script(
        ROLLBACK,
        "--release-sha",
        TARGET_SHA,
        "--manifest",
        "/release/manifest.json",
        "--down-migration-command",
        "alembic downgrade -1",
        "--approval-token",

        "human-approved-release",
        "--backup-command",
        "./deploy/backup.sh --dry-run",
        "--health-command",
        "curl --fail http://localhost/health",
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    assert TARGET_SHA in result.stdout
    assert "down migration" in result.stdout.lower()
    assert "approval" in result.stdout.lower()
    assert ":latest" not in result.stdout
@pytest.mark.parametrize("script", [DEPLOY, ROLLBACK])
def test_scripts_accept_image_references_bound_to_approved_digests(script: Path) -> None:
    digest = "sha256:" + "d" * 64
    manifest = ROOT / "tests" / "deploy" / f"{script.stem}-digest.json"
    compose = ROOT / "tests" / "deploy" / f"{script.stem}-digest-compose.yml"
    manifest.write_text(
        json.dumps(
            {
                "release_sha": RELEASE_SHA if script == DEPLOY else TARGET_SHA,
                "images": {
                    service: {
                        "reference": f"ghcr.io/example/{service}@{digest}",
                        "approved_digest": digest,
                    }
                    for service in ("api", "web", "worker")
                },
            }
        ),
        encoding="utf-8",
    )
    compose.write_text("services: {}\n", encoding="utf-8")
    try:
        result = run_script(
            script,
            "--release-sha",
            RELEASE_SHA if script == DEPLOY else TARGET_SHA,
            "--manifest",
            manifest.relative_to(ROOT).as_posix(),
            "--compose-file",
            compose.relative_to(ROOT).as_posix(),
        )
    finally:
        manifest.unlink(missing_ok=True)
        compose.unlink(missing_ok=True)

    assert result.returncode != 0
    assert "--backup-command" in result.stderr


def test_deploy_rejects_manifest_reference_not_in_resolved_compose_images(tmp_path: Path) -> None:
    manifest = tmp_path / "compose-mismatch.json"
    write_manifest(manifest, release_sha=RELEASE_SHA)
    content = json.loads(manifest.read_text(encoding="utf-8"))
    content["images"]["web"] = f"ghcr.io/other/web:{RELEASE_SHA}"
    manifest.write_text(json.dumps(content), encoding="utf-8")

    result = run_manifest_parser(
        manifest,
        RELEASE_SHA,
        [
            f"ghcr.io/example/api:{RELEASE_SHA}",
            f"ghcr.io/example/api:{RELEASE_SHA}",
            f"ghcr.io/example/web:{RELEASE_SHA}",
        ],
    )

    assert result.returncode != 0
    assert "compose image" in result.stderr.lower()


@pytest.mark.parametrize("script", [DEPLOY, ROLLBACK])
def test_scripts_order_backup_compose_validation_migration_and_start(script: Path) -> None:
    text = script.read_text(encoding="utf-8")
    migration_marker = "run_hook migration" if script == DEPLOY else "run_hook down-migration"
    compose_marker = 'docker compose -f "$COMPOSE_FILE" config --images'

    assert text.index("run_hook preflight") < text.index("run_hook backup")
    assert text.index("run_hook backup") < text.index(compose_marker)
    assert text.index(compose_marker) < text.index("docker compose -f \"$COMPOSE_FILE\" pull")
    assert text.index("docker compose -f \"$COMPOSE_FILE\" pull") < text.index(migration_marker)
    assert text.index(migration_marker) < text.index("STACK_STARTED=1")


@pytest.mark.parametrize("script", [DEPLOY, ROLLBACK])
def test_scripts_leave_partial_release_for_operator_controlled_recovery(script: Path) -> None:
    text = script.read_text(encoding="utf-8")

    assert "docker compose -f \"$COMPOSE_FILE\" ps -aq api worker web" in text
    assert "removing only target-release containers" in text


def test_scripts_arm_failure_cleanup_before_compose_start() -> None:
    for script in (DEPLOY, ROLLBACK):
        text = script.read_text(encoding="utf-8")
        assert "STACK_STARTED=1" in text
        assert text.index("STACK_STARTED=1") < text.index("docker compose -f", text.index("STACK_STARTED=1"))




@pytest.mark.parametrize("script", [DEPLOY, ROLLBACK])
def test_scripts_enable_strict_shell_mode(script: Path) -> None:
    text = script.read_text(encoding="utf-8")

    assert "set -Eeuo pipefail" in text
