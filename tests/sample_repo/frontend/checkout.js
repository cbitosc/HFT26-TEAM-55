/**
 * Client-side checkout UI orchestration and payment button binding.
 */

import { getAuthToken } from "./auth.js";

export async function initiateCheckout(sessionId, stripeToken) {
    const authToken = getAuthToken();
    if (!authToken) {
        window.location.href = "/login";
        return;
    }

    const payload = {
        session_id: sessionId,
        customer_token: stripeToken,
    };

    const res = await fetch("/api/checkout", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${authToken}`,
        },
        body: JSON.stringify(payload),
    });

    const result = await res.json();
    if (result.status === "ok") {
        alert("Payment successful! Receipt sent to email.");
    } else {
        alert("Payment failed: " + result.message);
    }
}
