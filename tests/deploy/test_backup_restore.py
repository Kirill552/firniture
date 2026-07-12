from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKUP = ROOT / "deploy" / "backup.sh"
RESTORE = ROOT / "deploy" / "restore.sh"


def run_script(script: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    command_env = os.environ.copy()
    if env:
        command_env.update(env)
    return subprocess.run(
        ["bash", script.relative_to(ROOT).as_posix(), *args],
        cwd=ROOT,
        env=command_env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_backup_fails_closed_without_explicit_paths() -> None:
    result = run_script(BACKUP)

    assert result.returncode != 0
    assert "--source" in result.stderr
    assert "--output" in result.stderr
    assert "--recipients-file" in result.stderr


def test_backup_rejects_unknown_argument() -> None:
    result = run_script(
        BACKUP,
        "--source",
        "/source",
        "--output",
        "/offsite/archive.tar.age",
        "--recipient-file",
        "/keys/recipient.txt",
        "--destination",
        "/other",
    )

    assert result.returncode != 0
    assert "unknown option" in result.stderr.lower()


def test_backup_dry_run_describes_encryption_and_checksum_contract() -> None:
    archive = "/offsite/backup.tar.age"
    result = run_script(
        BACKUP,
        "--source",
        "/source",
        "--output",
        archive,
        "--recipients-file",
        "/keys/recipient.txt",
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    assert "tar --create --file -" in result.stdout
    assert "age --encrypt --recipients-file" in result.stdout
    assert archive in result.stdout
    assert f"sha256sum {archive}" in result.stdout



def test_restore_fails_closed_without_explicit_paths() -> None:
    result = run_script(RESTORE)

    assert result.returncode != 0
    assert "--archive" in result.stderr
    assert "--destination" in result.stderr
    assert "--identity" in result.stderr


def test_restore_dry_run_describes_verification_decryption_and_extract_contract() -> None:
    archive = "/offsite/backup.tar.age"
    destination = "/restore"
    result = run_script(
        RESTORE,
        "--archive",
        archive,
        "--destination",
        destination,
        "--identity",
        "/keys/identity.txt",
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    assert f"sha256sum --check {archive}.sha256" in result.stdout
    assert "age --decrypt --identity" in result.stdout
    assert "tar --extract --file -" in result.stdout
    assert destination in result.stdout


def test_scripts_do_not_embed_credentials_or_destinations() -> None:
    for script in (BACKUP, RESTORE):
        text = script.read_text(encoding="utf-8")
        assert "postgres://" not in text
        assert "password" not in text.lower()
        assert "/var/" not in text
        assert "/opt/" not in text
