import http from "k6/http";
import { check } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8000";
const LOAD_TEST_TOKEN = __ENV.LOAD_TEST_TOKEN || "";

// Этот JSON — единственный источник сценариев, фикстур и целевых порогов.
// Пороги являются кандидатами для согласования; capacity/SLO остаются human-gated.
const WORKLOAD_DEFINITION_JSON = String.raw`{
  "version": 1,
  "approval_status": "deferred",
  "human_gates": ["measured_capacity", "slo_approval"],
  "scenarios": {
    "anonymous_upload": {"executor": "constant-arrival-rate", "rate": 2, "timeUnit": "1s", "duration": "60s", "preAllocatedVUs": 2, "maxVUs": 10, "method": "POST", "endpoint": "/api/v1/orders/anonymous", "auth": "anonymous"},
    "authenticated_bom_edit": {"executor": "constant-arrival-rate", "rate": 2, "timeUnit": "1s", "duration": "60s", "preAllocatedVUs": 2, "maxVUs": 10, "method": "PATCH", "endpoint": "/api/v1/orders/{order_id}/bom", "auth": "required"},
    "ai_extraction": {"executor": "constant-arrival-rate", "rate": 1, "timeUnit": "1s", "duration": "60s", "preAllocatedVUs": 1, "maxVUs": 5, "method": "POST", "endpoint": "/api/v1/spec/extract-from-image", "auth": "anonymous"},
    "cam_job": {"executor": "constant-arrival-rate", "rate": 1, "timeUnit": "1s", "duration": "60s", "preAllocatedVUs": 1, "maxVUs": 5, "method": "POST", "endpoint": "/api/v1/cam/dxf", "auth": "required"},
    "artifact_download": {"executor": "constant-arrival-rate", "rate": 1, "timeUnit": "1s", "duration": "60s", "preAllocatedVUs": 1, "maxVUs": 5, "method": "GET", "endpoint": "/api/v1/cam/jobs/{job_id}/download", "auth": "required"},
    "backlog": {"executor": "constant-arrival-rate", "rate": 1, "timeUnit": "1s", "duration": "60s", "preAllocatedVUs": 1, "maxVUs": 5, "method": "GET", "endpoint": "/api/v1/cam/jobs?limit=50&offset=0", "auth": "required"}
  },
  "thresholds": {
    "http_req_failed": ["rate<0.01"],
    "http_req_duration{scenario:anonymous_upload}": ["p(95)<1500"],
    "http_req_duration{scenario:authenticated_bom_edit}": ["p(95)<1200"],
    "http_req_duration{scenario:ai_extraction}": ["p(95)<5000"],
    "http_req_duration{scenario:cam_job}": ["p(95)<2000"],
    "http_req_duration{scenario:artifact_download}": ["p(95)<1500"],
    "http_req_duration{scenario:backlog}": ["p(95)<1200"]
  },
  "fixtures": {
    "order_id": "00000000-0000-4000-8000-000000000036",
    "job_id": "00000000-0000-4000-8000-000000000037",
    "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
    "anonymous_order": {"customer_ref": "load-anonymous", "notes": "deterministic-load-fixture-v1"},
    "bom_patch": {
      "dimensions": {"width_mm": 600, "height_mm": 720, "depth_mm": 560},
      "panels": [{"id": "00000000-0000-4000-8000-000000000038", "width_mm": 600, "height_mm": 720}]
    },
    "cam_job": {
      "order_id": "00000000-0000-4000-8000-000000000036",
      "panels": [{"name": "load-panel", "width_mm": 600, "height_mm": 720, "thickness_mm": 16, "material": "ЛДСП"}],
      "optimize_layout": true,
      "idempotency_key": "load-cam-fixture-v1"
    }
  }
}`;

export const workloadDefinition = JSON.parse(WORKLOAD_DEFINITION_JSON);

const fixture = workloadDefinition.fixtures;
const jsonParams = () => ({
  headers: {
    "Content-Type": "application/json",
    ...(LOAD_TEST_TOKEN ? { Authorization: `Bearer ${LOAD_TEST_TOKEN}` } : {}),
  },
  tags: { workload: "order-flow" },
});

const requestUrl = (path) => `${BASE_URL}${path}`;

function assertResponse(response, name) {
  check(response, {
    [`${name} returns a successful HTTP status`]: (result) =>
      result.status >= 200 && result.status < 400,
  });
}

function requireAuth(name) {
  if (LOAD_TEST_TOKEN) return true;
  check({ token: LOAD_TEST_TOKEN }, {
    [`${name} requires LOAD_TEST_TOKEN`]: (result) => Boolean(result.token),
  });
  return false;
}

export function anonymous_upload() {
  const response = http.post(
    requestUrl(workloadDefinition.scenarios.anonymous_upload.endpoint),
    JSON.stringify(fixture.anonymous_order),
    jsonParams(),
  );
  assertResponse(response, "anonymous upload");
}

export function authenticated_bom_edit() {
  if (!requireAuth("authenticated BOM edit")) return;
  const endpoint = `/api/v1/orders/${fixture.order_id}/bom`;
  const response = http.patch(requestUrl(endpoint), JSON.stringify(fixture.bom_patch), jsonParams());
  assertResponse(response, "authenticated BOM edit");
}

export function ai_extraction() {
  const payload = {
    image_base64: fixture.image_base64,
    image_mime_type: "image/png",
    language_hint: "ru",
  };
  const response = http.post(
    requestUrl(workloadDefinition.scenarios.ai_extraction.endpoint),
    JSON.stringify(payload),
    jsonParams(),
  );
  assertResponse(response, "AI extraction");
}

export function cam_job() {
  if (!requireAuth("CAM job")) return;
  const response = http.post(
    requestUrl(workloadDefinition.scenarios.cam_job.endpoint),
    JSON.stringify(fixture.cam_job),
    jsonParams(),
  );
  assertResponse(response, "CAM job");
}

export function artifact_download() {
  if (!requireAuth("artifact download")) return;
  const endpoint = `/api/v1/cam/jobs/${fixture.job_id}/download`;
  const response = http.get(requestUrl(endpoint), jsonParams());
  assertResponse(response, "artifact download");
}

export function backlog() {
  if (!requireAuth("backlog")) return;
  const response = http.get(
    requestUrl(workloadDefinition.scenarios.backlog.endpoint),
    jsonParams(),
  );
  assertResponse(response, "CAM backlog");
}

const scenarios = Object.fromEntries(
  Object.entries(workloadDefinition.scenarios).map(([name, config]) => [name, {
    executor: config.executor,
    rate: config.rate,
    timeUnit: config.timeUnit,
    duration: config.duration,
    preAllocatedVUs: config.preAllocatedVUs,
    maxVUs: config.maxVUs,
    exec: name,
  }]),
);

export const options = {
  scenarios,
  thresholds: workloadDefinition.thresholds,
  tags: { workload: "order-flow" },
};
