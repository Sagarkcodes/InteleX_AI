window.addEventListener("DOMContentLoaded", async () => {
  const instruction = document.getElementById("ai-instruction");
  const readingText = document.getElementById("reading-text");
  const paragraphBox = document.getElementById("paragraph-box");
  const controls = document.getElementById("controls");
  const startBtn = document.getElementById("start-recording");
  const stopBtn = document.getElementById("stop-recording");
  const timerDisplay = document.getElementById("record-timer");
  const statusText = document.getElementById("status-text");
  const agentAvatar = document.querySelector(".agent-avatar");

  let recorder, audioChunks = [], timer, seconds = 0;

  // ✅ Animate avatar glow during speech
  function setSpeakingState(isSpeaking) {
    if (!agentAvatar) return;
    if (isSpeaking) {
      agentAvatar.classList.add("speaking-glow");
    } else {
      agentAvatar.classList.remove("speaking-glow");
    }
  }

  // ✅ Speak text using browser voice (same as video interview)
  function speakOnce(text, onEnd) {
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      utterance.pitch = 1.02;
      const voices = window.speechSynthesis.getVoices();
      if (voices && voices.length)
        utterance.voice = voices.find(v => v.lang && v.lang.includes("en")) || voices[0];

      utterance.onstart = () => setSpeakingState(true);
      utterance.onend = () => {
        setSpeakingState(false);
        if (onEnd) onEnd();
      };

      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn("⚠️ Browser TTS error:", e);
      if (onEnd) onEnd();
    }
  }

  // 🧠 Step 1 — Greeting (instant voice)
  const greetingText =
    "Hello Candidate. Please stay in a calm environment and read the displayed paragraph clearly. You will have one minute to complete your reading.";
  instruction.textContent = greetingText;
  speakOnce(greetingText);

  // 🧩 Step 2 — Load paragraph immediately (FIXED ENDPOINT)
  try {
    const res = await fetch("/next-paragraph");
    const data = await res.json();

    const paragraph =
      data.paragraph ||
      "Artificial Intelligence is transforming the way we interact with technology and data. It enables machines to adapt, reason, and respond intelligently to the world around them.";

    paragraphBox.classList.remove("hidden");
    controls.classList.remove("hidden");
    readingText.textContent = paragraph;
  } catch (err) {
    console.error("❌ Failed to fetch paragraph:", err);
  }

  // 🎙️ Step 3 — Recording controls
  startBtn.addEventListener("click", async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recorder = new MediaRecorder(stream);
    audioChunks = [];

    recorder.ondataavailable = (e) => audioChunks.push(e.data);
    recorder.onstop = async () => {
      const blob = new Blob(audioChunks, { type: "audio/webm" });
      const formData = new FormData();
      formData.append("audio_data", blob, "voice_sample.webm");

      statusText.textContent = "⏳ Uploading your voice for analysis...";
      const res = await fetch("/upload-audio", { method: "POST", body: formData });
      const result = await res.json();

      if (result.success) {
        statusText.textContent = "✅ Voice submitted successfully!";
        setTimeout(() => (window.location.href = result.redirect), 1000);
      } else {
        statusText.textContent = "❌ Upload failed. Please retry.";
      }
    };

    recorder.start();
    startTimer();
    startBtn.disabled = true;
    stopBtn.disabled = false;
    statusText.textContent = "🎙️ Recording started...";
  });

  stopBtn.addEventListener("click", () => {
    if (recorder && recorder.state === "recording") {
      recorder.stop();
      stopTimer();
      startBtn.disabled = false;
      stopBtn.disabled = true;
      statusText.textContent = "🛑 Recording stopped.";
    }
  });

  // Timer functions
  function startTimer() {
    seconds = 0;
    timer = setInterval(() => {
      seconds++;
      const m = String(Math.floor(seconds / 60)).padStart(2, "0");
      const s = String(seconds % 60).padStart(2, "0");
      timerDisplay.textContent = `Recording Time: ${m}:${s}`;
    }, 1000);
  }

  function stopTimer() {
    clearInterval(timer);
  }
});
