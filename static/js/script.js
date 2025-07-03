document.addEventListener('DOMContentLoaded', () => {
  const promptInput = document.getElementById('prompt-input');
  const styleSelect = document.getElementById('style-select');
  const generateBtn = document.getElementById('generate-btn');
  const imageResult = document.getElementById('image-result');
  const generatedImage = document.getElementById('generated-image');
  const downloadBtn = document.getElementById('download-btn');
  const variationBtn = document.getElementById('new-variation-btn');
  const favoriteBtn = document.getElementById('favorite-btn');
  const historyGallery = document.getElementById('history-gallery');
  const favoritesGallery = document.getElementById('favorites-gallery');
  const loadingOverlay = document.getElementById('loading-overlay');
  const darkToggle = document.getElementById('dark-toggle');

  darkToggle?.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('dark-mode', document.body.classList.contains('dark-mode'));
  });

  if (localStorage.getItem('dark-mode') === 'true') {
    document.body.classList.add('dark-mode');
  }

  loadHistory();
  loadFavorites();

  generateBtn.addEventListener('click', generateImage);

  promptInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      generateImage();
    }
  });

  variationBtn?.addEventListener('click', generateImage);

  async function generateImage() {
    const prompt = promptInput.value.trim();
    const style = styleSelect.value;

    if (!prompt) return showAlert("❗ Please enter a prompt.");

    const enhancedPrompt = enhancePrompt(prompt);
    loadingOverlay.classList.add("active");

    try {
      const formData = new FormData();
      formData.append("prompt", enhancedPrompt);
      formData.append("style", style);

      const res = await fetch("/generate", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (data.filename) {
        const imageUrl = `/outputs/${data.filename}`;
        showGeneratedImage(imageUrl, data.prompt, data.style, data.filename);
        await loadHistory();
        showStatus("✅ Image generated successfully!");
      } else {
        throw new Error("Filename not returned from server.");
      }

    } catch (err) {
      console.error("❌ Generation error:", err);
      showAlert("❌ Failed to generate image.");
    } finally {
      loadingOverlay.classList.remove("active");
    }
  }

  function enhancePrompt(prompt) {
    return prompt.split(" ").length < 4
      ? `${prompt}, ultra-detailed, masterpiece, cinematic lighting, 4K, trending on ArtStation`
      : prompt;
  }

  function showGeneratedImage(imageUrl, prompt, style, filename) {
    generatedImage.src = imageUrl;
    generatedImage.alt = prompt;
    imageResult.style.display = "block";
    downloadBtn.href = imageUrl;
    downloadBtn.download = `generated-${Date.now()}.png`;
    favoriteBtn.setAttribute("data-filename", filename);
  }

  favoriteBtn?.addEventListener("click", async () => {
    const filename = favoriteBtn.getAttribute("data-filename");
    if (!filename) return;

    try {
      const res = await fetch("/favorite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename }),
      });

      const result = await res.json();
      if (result.status === "success") {
        showStatus("⭐ Image marked as favorite");
        loadFavorites();
      } else {
        showAlert("❌ Couldn't mark favorite");
      }
    } catch (err) {
      console.error("Favorite error:", err);
      showAlert("❌ Failed to favorite image");
    }
  });

  async function loadHistory() {
    try {
      const res = await fetch("/history");
      const history = await res.json();

      if (!Array.isArray(history) || history.length === 0) {
        historyGallery.innerHTML = `<p class="empty-history">📭 No image history found</p>`;
        return;
      }

      historyGallery.innerHTML = history.map(item => `
        <div class="history-item">
          <img src="/outputs/${item.filename}" alt="${sanitize(item.prompt)}">
          <div class="history-info">
            <h4>${sanitize(item.prompt)}</h4>
            <p>${capitalize(item.style)} | ${item.timestamp}</p>
            <button class="delete-btn" data-filename="${item.filename}">🗑️ Delete</button>
          </div>
        </div>
      `).join("");

      attachDeleteEvents();

    } catch (err) {
      console.error("❌ Error loading history:", err);
      historyGallery.innerHTML = `<p class="error">❌ Failed to load history</p>`;
    }
  }

  async function loadFavorites() {
    try {
      const res = await fetch("/favorites");
      const filenames = await res.json();

      if (!Array.isArray(filenames) || filenames.length === 0) {
        favoritesGallery.innerHTML = `<p class="empty-history">⭐ No favorite images yet</p>`;
        return;
      }

      // Fetch prompt + style info from history for each favorite image
      const historyRes = await fetch("/history");
      const history = await historyRes.json();

      const matched = history.filter(item => filenames.includes(item.filename));

      favoritesGallery.innerHTML = matched.map(item => `
        <div class="history-item">
          <img src="/outputs/${item.filename}" alt="${sanitize(item.prompt)}">
          <div class="history-info">
            <h4>${sanitize(item.prompt)}</h4>
            <p>${capitalize(item.style)} | ${item.timestamp}</p>
          </div>
        </div>
      `).join("");

    } catch (err) {
      console.error("❌ Error loading favorites:", err);
      favoritesGallery.innerHTML = `<p class="error">❌ Failed to load favorites</p>`;
    }
  }

  function attachDeleteEvents() {
    document.querySelectorAll(".delete-btn").forEach(btn => {
      btn.addEventListener("click", async function () {
        const filename = this.getAttribute("data-filename");
        if (!confirm(`Are you sure you want to delete "${filename}"?`)) return;

        try {
          const res = await fetch("/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ filename }),
          });

          const result = await res.json();
          if (result.status === "success") {
            showAlert(`🗑️ Deleted: ${result.deleted}`);
            await loadHistory();
            await loadFavorites();
          }
        } catch (err) {
          console.error("❌ Delete failed:", err);
          showAlert("❌ Couldn't delete image.");
        }
      });
    });
  }

  function showAlert(message) {
    const alert = document.createElement("div");
    alert.className = "alert-message";
    alert.textContent = message;

    Object.assign(alert.style, {
      position: "fixed",
      top: "20px",
      left: "50%",
      transform: "translateX(-50%)",
      backgroundColor: "#e74c3c",
      color: "#fff",
      padding: "10px 20px",
      borderRadius: "6px",
      zIndex: 9999,
      boxShadow: "0 4px 10px rgba(0,0,0,0.2)",
    });

    document.body.appendChild(alert);
    setTimeout(() => alert.remove(), 3000);
  }

  function showStatus(message) {
    const alertBox = document.getElementById("status-alert");
    alertBox.textContent = message;
    alertBox.style.display = "block";
    alertBox.style.backgroundColor = "#28a745";
    alertBox.style.color = "#fff";
    alertBox.style.padding = "10px 20px";
    alertBox.style.borderRadius = "8px";
    alertBox.style.position = "fixed";
    alertBox.style.top = "20px";
    alertBox.style.left = "50%";
    alertBox.style.transform = "translateX(-50%)";
    alertBox.style.zIndex = 9999;
    alertBox.style.boxShadow = "0 4px 10px rgba(0, 0, 0, 0.2)";

    setTimeout(() => {
      alertBox.style.display = "none";
    }, 3000);
  }

  const capitalize = str => str ? str.charAt(0).toUpperCase() + str.slice(1) : '';
  const sanitize = str => {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  };
});
