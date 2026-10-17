// Every API call in the app goes through this file (see plan.md section 4).
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function detailOf(data, status) {
  const detail = data && data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail[0].msg || "That request was not valid.";
  }
  return `Request failed (${status}).`;
}

async function request(path, { method = "GET", body, token, raw = false } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined && !raw) headers["Content-Type"] = "application/json";

  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : raw ? body : JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    throw new Error(
      "The API is not running. Start it with: uvicorn main:app --port 8000 (in backend/)."
    );
  }

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }
  if (!response.ok) throw new Error(detailOf(data, response.status));
  return data;
}

// --- auth ------------------------------------------------------------------

export function register({ email, name, password }) {
  return request("/auth/register", { method: "POST", body: { email, name, password } });
}

export function login({ email, password }) {
  return request("/auth/login", { method: "POST", body: { email, password } });
}

export function me(token) {
  return request("/auth/me", { token });
}

// --- projects --------------------------------------------------------------

export function listProjects({ q, category, tech, maxPrice } = {}) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (category) params.set("category", category);
  if (tech) params.set("tech", tech);
  if (maxPrice) params.set("max_price", maxPrice);
  const query = params.toString();
  return request(`/projects${query ? `?${query}` : ""}`);
}

export function getProject(id, token) {
  return request(`/projects/${id}`, { token });
}

export function myProjects(token) {
  return request("/projects/mine", { token });
}

export function createProject(token, payload) {
  return request("/projects", { method: "POST", body: payload, token });
}

export function updateProject(token, id, payload) {
  return request(`/projects/${id}`, { method: "PUT", body: payload, token });
}

export function publishProject(token, id) {
  return request(`/projects/${id}/publish`, { method: "POST", token });
}

export function uploadProjectFile(token, id, file) {
  const form = new FormData();
  form.append("file", file);
  return request(`/projects/${id}/file`, { method: "POST", body: form, token, raw: true });
}

// Bearer auth means the ZIP is fetched with the token and then saved from a blob.
export async function downloadProjectFile(token, id, filename) {
  const response = await fetch(`${API_URL}/projects/${id}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    const text = await response.text();
    let data = null;
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
    throw new Error(detailOf(data, response.status));
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename || `project-${id}.zip`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

// --- AI (all calls land on the local Ollama model) -------------------------

export function autofill(token, readme_text) {
  return request("/ai/autofill", { method: "POST", body: { readme_text }, token });
}

// Pass { project_id } to cache the review on the row, or { listing } before the first save.
export function reviewListing(token, payload) {
  return request("/ai/review", { method: "POST", body: payload, token });
}

export function askProject(id, question) {
  return request(`/projects/${id}/ask`, { method: "POST", body: { question } });
}

// --- orders (mock provider) ------------------------------------------------

export function createOrder(token, projectId) {
  return request("/orders", { method: "POST", body: { project_id: projectId }, token });
}

export function confirmOrder(token, orderId) {
  return request(`/orders/${orderId}/confirm`, { method: "POST", token });
}

export function myOrders(token) {
  return request("/orders/me", { token });
}
