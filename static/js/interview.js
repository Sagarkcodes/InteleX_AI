// ==================== VOICE PERSONALITY ASSESSMENT ====================

// ----------- ELEMENT REFERENCES -----------
const aiAvatar = document.getElementById("ai-avatar");
const agentDialogue = document.getElementById("agent-dialogue");
const startBtn = document.getElementById("start-audio-btn");
const stopBtn = document.getElementById("stop-record-btn");
const recStatus = document.getElementById("rec-status");
const timerBar = document.getElementById("record-progress");
const timerText = document.getElementById("record-timer");

// ----------- AUDIO RECORDING STATE -----------
let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let recordTimer;
let progressInterval;
const RECORD_TIME_LIMIT = 60; // 1 minute

// ----------- SPEECH SYNTHESIS -----------
function speak(text, callback) {
  agentDialogue.textContent = text;
  const synth = window.speechSynthesis;
  const utter = new SpeechSynthesisUtterance(text);

  utter.pitch = 1.05;
  utter.rate = 1.0;
  utter.volume = 1.0;

  const voices = synth.getVoices();
  if (voices && voices.length > 0) {
    utter.voice = voices.find(v => v.lang && v.lang.includes("en")) || voices[0];
  }

  aiAvatar.classList.add("speaking");
  synth.speak(utter);

  utter.onend = () => {
    aiAvatar.classList.remove("speaking");
    if (callback) callback();
  };
}

// ----------- INTRO SEQUENCE -----------
function playIntro() {
  speak(
    "Hello there! I’m InteleX, your AI interview assistant. Let’s begin with a short personality reading test.",
    () => {
      speak(
        "When I finish speaking, read the displayed paragraph aloud clearly for one minute.",
        () => {
          recStatus.textContent = "You can begin when you're ready.";
          startBtn.disabled = false;
        }
      );
    }
  );
}

// Trigger the intro once browser loads voices
window.speechSynthesis.onvoiceschanged = () => playIntro();

// ----------- RECORDING FUNCTIONS -----------
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
    mediaRecorder.onstop = uploadAudio;

    isRecording = true;
    startBtn.disabled = true;
    stopBtn.disabled = false;
    recStatus.textContent = "Recording in progress... 🎤";
    startTimer();

    mediaRecorder.start();
  } catch (err) {
    recStatus.textContent = "⚠️ Microphone access denied. Please allow microphone and retry.";
    console.error("Mic access error:", err);
  }
}

function stopRecording() {
  if (!isRecording) return;
  isRecording = false;

  recStatus.textContent = "Processing your response...";
  stopBtn.disabled = true;

  clearInterval(progressInterval);
  clearInterval(recordTimer);
  mediaRecorder.stop();
}

// ----------- TIMER HANDLING -----------
function startTimer() {
  let elapsed = 0;
  timerBar.style.width = "0%";

  progressInterval = setInterval(() => {
    elapsed++;
    const progressPercent = (elapsed / RECORD_TIME_LIMIT) * 100;
    timerBar.style.width = progressPercent + "%";
    const timeLeft = RECORD_TIME_LIMIT - elapsed;
    timerText.textContent = formatTime(timeLeft);

    if (elapsed >= RECORD_TIME_LIMIT) stopRecording();
  }, 1000);
}

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

// ----------- UPLOAD AUDIO TO BACKEND -----------
function uploadAudio() {
  const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
  audioChunks = [];

  const formData = new FormData();
  formData.append("audio", audioBlob);

  fetch("/upload-audio", { method: "POST", body: formData })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        recStatus.textContent = "✅ Audio uploaded successfully!";
        setTimeout(() => {
          window.location.href = data.redirect;
        }, 1000);
      } else {
        recStatus.textContent = "⚠️ Upload failed. Try again.";
      }
    })
    .catch(err => {
      console.error("Upload error:", err);
      recStatus.textContent = "⚠️ Connection error.";
    });
}

// ----------- EVENT LISTENERS -----------
startBtn.addEventListener("click", startRecording);
stopBtn.addEventListener("click", stopRecording);
