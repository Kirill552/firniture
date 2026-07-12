#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
    cat >&2 <<'USAGE'
Usage: restore.sh --archive FILE --destination DIR --identity FILE [--checksum FILE] [--dry-run]

Verify a SHA-256 sidecar, decrypt an age archive, and extract it into a new directory.
All paths are required explicitly; dry-run skips filesystem and command access.
USAGE
}

die() {
    printf 'restore.sh: %s\n' "$1" >&2
    exit 2
}

require_value() {
    [[ $# -ge 2 && -n "$2" ]] || die "$1 requires a value"
}

ARCHIVE=''
DESTINATION=''
IDENTITY=''
CHECKSUM=''
DRY_RUN=0

while (($# > 0)); do
    case "$1" in
        --archive)
            require_value "$1" "${2-}"
            ARCHIVE=$2
            shift 2
            ;;
        --destination)
            require_value "$1" "${2-}"
            DESTINATION=$2
            shift 2
            ;;
        --identity)
            require_value "$1" "${2-}"
            IDENTITY=$2
            shift 2
            ;;
        --checksum)
            require_value "$1" "${2-}"
            CHECKSUM=$2
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        --*)
            die "unknown option: $1"
            ;;
        *)
            die "unexpected positional argument: $1"
            ;;
    esac
done

if [[ -z "$ARCHIVE" || -z "$DESTINATION" || -z "$IDENTITY" ]]; then
    usage
    die "all required options must be provided"
fi
[[ -n "$CHECKSUM" ]] || CHECKSUM="${ARCHIVE}.sha256"

print_plan() {
    printf 'DRY-RUN: sha256sum --check %q\n' "$CHECKSUM"
    printf 'DRY-RUN: age --decrypt --identity %q %q | tar --extract --file - --directory %q --no-same-owner\n' \
        "$IDENTITY" "$ARCHIVE" "$DESTINATION"
}

if ((DRY_RUN)); then
    print_plan
    exit 0
fi

command -v sha256sum >/dev/null 2>&1 || die "required command not found: sha256sum"
command -v age >/dev/null 2>&1 || die "required command not found: age"
command -v tar >/dev/null 2>&1 || die "required command not found: tar"

[[ -f "$ARCHIVE" ]] || die "archive does not exist: $ARCHIVE"
[[ -f "$CHECKSUM" ]] || die "checksum does not exist: $CHECKSUM"
[[ -f "$IDENTITY" ]] || die "identity file does not exist: $IDENTITY"
[[ ! -e "$DESTINATION" ]] || die "destination already exists: $DESTINATION"

ARCHIVE_DIR=$(cd -- "$(dirname -- "$ARCHIVE")" && pwd)
ARCHIVE_NAME=$(basename -- "$ARCHIVE")
ARCHIVE="$ARCHIVE_DIR/$ARCHIVE_NAME"
CHECKSUM_DIR=$(cd -- "$(dirname -- "$CHECKSUM")" && pwd)
CHECKSUM_NAME=$(basename -- "$CHECKSUM")
CHECKSUM="$CHECKSUM_DIR/$CHECKSUM_NAME"
DESTINATION_PARENT=$(dirname -- "$DESTINATION")
[[ -d "$DESTINATION_PARENT" ]] || die "destination parent does not exist: $DESTINATION_PARENT"

if ! read -r _ CHECKSUM_ENTRY < "$CHECKSUM"; then
    die "checksum file is malformed: $CHECKSUM"
fi
CHECKSUM_ENTRY=${CHECKSUM_ENTRY#\*}
[[ "$CHECKSUM_ENTRY" == "$ARCHIVE_NAME" ]] || die "checksum does not reference archive: $ARCHIVE_NAME"

if ! (cd -- "$ARCHIVE_DIR" && sha256sum --check "$CHECKSUM"); then
    die "checksum verification failed"
fi

mkdir -- "$DESTINATION"
if ! age --decrypt --identity "$IDENTITY" "$ARCHIVE" \
    | tar --extract --file - --directory "$DESTINATION" --no-same-owner; then
    rm -rf -- "$DESTINATION"
    die "archive decryption or extraction failed"
fi

printf 'restore completed: %s\n' "$DESTINATION"
