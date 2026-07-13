import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CADDYFILE = ROOT / "deploy" / "Caddyfile"
COMPOSE = ROOT / "docker-compose.prod.yml"
API_DOCKERFILE = ROOT / "api" / "Dockerfile"
WEB_DOCKERFILE = ROOT / "web" / "Dockerfile"


def _caddyfile() -> str:
    return CADDYFILE.read_text(encoding="utf-8")


def _published_ports(service: str) -> list[str]:
    service_block = _service_block(service)
    return [
        f"{host}:{container}"
        for host, container in re.findall(
            r'^\s+- "(?P<host>\d+):(?P<container>\d+)"$', service_block, re.MULTILINE
        )
    ]


def test_production_publishes_only_caddy_http_ports() -> None:
    assert _published_ports("caddy") == ["80:80", "443:443"]
    for service in ("api", "web", "minio"):
        assert _published_ports(service) == []

    services = ("postgres", "redis", "minio", "api", "worker", "web", "caddy")
    host_ports = {
        int(mapping.split(":", maxsplit=1)[0])
        for service in services
        for mapping in _published_ports(service)
    }
    assert host_ports == {80, 443}


_PRODUCTION_SERVICES = ("postgres", "redis", "minio", "api", "worker", "web", "caddy")
_IMAGE_TAG_TOKEN = "${IMAGE_TAG:?IMAGE_TAG must be set}"
_IMAGE_TAG_PATTERN = re.compile(r"^[0-9a-f]{40,64}$")
_DIGEST_PATTERN = re.compile(r"@sha256:[0-9a-f]{64}$")
_APP_IMAGE_REFERENCES = {
    "api": f"ghcr.io/kirill552/firniture/api:{_IMAGE_TAG_TOKEN}",
    "worker": f"ghcr.io/kirill552/firniture/api:{_IMAGE_TAG_TOKEN}",
    "web": f"ghcr.io/kirill552/firniture/web:{_IMAGE_TAG_TOKEN}",
}


def _image_references() -> dict[str, str]:
    references = {}
    for service in _PRODUCTION_SERVICES:
        match = re.search(r"^    image:\s+(?P<image>.+)$", _service_block(service), re.MULTILINE)
        assert match, f"Service {service!r} must declare an image"
        references[service] = match.group("image")
    return references


def _validate_image_tag(image_tag: str) -> bool:
    return bool(_IMAGE_TAG_PATTERN.fullmatch(image_tag))


def _render_image_reference(image: str, image_tag: str) -> str:
    if _IMAGE_TAG_TOKEN not in image:
        return image
    if not _validate_image_tag(image_tag):
        raise ValueError("IMAGE_TAG must be a lowercase 40-64 character commit SHA")
    return image.replace(_IMAGE_TAG_TOKEN, image_tag)


def test_production_minio_image_and_credentials_are_pinned() -> None:
    minio = _service_block("minio")

    minio_image = _image_references()["minio"]
    assert _DIGEST_PATTERN.search(minio_image)
    assert re.fullmatch(
        r"minio/minio:RELEASE\.\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z@sha256:[0-9a-f]{64}",
        minio_image,
    )
    assert re.search(
        r"^\s+MINIO_ROOT_USER:\s+\$\{S3_ACCESS_KEY:\?[^}]+\}$",
        minio,
        re.MULTILINE,
    )
    assert re.search(
        r"^\s+MINIO_ROOT_PASSWORD:\s+\$\{S3_SECRET_KEY:\?[^}]+\}$",
        minio,
        re.MULTILINE,
    )
    assert "minio123" not in minio


def test_production_images_are_immutable_for_every_service() -> None:
    images = _image_references()

    assert set(images) == set(_PRODUCTION_SERVICES)
    assert all("latest" not in image.lower() for image in images.values())

    for service, image in images.items():
        if service in _APP_IMAGE_REFERENCES:
            assert image == _APP_IMAGE_REFERENCES[service], (
                f"{service} must use the verified release SHA contract"
            )
        else:
            assert _DIGEST_PATTERN.search(image), f"{service} must use a verified digest"


def test_production_images_require_strict_image_tag_contract() -> None:
    images = _image_references()
    valid_tag = "0123456789abcdef" * 3

    for service in ("api", "worker", "web"):
        rendered = _render_image_reference(images[service], valid_tag)
        assert rendered.endswith(f":{valid_tag}")

    invalid_tags = (
        "",
        "latest",
        "main",
        "v1.2.3",
        "A" * 40,
        "a" * 39,
        "a" * 65,
        "a" * 39 + "g",
    )
    for invalid_tag in invalid_tags:
        assert not _validate_image_tag(invalid_tag)
        for service in ("api", "worker", "web"):
            try:
                _render_image_reference(images[service], invalid_tag)
            except ValueError:
                pass
            else:
                raise AssertionError(f"{service} accepted invalid IMAGE_TAG {invalid_tag!r}")

def _service_block(service: str) -> str:
    compose = COMPOSE.read_text(encoding="utf-8")
    service_match = re.search(
        rf"^  {re.escape(service)}:\n(?P<body>.*?)(?=^  [a-zA-Z0-9_-]+:|^networks:|^volumes:)",
        compose,
        re.MULTILINE | re.DOTALL,
    )
    assert service_match, f"Service {service!r} is missing from production Compose"
    return service_match.group("body")


def test_production_proxy_network_connects_caddy_to_api_and_web() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")

    assert re.search(r"^  caddy:\n", compose, re.MULTILINE)
    assert re.search(r"^networks:\n(?:.*\n)*?^  proxy:\s*$", compose, re.MULTILINE)
    for service in ("caddy", "api", "web"):
        service_block = _service_block(service)
        assert re.search(
            r"^    networks:\n(?:^      - .*\n)*?^      - proxy\s*$",
            service_block,
            re.MULTILINE,
        ), f"Service {service!r} must join the proxy network"

    caddy = _service_block("caddy")
    assert re.search(r'image:\s*caddy:[^\s]+', caddy)
    assert re.search(r'^\s+- "80:80"$', caddy, re.MULTILINE)
    assert re.search(r'^\s+- "443:443"$', caddy, re.MULTILINE)
    assert "depends_on:" in caddy
    assert "condition: service_healthy" in caddy

    web = _service_block("web")
    assert "api:" in web
    assert "condition: service_healthy" in web


def test_api_readiness_checks_dependencies_without_using_liveness_endpoint() -> None:
    api = _service_block("api")
    healthcheck = re.search(
        r"healthcheck:\n(?P<body>.*?)(?=^    [a-zA-Z0-9_-]+:)",
        api,
        re.MULTILINE | re.DOTALL,
    )
    assert healthcheck, "API must declare a separate readiness healthcheck"

    readiness = healthcheck.group("body")
    assert "python" in readiness
    assert "/health" not in readiness
    for dependency in ("127.0.0.1", "postgres", "redis", "minio"):
        assert dependency in readiness, f"Readiness must probe {dependency!r}"

    assert "depends_on:" in api
    assert "condition: service_healthy" in api


def test_caddy_handler_order_and_exact_api_upstream() -> None:
    config = _caddyfile()
    api_handler_start = config.find("handle @api {")
    api_proxy_start = config.find("reverse_proxy api:8000", api_handler_start)
    fallback_handler = re.search(
        r"(?P<handler>handle\s*\{\s*reverse_proxy\s+web:3000\s*\})",
        config,
        re.DOTALL,
    )
    assert api_handler_start >= 0 and api_proxy_start >= 0 and fallback_handler
    assert api_handler_start < api_proxy_start < fallback_handler.start(), (
        "API handler must precede web fallback"
    )

    matcher = re.search(r"@api\s+path\s+(?P<paths>[^\n]+)", config)
    assert matcher, "Caddy must declare an API path matcher"
    assert "/api" in matcher.group("paths").split()
    assert "/api/*" in matcher.group("paths").split()

    api_region = config[matcher.start() : fallback_handler.start()]
    assert "reverse_proxy web:3000" not in api_region
    assert "header_up X-Forwarded-For {remote_host}" in api_region

def _exposed_port(dockerfile: Path) -> int:
    match = re.search(r"^EXPOSE (?P<port>\d+)$", dockerfile.read_text(encoding="utf-8"), re.MULTILINE)
    assert match, f"{dockerfile} must declare EXPOSE"
    return int(match.group("port"))


def test_caddy_routes_http_to_https_and_api_to_backend() -> None:
    config = _caddyfile()
    api_port = _exposed_port(API_DOCKERFILE)
    web_port = _exposed_port(WEB_DOCKERFILE)

    assert "http://avtoraskroy.ru" in config
    assert "https://avtoraskroy.ru" in config
    assert re.search(r"@api\s+path\s+/api\s+/api/\*", config)
    assert f"reverse_proxy api:{api_port}" in config
    assert f"reverse_proxy web:{web_port}" in config


def test_caddy_upstreams_match_container_expose_contract() -> None:
    config = _caddyfile()
    assert f"api:{_exposed_port(API_DOCKERFILE)}" in config
    assert f"web:{_exposed_port(WEB_DOCKERFILE)}" in config


def test_caddy_https_headers_are_safe_and_scoped_to_tls_site() -> None:
    config = _caddyfile()
    http_config, https_config = config.split("https://avtoraskroy.ru:443", maxsplit=1)
    assert "Strict-Transport-Security" not in http_config

    assert 'Strict-Transport-Security "max-age=31536000; includeSubDomains"' in https_config
    assert 'X-Content-Type-Options "nosniff"' in https_config
    assert 'X-Frame-Options "DENY"' in https_config
    assert 'Referrer-Policy "strict-origin-when-cross-origin"' in https_config
    assert "-Server" in https_config


def test_caddy_exposes_backend_health_contract() -> None:
    config = _caddyfile()
    assert re.search(r"handle\s+/health\s*\{\s*reverse_proxy\s+api:\d+\s*\}", config, re.DOTALL)
