const form = document.getElementById("redeemForm");
const formWrapper = document.getElementById("formWrapper");
const spinner = document.getElementById("spinner");
const email = document.getElementById("emailInput");
const voucher = document.getElementById("voucherInput");
const result = document.getElementById("result");

async function updateActiveUsers() {
  try {
    const response = await fetch("http://localhost:5000/active_users");
    if (!response.ok) throw new Error("Failed to get user count");

    const data = await response.json();
    const current = data.active ?? 0;
    const max = data.max ?? 10;

    // Update the text content
    const activeUsersSpan = document.getElementById("activeUsers");
    activeUsersSpan.textContent = `Active Users: ${current}/${max}`;

    // Optional: color indicator (red when full)
    if (current >= max) {
      activeUsersSpan.style.color = "red"; // full
    } else if (current >= 5) {
      activeUsersSpan.style.color = "orange"; // less than or equal to 5
    } else {
      activeUsersSpan.style.color = "limegreen"; // between 6–9
    }
  } catch (err) {
    const activeUsersSpan = document.getElementById("activeUsers");
    activeUsersSpan.textContent = "Active Users: N/A";
    console.error("Error updating user count:", err);
  }
}

// Run once when the page loads
window.addEventListener("DOMContentLoaded", updateActiveUsers);

// Update every 5 seconds
setInterval(updateActiveUsers, 5000);

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const code = voucher.value.trim();

  if (!code) {
    result.textContent = "Please enter a voucher code.";
    return;
  }

  // --- Show spinner, hide form content ---
  formWrapper.hidden = true;
  spinner.hidden = false;
  result.textContent = "";

  try {
    const response = await fetch("http://localhost:5000/api/redeem", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ voucher: code, email: email.value.trim() }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Failed to redeem voucher.");
    }

    // Handle response
    if (data.message && data.message.includes("Enjoy your extra 5 minutes")) {
      result.textContent = data.message;
      email.value = "";
      voucher.value = "";
    } else {
      window.location.href = "success.html";
    }
  } catch (error) {
    result.textContent = error.message || "An error occurred.";
  } finally {
    // --- Hide spinner, show form content again ---
    spinner.hidden = true;
    formWrapper.hidden = false;
  }
});
