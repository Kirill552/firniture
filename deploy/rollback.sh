#!/usr/bin/env bash
set -Eeuo pipefail
usage() {
    cat >&2 <<'USAGE'
Использование: rollback.sh --release-sha SHA --manifest FILE [options]
Восстанавливает неизменяемый релиз SHA. Сначала выполняются предпроверка и
резервное копирование. Деструктивная миграция запрещена без
--approval-token, явно выданного владельцем релиза.
Флаг --dry-run печатает план без доступа к файлам и внешним командам.
Манифест должен быть JSON с точным release_sha и ссылками образов
api/web/worker с этим SHA или одобренными sha256-дайджестами.
Параметры:
  --compose-file FILE              Production Compose file (по умолчанию: docker-compose.prod.yml)
  --preflight-command COMMAND      Команда предпроверки
  --backup-command COMMAND         Обязательная команда резервного копирования
  --down-migration-command COMMAND Деструктивная команда миграции
  --approval-token TOKEN            Подтверждение деструктивной миграции
  --health-command COMMAND         Команда проверки состояния (по умолчанию: Compose service check)
  --dry-run                        Напечатать план без доступа к файлам и командам
USAGE
}
die() {
    printf 'rollback.sh: %s\n' "$1" >&2
    exit 2
}
require_value() {
    [[ $# -ge 2 && -n "$2" ]] || die "$1 requires a value"
}

RELEASE_SHA=''
MANIFEST=''
COMPOSE_FILE='docker-compose.prod.yml'
PREFLIGHT_COMMAND=''
BACKUP_COMMAND=''
DOWN_MIGRATION_COMMAND=''
APPROVAL_TOKEN=''
HEALTH_COMMAND=''
DRY_RUN=0

while (($# > 0)); do
    case "$1" in
        --release-sha)
            require_value "$1" "${2-}"
            RELEASE_SHA=$2
            shift 2
            ;;
        --manifest)
            require_value "$1" "${2-}"
            MANIFEST=$2
            shift 2
            ;;
        --compose-file)
            require_value "$1" "${2-}"
            COMPOSE_FILE=$2
            shift 2
            ;;
        --preflight-command)
            require_value "$1" "${2-}"
            PREFLIGHT_COMMAND=$2
            shift 2
            ;;
        --backup-command)
            require_value "$1" "${2-}"
            BACKUP_COMMAND=$2
            shift 2
            ;;
        --down-migration-command)
            require_value "$1" "${2-}"
            DOWN_MIGRATION_COMMAND=$2
            shift 2
            ;;
        --approval-token)
            require_value "$1" "${2-}"
            APPROVAL_TOKEN=$2
            shift 2
            ;;
        --health-command)
            require_value "$1" "${2-}"
            HEALTH_COMMAND=$2
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

[[ -n "$RELEASE_SHA" ]] || { usage; die "--release-sha must be provided"; }
[[ -n "$MANIFEST" ]] || { usage; die "--manifest must be provided"; }
[[ "$RELEASE_SHA" =~ ^[0-9a-f]{40,64}$ ]] || die "release SHA must be 40-64 lowercase hexadecimal characters"
if [[ -n "$DOWN_MIGRATION_COMMAND" && -z "$APPROVAL_TOKEN" ]]; then
    die "destructive down migration refused: explicit approval token is required"
fi

: "${HEALTH_COMMAND:=docker compose -f \"$COMPOSE_FILE\" ps --status running}"
: "${PREFLIGHT_COMMAND:=docker compose -f \"$COMPOSE_FILE\" config --quiet}"

print_plan() {
    printf 'rollback release SHA: %s\n' "$RELEASE_SHA"
    printf 'release manifest: %s\n' "$MANIFEST"
    printf 'compose file: %s\n' "$COMPOSE_FILE"
    printf 'immutable image tag: %s\n' "$RELEASE_SHA"
    printf 'preflight hook: %s\n' "$PREFLIGHT_COMMAND"
    if [[ -n "$BACKUP_COMMAND" ]]; then
        printf 'backup hook: %s\n' "$BACKUP_COMMAND"
    else
        printf 'backup hook: <required command>\n'
    fi
    if [[ -n "$DOWN_MIGRATION_COMMAND" ]]; then
        printf 'down migration hook: %s\n' "$DOWN_MIGRATION_COMMAND"
        printf 'approval token: supplied\n'
    else
        printf 'down migration hook: none\n'
    fi
    printf 'health hook: %s\n' "$HEALTH_COMMAND"
    printf 'compose pull: docker compose -f %q pull\n' "$COMPOSE_FILE"
    printf 'compose up: docker compose -f %q up --detach --remove-orphans\n' "$COMPOSE_FILE"
}

validate_manifest() {
    local python_bin compose_images=${1-}
    local parser="${BASH_SOURCE[0]%/*}/release_manifest.py"
    python_bin=$(command -v python3 || command -v python || true)
    [[ -n "$python_bin" ]] || die "required command not found: python3 or python"
    [[ -f "$parser" ]] || die "release manifest parser does not exist: $parser"

    if ! printf '%s\n' "$compose_images" | "$python_bin" "$parser" "$MANIFEST" "$RELEASE_SHA"; then
        die "release manifest validation failed"
    fi
}

if ((DRY_RUN)); then
    [[ -n "$BACKUP_COMMAND" ]] || printf 'DRY-RUN warning: backup hook is required for a real rollback\n' >&2
    print_plan
    exit 0
fi

[[ -f "$MANIFEST" ]] || die "release manifest does not exist: $MANIFEST"
[[ -s "$MANIFEST" ]] || die "release manifest is empty: $MANIFEST"
[[ -f "$COMPOSE_FILE" ]] || die "compose file does not exist: $COMPOSE_FILE"
validate_manifest
[[ -n "$BACKUP_COMMAND" ]] || die "--backup-command is required for a real rollback"
command -v docker >/dev/null 2>&1 || die "required command not found: docker"

export RELEASE_SHA
export RELEASE_MANIFEST="$MANIFEST"
export COMPOSE_FILE
export IMAGE_TAG="$RELEASE_SHA"

run_hook() {
    local hook_name=$1
    local command=$2
    [[ -n "$command" ]] || die "$hook_name hook is not configured"
    printf 'running %s hook\n' "$hook_name"
    bash -c "$command"
}

STACK_STARTED=0
cleanup_on_error() {
    if ((STACK_STARTED)); then
        printf 'rollback.sh: rollback failed; removing only target-release containers\n' >&2
        while IFS= read -r container; do
            [[ -n "$container" ]] || continue
            image=$(docker inspect --format '{{.Config.Image}}' "$container" 2>/dev/null || true)
            if [[ "$image" == *":$RELEASE_SHA" ]]; then
                docker rm -f "$container" || true
            fi
        done < <(docker compose -f "$COMPOSE_FILE" ps -aq api worker web || true)
    fi
}
trap cleanup_on_error ERR

run_hook preflight "$PREFLIGHT_COMMAND"
run_hook backup "$BACKUP_COMMAND"
COMPOSE_IMAGES=$(docker compose -f "$COMPOSE_FILE" config --images) ||
    die "unable to resolve Compose image references"
validate_manifest "$COMPOSE_IMAGES"
printf 'pulling immutable rollback images for %s\n' "$RELEASE_SHA"
docker compose -f "$COMPOSE_FILE" pull
if [[ -n "$DOWN_MIGRATION_COMMAND" ]]; then
    printf 'running approved destructive down migration\n'
    RELEASE_APPROVAL_TOKEN="$APPROVAL_TOKEN" run_hook down-migration "$DOWN_MIGRATION_COMMAND"
fi
printf 'starting rollback release %s\n' "$RELEASE_SHA"
STACK_STARTED=1
docker compose -f "$COMPOSE_FILE" up --detach --remove-orphans
run_hook health "$HEALTH_COMMAND"
trap - ERR
printf 'rollback completed: %s\n' "$RELEASE_SHA"
