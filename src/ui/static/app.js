// The questionnaire: upload the dataset, then request the model with its link.
(() => {
  "use strict";

  const DATA_URL = "/v1/data";
  const MODEL_URL = "/v1/model";

  const form = document.getElementById("form");
  const email = document.getElementById("email");
  const product = document.getElementById("product");
  const input = document.getElementById("file");
  const dropzone = document.getElementById("dropzone");
  const title = document.getElementById("dropzone-title");
  const hint = document.getElementById("dropzone-hint");
  const submit = document.getElementById("submit");
  const progress = document.getElementById("progress");
  const progressBar = document.getElementById("progress-bar");
  const statusLine = document.getElementById("status");
  const error = document.getElementById("error");
  const result = document.getElementById("result");
  const resultText = document.getElementById("result-text");

  const formatSize = (bytes) => {
    const units = ["B", "KB", "MB", "GB"];
    let size = bytes;
    let unit = 0;
    while (size >= 1024 && unit < units.length - 1) {
      size /= 1024;
      unit += 1;
    }
    return `${size.toFixed(size < 10 && unit > 0 ? 1 : 0)} ${units[unit]}`;
  };

  const show = (element, text) => {
    element.textContent = text;
    element.hidden = false;
  };

  // FastAPI returns a string detail, or a list of validation errors.
  const detailOf = (payload, fallback) => {
    const detail = payload?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length) {
      return detail.map((item) => item.msg).join(", ");
    }
    return fallback;
  };

  const resetFile = () => {
    input.value = "";
    dropzone.classList.remove("has-file");
    title.textContent = "Drop your .zip here";
    hint.textContent = "or click to browse";
  };

  const selectFile = (file) => {
    error.hidden = true;
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".zip")) {
      resetFile();
      show(error, "Only .zip files are accepted.");
      return;
    }
    dropzone.classList.add("has-file");
    title.textContent = file.name;
    hint.textContent = formatSize(file.size);
  };

  input.addEventListener("change", () => selectFile(input.files[0]));

  ["dragenter", "dragover"].forEach((event) =>
    dropzone.addEventListener(event, (e) => {
      e.preventDefault();
      dropzone.classList.add("is-dragging");
    }),
  );

  ["dragleave", "drop"].forEach((event) =>
    dropzone.addEventListener(event, (e) => {
      e.preventDefault();
      dropzone.classList.remove("is-dragging");
    }),
  );

  dropzone.addEventListener("drop", (e) => {
    if (!e.dataTransfer.files.length) return;
    input.files = e.dataTransfer.files;
    selectFile(e.dataTransfer.files[0]);
  });

  // XHR rather than fetch: it reports upload progress, and datasets are big.
  const uploadDataset = (file) =>
    new Promise((resolve, reject) => {
      const body = new FormData();
      body.append("file", file);

      const request = new XMLHttpRequest();
      request.open("POST", DATA_URL);
      request.responseType = "json";

      request.upload.addEventListener("progress", (event) => {
        if (!event.lengthComputable) return;
        progressBar.style.width = `${(event.loaded / event.total) * 100}%`;
      });
      request.addEventListener("load", () => {
        if (request.status === 201) resolve(request.response.link);
        else reject(new Error(detailOf(request.response, "Could not upload the dataset.")));
      });
      request.addEventListener("error", () =>
        reject(new Error("Upload failed, please check your connection.")),
      );

      request.send(body);
    });

  const requestModel = async (payload) => {
    const response = await fetch(MODEL_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(detailOf(body, "Could not submit your request."));
    }
    return body;
  };

  const setBusy = (busy, label) => {
    submit.disabled = busy;
    submit.textContent = busy ? label : "Submit request";
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.hidden = true;
    result.hidden = true;

    const file = input.files[0];
    const size = form.querySelector("input[name='model_size']:checked");
    if (!email.value.trim() || !email.checkValidity()) {
      show(error, "Please enter a valid email address.");
      return;
    }
    if (!file) {
      show(error, "Please choose a .zip dataset.");
      return;
    }

    try {
      setBusy(true, "Uploading…");
      progressBar.style.width = "0";
      progress.hidden = false;
      show(statusLine, "Uploading your dataset…");

      const link = await uploadDataset(file);

      show(statusLine, "Submitting your request…");
      const submission = await requestModel({
        email: email.value.trim(),
        upload_link: link,
        model_size: size.value,
        product_id: Number(product.value),
      });

      form.hidden = true;
      progress.hidden = true;
      statusLine.hidden = true;
      resultText.textContent =
        `Request #${submission.id} is queued. We will email the result to ` +
        `${email.value.trim()} as soon as it is ready.`;
      result.hidden = false;
    } catch (failure) {
      progress.hidden = true;
      statusLine.hidden = true;
      show(error, failure.message);
    } finally {
      setBusy(false);
    }
  });
})();
