/**
 * Client-side authentication event handlers and JWT token storage.
 */

const TOKEN_STORAGE_KEY = "shopstream_auth_token";

export function saveAuthToken(token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function getAuthToken() {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function clearAuthSession() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
}

export async function handleLoginSubmit(event, emailInput, passwordInput) {
    event.preventDefault();
    const payload = {
        email: emailInput.value.trim(),
        password: passwordInput.value,
    };

    const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (data.status === "ok" && data.token) {
        saveAuthToken(data.token);
        window.location.href = "/dashboard";
    } else {
        alert(data.message || "Login failed");
    }
}
