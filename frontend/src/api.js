
export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function errorMessage(detail, status) {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map(
        (issue) =>
          `${issue.loc?.slice(1).join(".") || "request"}: ${issue.msg}`
      )
      .join("; ");
  }

  return `Request failed (${status}). Check the API response.`;
}

async function request(path, options = {}) {
  let response;

  try {
    response = await fetch(`/api${path}`, {
      ...options,
      headers: {
        Accept: "application/json",
        ...(options.body
          ? { "Content-Type": "application/json" }
          : {}),
        ...options.headers,
      },
    });
  } catch (error) {
    if (error.name === "AbortError") {
      throw error;
    }

    throw new ApiError(
      "Cannot reach API. Check the servers and proxy."
    );
  }

  if (response.status === 204) {
    return null;
  }

  const text = await response.text();

  let data;

  try {
    data = JSON.parse(text);
  } catch {
    data = null;
  }

  if (!response.ok) {
    throw new ApiError(
      errorMessage(data?.detail, response.status),
      response.status
    );
  }

  if (data === null) {
    throw new ApiError("API returned invalid JSON.");
  }

  return data;
}

export function getProducts(params, signal) {
  return request(
    `/products?${new URLSearchParams(params)}`,
    { signal }
  );
}

export function createProduct(data) {
  return request("/products", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateProduct(id, changes) {
  return request(`/products/${id}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

export function deleteProduct(id) {
  return request(`/products/${id}`, {
    method: "DELETE",
  });
}
