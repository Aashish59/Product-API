
import { useEffect, useReducer, useState } from "react";
import { checkout } from "./api.js";
import {
  CART_KEY,
  PENDING_KEY,
  cartReducer,
  loadCart,
  loadPending
} from "./cart.js";

export default function CartPanel({ products, onComplete }) {
  const [cart, dispatch] = useReducer(cartReducer, undefined, loadCart);
  const [pending, setPending] = useState(loadPending);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [storageError, setStorageError] = useState("");
  const [receipt, setReceipt] = useState(null);

  useEffect(() => {
    try {
      localStorage.setItem(CART_KEY, JSON.stringify(cart));
    } catch {
      setStorageError("Cart cannot be saved in this browser.");
    }
  }, [cart]);

  async function submit() {
    if (busy || (!pending && cart.length === 0)) return;

    setBusy(true);
    setError("");
    setReceipt(null);

    let result;

    try {
      const body = pending || {
        request_id: crypto.randomUUID(),
        items: cart.map((line) => ({
          product_id: line.id,
          quantity: line.quantity,
        })),
      };

      // Save before sending: a reload can recover an uncertain result.
      sessionStorage.setItem(PENDING_KEY, JSON.stringify(body));
      setPending(body);

      result = await checkout(body);
    } catch (problem) {
      // 4xx from our API is definitive; network/5xx is uncertain.
      if (problem.status >= 400 && problem.status < 500) {
        sessionStorage.removeItem(PENDING_KEY);
        setPending(null);
      }

      setError(problem.message);
      setBusy(false);
      return;
    }

    // If cleanup fails, leave pending intact: replay remains safe.
    try {
      localStorage.setItem(CART_KEY, "[]");
      sessionStorage.removeItem(PENDING_KEY);
      setPending(null);
      dispatch({ type: "clear" });
      setReceipt(result);
      onComplete();
    } catch {
      setError("Order saved. Keep this tab; retry to recover its receipt.");
    } finally {
      setBusy(false);
    }
  }

  const locked = busy || Boolean(pending);

  const estimate = cart.reduce(
    (sum, line) => sum + line.price_minor * line.quantity,
    0
  );

  return (
    <section aria-label="Shopping cart">
      <h2>Shopping cart - mock checkout</h2>
      <p>One currency; amounts are integer minor units. No payment.</p>
      <p>Choose from the current catalog page:</p>

      {products.map((p) => (
        <button
          key={p.id}
          disabled={locked || p.stock === 0 || cart.length >= 20}
          onClick={() => dispatch({ type: "add", product: p })}
        >
          Add {p.name}
        </button>
      ))}

      <p>Up to 20 products; quantities 1-1000. Server checks actual stock.</p>

      {cart.length === 0 && <p>Your cart is empty.</p>}

      {cart.map((line) => (
        <div key={line.id}>
          <span>
            {line.name} - estimate {line.price_minor} each
          </span>

          <label>
            Quantity for {line.name}
            <input
              type="number"
              min="1"
              max="1000"
              step="1"
              value={line.quantity}
              disabled={locked}
              onChange={(e) =>
                dispatch({
                  type: "quantity",
                  id: line.id,
                  quantity: Number(e.target.value)
                })
              }
            />
          </label>

          <button
            disabled={locked}
            onClick={() =>
              dispatch({
                type: "remove",
                id: line.id,
              })
            }
          >
            Remove {line.name}
          </button>
        </div>
      ))}

      <p>Estimated total: {estimate} minor units.</p>
      <p>The server uses current prices and returns the final total.</p>

      <button
        disabled={busy || (!pending && cart.length === 0)}
        onClick={submit}
      >
        {busy
          ? "Checking out..."
          : pending
          ? "Retry same checkout"
          : "Mock checkout"}
      </button>

      {pending && (
        <p role="status">
          Checkout {pending.request_id} is unresolved.
          Cart editing is locked. Retry the same request.
        </p>
      )}

      {error && <p role="alert">{error}</p>}

      {storageError && <p role="alert">{storageError}</p>}

      {receipt && (
        <div role="status">
          <h3>Order saved</h3>
          <p>Request: {receipt.request_id}</p>
          <p>Final total: {receipt.total_minor} minor units</p>

          <ul>
            {receipt.items.map((line) => (
              <li key={line.product_id}>
                {line.name}: {line.quantity} x {line.unit_price_minor}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
