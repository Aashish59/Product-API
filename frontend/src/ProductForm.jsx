
import { useEffect, useState } from "react";

const initial = (product) => ({
  sku: product?.sku ?? "",
  name: product?.name ?? "",
  price_minor: String(product?.price_minor ?? 1000),
  stock: String(product?.stock ?? 0),
});

export default function ProductForm({
  product,
  busy,
  onSave,
  onCancel,
}) {
  const [values, setValues] = useState(() => initial(product));

  // Update form fields whenever the selected product changes.
  useEffect(() => {
    setValues(initial(product));
  }, [product]);

  function change(event) {
    const { name, value } = event.target;

    setValues((old) => ({
      ...old,
      [name]: value,
    }));
  }

  async function submit(event) {
    event.preventDefault();

    const ok = await onSave({
      ...(product ? { id: product.id } : {}),
      ...values,
      name: values.name.trim(),
      price_minor: Number(values.price_minor),
      stock: Number(values.stock),
    });

    if (ok && !product) {
      setValues(initial(null));
    }
  }

  return (
    <form aria-label="Product form" onSubmit={submit}>
      <h2>{product ? "Edit product" : "Create product"}</h2>

      <fieldset disabled={busy}>
        <label>
          SKU
          <input
            name="sku"
            value={values.sku}
            onChange={change}
            required
            pattern="[A-Z0-9\-]{3,24}"
            readOnly={Boolean(product)}
          />
        </label>

        <label>
          Name
          <input
            name="name"
            value={values.name}
            onChange={change}
            required
            minLength={3}
            maxLength={80}
          />
        </label>

        <label>
          Price (minor units)
          <input
            type="number"
            name="price_minor"
            value={values.price_minor}
            onChange={change}
            required
            min={1}
            max={2000000000}
            step={1}
          />
        </label>

        <label>
          Stock
          <input
            type="number"
            name="stock"
            value={values.stock}
            onChange={change}
            required
            min={0}
            max={1000000}
            step={1}
          />
        </label>

        <button type="submit" disabled={busy}>
          {busy
            ? "Saving..."
            : product
              ? "Save changes"
              : "Create product"}
        </button>

        {product && (
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
          >
            Cancel edit
          </button>
        )}
      </fieldset>
    </form>
  );
}
