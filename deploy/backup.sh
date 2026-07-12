#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
    cat >&2 <<'USAGE'
Usage: backup.sh --source DIR --output FILE --recipients-file FILE [--dry-run]

Create a tar archive, encrypt it with age, and write a SHA-256 sidecar.
All paths are required explicitly; dry-run skips filesystem and command access.
USAGE
}

die() {
    printf 'backup.sh: %s\n' "$1" >&2
    exit 2
}

require_value() {
    [[ $# -ge 2 && -n "$2" ]] || die "$1 requires a value"
}

SOURCE=''
OUTPUT=''
RECIPIENTS_FILE=''
DRY_RUN=0

while (($# > 0)); do
    case "$1" in
        --source)
            require_value "$1" "${2-}"
            SOURCE=$2
            shift 2
            ;;
        --output)
            require_value "$1" "${2-}"
            OUTPUT=$2
            shift 2
            ;;
        --recipients-file)
            require_value "$1" "${2-}"
            RECIPIENTS_FILE=$2
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

if [[ -z "$SOURCE" || -z "$OUTPUT" || -z "$RECIPIENTS_FILE" ]]; then
    usage
    die "all required options must be provided"
fi

CHECKSUM="${OUTPUT}.sha256"

print_plan() {
    printf 'DRY-RUN: tar --create --file - --directory %q . | age --encrypt --recipients-file %q > %q\n' \
        "$SOURCE" "$RECIPIENTS_FILE" "$OUTPUT"
    printf 'DRY-RUN: sha256sum %q > %q\n' "$OUTPUT" "$CHECKSUM"
}

if ((DRY_RUN)); then
    print_plan
    exit 0
fi

command -v tar >/dev/null 2>&1 || die "required command not found: tar"
command -v age >/dev/null 2>&1 || die "required command not found: age"
command -v sha256sum >/dev/null 2>&1 || die "required command not found: sha256sum"

[[ -d "$SOURCE" ]] || die "source directory does not exist: $SOURCE"
[[ -f "$RECIPIENTS_FILE" ]] || die "recipients file does not exist: $RECIPIENTS_FILE"
[[ ! -e "$OUTPUT" ]] || die "output already exists: $OUTPUT"
[[ ! -e "$CHECKSUM" ]] || die "checksum already exists: $CHECKSUM"

OUTPUT_DIR=$(dirname -- "$OUTPUT")
[[ -d "$OUTPUT_DIR" ]] || die "output directory does not exist: $OUTPUT_DIR"

TEMP_ARCHIVE=$(mktemp "${OUTPUT}.part.XXXXXX")
TEMP_CHECKSUM=$(mktemp "${CHECKSUM}.part.XXXXXX")
cleanup() {
    rm -f -- "$TEMP_ARCHIVE" "$TEMP_CHECKSUM"
}
trap cleanup EXIT

if ! tar --create --file - --directory "$SOURCE" . \
    | age --encrypt --recipients-file "$RECIPIENTS_FILE" > "$TEMP_ARCHIVE"; then
    die "archive encryption failed"
fi

DIGEST_LINE=$(sha256sum "$TEMP_ARCHIVE")
DIGEST=${DIGEST_LINE%% *}
printf '%s  %s\n' "$DIGEST" "$(basename -- "$OUTPUT")" > "$TEMP_CHECKSUM"
mv -- "$TEMP_ARCHIVE" "$OUTPUT"
mv -- "$TEMP_CHECKSUM" "$CHECKSUM"
trap - EXIT
printf 'backup created: %s\nchecksum created: %s\n' "$OUTPUT" "$CHECKSUM"
