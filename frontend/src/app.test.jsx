
import { beforeEach, expect, test, vi } from "vitest";
import {
  act,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import * as api from "./api.js";
import App from "./app.jsx";

vi.mock("./api.js", () => ({
  getProducts: vi.fn(),
  createProduct: vi.fn(),
  updateProduct: vi.fn(),
  deleteProduct: vi.fn(),
}));

const product = {
  id: 1,
  sku: "BOOK-001",
  name: "Python Book",
  price_minor: 2500,
  stock: 3,
};

const page = (items = []) => ({
  items,
  total: items.length,
  offset: 0,
  limit: 5,
});

beforeEach(() => {
  vi.resetAllMocks();
  api.getProducts.mockResolvedValue(page());
});

test("renders the empty state after loading", async () => {
  render(<App />);

  expect(
    await screen.findByText("No products found.")
  ).toBeVisible();
});

test("submits numeric values and refreshes after creating", async () => {
  api.createProduct.mockResolvedValue(product);

  const user = userEvent.setup();

  render(<App />);

  await screen.findByText("No products found.");

  await user.type(
    screen.getByLabelText("SKU"),
    "BOOK-001"
  );

  await user.type(
    screen.getByLabelText("Name"),
    "Python Book"
  );

  const price = screen.getByLabelText(
    "Price (minor units)"
  );

  await user.clear(price);
  await user.type(price, "2500");

  await user.click(
    screen.getByRole("button", { name: "Create product" })
  );

  await waitFor(() =>
    expect(api.createProduct).toHaveBeenCalledWith({
      sku: "BOOK-001",
      name: "Python Book",
      price_minor: 2500,
      stock: 0,
    })
  );

  expect(
    await screen.findByText("Product saved.")
  ).toBeVisible();

  expect(screen.getByLabelText("SKU")).toHaveValue("");

  await waitFor(() =>
    expect(api.getProducts).toHaveBeenCalledTimes(2)
  );
});

test("editing sends a PATCH shape without immutable SKU", async () => {
  api.getProducts.mockResolvedValue(page([product]));

  api.updateProduct.mockResolvedValue({
    ...product,
    stock: 0,
  });

  const user = userEvent.setup();

  render(<App />);

  await screen.findByText("BOOK-001");

  await user.click(
    screen.getByRole("button", { name: "Edit" })
  );

  expect(screen.getByLabelText("SKU")).toHaveAttribute(
    "readonly"
  );

  const stock = screen.getByLabelText("Stock");

  await user.clear(stock);
  await user.type(stock, "0");

  await user.click(
    screen.getByRole("button", { name: "Save changes" })
  );

  await waitFor(() =>
    expect(api.updateProduct).toHaveBeenCalledWith(1, {
      name: "Python Book",
      price_minor: 2500,
      stock: 0,
    })
  );
});

test("a conflict shows feedback and preserves the form", async () => {
  api.createProduct.mockRejectedValue(
    new Error("SKU already exists")
  );

  const user = userEvent.setup();

  render(<App />);

  await user.type(
    screen.getByLabelText("SKU"),
    "BOOK-001"
  );

  await user.type(
    screen.getByLabelText("Name"),
    "Another Book"
  );

  await user.click(
    screen.getByRole("button", { name: "Create product" })
  );

  expect(
    await screen.findByRole("alert")
  ).toHaveTextContent("SKU already exists");

  expect(screen.getByLabelText("SKU")).toHaveValue(
    "BOOK-001"
  );
});

test("the catalog retries after a request failure", async () => {
  api.getProducts.mockRejectedValueOnce(
    new Error("API offline")
  );

  const user = userEvent.setup();

  render(<App />);

  expect(
    await screen.findByRole("alert")
  ).toHaveTextContent("API offline");

  await user.click(
    screen.getByRole("button", { name: "Retry" })
  );

  expect(
    await screen.findByText("No products found.")
  ).toBeVisible();
});

test("a cancelled delete does not call the API", async () => {
  api.getProducts.mockResolvedValue(page([product]));

  vi.spyOn(window, "confirm").mockReturnValue(false);

  const user = userEvent.setup();

  render(<App />);

  await screen.findByText("BOOK-001");

  await user.click(
    screen.getByRole("button", { name: "Delete" })
  );

  expect(api.deleteProduct).not.toHaveBeenCalled();
});

test("an older search response cannot overwrite newer results", async () => {
  let resolveOld;

  api.getProducts
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveOld = resolve;
        })
    )
    .mockResolvedValue(
      page([{ ...product, name: "Fresh result" }])
    );

  const user = userEvent.setup();

  render(<App />);

  await waitFor(() =>
    expect(api.getProducts).toHaveBeenCalledTimes(1)
  );

  await user.type(
    screen.getByLabelText("Search name"),
    "Fresh"
  );

  await user.click(
    screen.getByRole("button", { name: "Search" })
  );

  await screen.findByText("Fresh result");

  await act(async () => {
    resolveOld(
      page([{ ...product, name: "Stale result" }])
    );
  });

  expect(
    screen.queryByText("Stale result")
  ).not.toBeInTheDocument();

  expect(api.getProducts.mock.calls[0][1].aborted).toBe(
    true
  );
});

test("deleting the only item on the last page returns to a valid page", async () => {
  let rows = Array.from({ length: 6 }, (_, i) => ({
    ...product,
    id: i + 1,
    sku: `BOOK-${i + 1}`,
  }));

  api.getProducts.mockImplementation(
    ({ offset, limit }) =>
      Promise.resolve({
        items: rows.slice(offset, offset + limit),
        total: rows.length,
        offset,
        limit,
      })
  );

  api.deleteProduct.mockImplementation(async (id) => {
    rows = rows.filter((row) => row.id !== id);
  });

  vi.spyOn(window, "confirm").mockReturnValue(true);

  const user = userEvent.setup();

  render(<App />);

  await screen.findByText("BOOK-1");

  await user.click(
    screen.getByRole("button", { name: "Next" })
  );

  const cell = await screen.findByText("BOOK-6");

  await user.click(
    within(cell.closest("tr")).getByRole("button", {
      name: "Delete",
    })
  );

  expect(await screen.findByText("BOOK-1")).toBeVisible();

  expect(
    screen.queryByText("BOOK-6")
  ).not.toBeInTheDocument();

  expect(
    screen.getByRole("button", { name: "Previous" })
  ).toBeDisabled();
});
