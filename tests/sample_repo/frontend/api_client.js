/**
 * Centralized fetch API wrapper with automatic Bearer token injection.
 */

import { getAuthToken, clearAuthSession } from "./auth.js";

export async function apiRequest(endpoint, options = {}) {
    const headers = options.headers || {};
    const token = getAuthToken();

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    if (!headers["Content-Type"] && !(options.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
    }

    const response = await fetch(endpoint, {
        ...options,
        headers,
    });

    if (response.status === 401) {
        clearAuthSession();
        window.location.href = "/login";
        return null;
    }

    return response.json();
}
