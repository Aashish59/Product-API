
export const CART_KEY = "learning-cv-cart-v1";
export const PENDING_KEY = "learning-cv-checkout-v1";

// Manage cart operations
export function cartReducer(state, action) {

  // Clear the entire cart
  if (action.type === "clear") {
    return [];
  }

  // Remove a product from the cart
  if (action.type === "remove") {
    return state.filter(
      (line) => line.id !== action.id
    );
  }

  // Add a product to the cart
  if (action.type === "add") {
    const p = action.product;

    // Do not add products that are out of stock
    if (p.stock < 1) {
      return state;
    }

    // Check whether the product already exists in the cart
    const found = state.find(
      (line) => line.id === p.id
    );

    // If it exists, increase its quantity
    if (found) {
      return state.map((line) =>
        line.id === p.id
          ? {
              ...line,
              quantity: Math.min(line.quantity + 1, 1000)
            }
          : line
      );
    }

    // Maximum 20 different products in the cart
    if (state.length >= 20) {
      return state;
    }

    // Add a new product to the cart
    return [
      ...state,
      {
        id: p.id,
        name: p.name,
        price_minor: p.price_minor,
        quantity: 1
      }
    ];
  }

  // Update product quantity
  if (
    action.type === "quantity" &&
    Number.isInteger(action.quantity) &&
    action.quantity >= 1 &&
    action.quantity <= 1000
  ) {
    return state.map((line) =>
      line.id === action.id
        ? { ...line, quantity: action.quantity }
        : line
    );
  }

  // Return the existing cart if action is invalid
  return state;
}


// Load cart data from localStorage
export function loadCart() {
  try {
    const data = JSON.parse(
      localStorage.getItem(CART_KEY) || "[]"
    );

    // Check whether cart data is a valid array
    if (!Array.isArray(data) || data.length > 20) {
      return [];
    }

    // Check for duplicate product IDs
    if (
      new Set(data.map((x) => x?.id)).size !== data.length
    ) {
      return [];
    }

    // Validate every product in the cart
    return data.every(
      (x) =>
        x &&
        Number.isInteger(x.id) &&
        x.id > 0 &&
        typeof x.name === "string" &&
        Number.isInteger(x.price_minor) &&
        x.price_minor > 0 &&
        Number.isInteger(x.quantity) &&
        x.quantity >= 1 &&
        x.quantity <= 1000
    )
      ? data
      : [];

  } catch {
    return [];
  }
}


// Load pending checkout data from sessionStorage
export function loadPending() {
  try {
    return JSON.parse(
      sessionStorage.getItem(PENDING_KEY) || "null"
    );
  } catch {
    return null;
  }
}
