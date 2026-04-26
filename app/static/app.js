const submitBtn = document.getElementById("submitBtn");
const numbersInput = document.getElementById("numbersInput");
const jobIdEl = document.getElementById("jobId");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");

let pollTimer = null;

function parseNumbers(raw) {
  return raw
    .split(",")
    .map((x) => x.trim())
    .filter((x) => x.length > 0)
    .map((x) => Number(x))
    .filter((x) => Number.isFinite(x));
}

async function pollJob(jobId) {
  const res = await fetch(`/jobs/${jobId}`);
  const data = await res.json();

  statusEl.textContent = data.status;

  if (data.status === "SUCCESS" || data.status === "FAILURE") {
    clearInterval(pollTimer);
    pollTimer = null;
    resultEl.textContent = JSON.stringify(data, null, 2);
  }
}

submitBtn.addEventListener("click", async () => {
  const numbers = parseNumbers(numbersInput.value);

  if (numbers.length === 0) {
    alert("Please provide at least one valid number.");
    return;
  }

  resultEl.textContent = "";
  statusEl.textContent = "SUBMITTING...";

  const res = await fetch("/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ numbers }),
  });

  const data = await res.json();
  const jobId = data.job_id;
  jobIdEl.textContent = jobId;

  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(() => pollJob(jobId), 1500);
  pollJob(jobId);
});
