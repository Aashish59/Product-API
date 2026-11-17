
import { useEffect, useState } from "react";
import * as api from "./api.js";
import ProductForm from "./ProductForm.jsx";

const LIMIT = 5;

export default function App() {
  const [filters, setFilters] = useState({
    q: "",
    sort: "name",
    offset: 0,
  });

  const [draft, setDraft] = useState("");
  const [revision, setRevision] = useState(0);

  const [page, setPage] = useState({
    items: [],
    total: 0,
    status: "loading",
    error: "",
  });

  const [editing, setEditing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);

  const refresh = () => setRevision((value) => value + 1);

  useEffect(() => {
    const controller = new AbortController();

    setPage((old) => ({
      ...old,
      status: "loading",
      error: "",
    }));

    api
      .getProducts(
        { ...filters, limit: LIMIT },
        controller.signal
      )
      .then((data) => {
        if (controller.signal.aborted) return;

        if (filters.offset > 0 && filters.offset >= data.total) {
          const offset = Math.max(
            0,
            Math.floor((data.total - 1) / LIMIT) * LIMIT
          );

          setFilters((old) => ({ ...old, offset }));
          return;
        }

        setPage({
          ...data,
          status: "ready",
          error: "",
        });
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setPage((old) => ({
            ...old,
            status: "error",
            error: error.message,
          }));
        }
      });

    return () => controller.abort();
  }, [filters, revision]);

  async function save(data) {
    setBusy(true);
    setNotice(null);

    try {
      if (editing) {
        const { name, price_minor, stock } = data;

        await api.updateProduct(editing.id, {
          name,
          price_minor,
          stock,
        });
      } else {
        await api.createProduct(data);
      }

      setEditing(null);
      refresh();

      setNotice({
        kind: "success",
        text: "Product saved.",
      });

      return true;
    } catch (error) {
      setNotice({
        kind: "error",
        text: error.message,
      });

      return false;
    } finally {
      setBusy(false);
    }
  }

  async function remove(product) {
    if (!window.confirm(`Delete ${product.name}?`)) return;

    setBusy(true);
    setNotice(null);

    try {
      await api.deleteProduct(product.id);

      if (editing?.id === product.id) {
        setEditing(null);
      }

      refresh();

      setNotice({
        kind: "success",
        text: "Product deleted.",
      });
    } catch (error) {
      setNotice({
        kind: "error",
        text: error.message,
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <header>
        <h1>Product workbench</h1>
        <p>
          React + FastAPI. Prices use one chosen currency's minor units.
        </p>
      </header>

      {notice && (
        <p role={notice.kind === "error" ? "alert" : "status"}>
          {notice.text}
        </p>
      )}

      <ProductForm
        key={editing?.id ?? "new"}
        product={editing}
        busy={busy}
        onSave={save}
        onCancel={() => setEditing(null)}
      />

      <section aria-label="Catalog">
        <h2>Catalog</h2>

        <form
          aria-label="Search form"
          onSubmit={(event) => {
            event.preventDefault();

            setFilters((old) => ({
              ...old,
              q: draft.trim(),
              offset: 0,
            }));
          }}
        >
          <label>
            Search name
            <input
              value={draft}
              maxLength={80}
              onChange={(event) => setDraft(event.target.value)}
            />
          </label>

          <button>Search</button>
        </form>

        <label>
          Sort
          <select
            value={filters.sort}
            onChange={(event) =>
              setFilters((old) => ({
                ...old,
                sort: event.target.value,
                offset: 0,
              }))
            }
          >
            <option value="name">Name</option>
            <option value="price_asc">Price ascending</option>
            <option value="price_desc">Price descending</option>
          </select>
        </label>

        {page.status === "loading" && (
          <p role="status">Loading products...</p>
        )}

        {page.status === "error" && (
          <div role="alert">
            <p>{page.error}</p>
            <button onClick={refresh}>Retry</button>
          </div>
        )}

        {page.status === "ready" && (
          <>
            {page.items.length === 0 ? (
              <p>No products found.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    {[
                      "SKU",
                      "Name",
                      "Price",
                      "Stock",
                      "Actions",
                    ].map((label) => (
                      <th key={label} scope="col">
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  {page.items.map((product) => (
                    <tr key={product.id}>
                      <td>{product.sku}</td>
                      <td>{product.name}</td>
                      <td>{product.price_minor}</td>
                      <td>{product.stock}</td>

                      <td>
                        <button
                          disabled={busy}
                          onClick={() => setEditing(product)}
                        >
                          Edit
                        </button>

                        <button
                          disabled={busy}
                          onClick={() => remove(product)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            <p>
              Showing {Math.min(filters.offset + 1, page.total)}-
              {Math.min(
                filters.offset + page.items.length,
                page.total
              )}{" "}
              of {page.total}
            </p>

            <button
              disabled={busy || filters.offset === 0}
              onClick={() =>
                setFilters((old) => ({
                  ...old,
                  offset: Math.max(0, old.offset - LIMIT),
                }))
              }
            >
              Previous
            </button>

            <button
              disabled={
                busy || filters.offset + LIMIT >= page.total
              }
              onClick={() =>
                setFilters((old) => ({
                  ...old,
                  offset: old.offset + LIMIT,
                }))
              }
            >
              Next
            </button>
          </>
        )}
      </section>
    </main>
  );
}
