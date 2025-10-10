const form = document.getElementById("redeemForm");
const formWrapper = document.getElementById("formWrapper");
const spinner = document.getElementById("spinner");
const email = document.getElementById("emailInput");
const voucher = document.getElementById("voucherInput");
const result = document.getElementById("result");

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
