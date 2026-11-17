
import {
  afterEach,
  beforeEach,
  expect,
  test,
  vi,
} from "vitest";

import * as api from "./api.js";

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

test("204 DELETE succeeds without parsing a JSON body", async () => {
  fetch.mockResolvedValue(new Response(null, { status: 204 }));

  await expect(api.deleteProduct(7)).resolves.toBeNull();

  expect(fetch).toHaveBeenCalledWith(
    "/api/products/7",
    expect.objectContaining({ method: "DELETE" })
  );
});

test("Pydantic field errors become a readable message", async () => {
  fetch.mockResolvedValue(
    new Response(
      JSON.stringify({
        detail: [
          {
            loc: ["body", "stock"],
            msg: "Must be nonnegative",
          },
        ],
      }),
      { status: 422 }
    )
  );

  await expect(api.createProduct({})).rejects.toThrow(
    "stock: Must be nonnegative"
  );
});

test("GET query values are encoded as data", async () => {
  fetch.mockResolvedValue(
    new Response('{"items":[],"total":0}')
  );

  await api.getProducts({ q: "AI & SQL", limit: 5 });

  const url = new URL(
    fetch.mock.calls[0][0],
    "http://example.test"
  );

  expect(url.pathname).toBe("/api/products");
  expect(url.searchParams.get("q")).toBe("AI & SQL");
});

test("network failures explain what to check", async () => {
  fetch.mockRejectedValue(new TypeError("Network failed"));

  await expect(api.getProducts({})).rejects.toThrow(
    "Cannot reach API"
  );
});

test("non-JSON HTTP failures do not expose an HTML page as data", async () => {
  fetch.mockResolvedValue(
    new Response("<h1>Proxy failed</h1>", { status: 502 })
  );

  await expect(api.getProducts({})).rejects.toMatchObject({
    status: 502,
  });
});

test("cancellation remains AbortError", async () => {
  const error = new DOMException("Cancelled", "AbortError");

  fetch.mockRejectedValue(error);

  await expect(api.getProducts({})).rejects.toBe(error);
});
