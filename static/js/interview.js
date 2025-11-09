// ==================== INTERVIEW PAGE SCRIPT ====================

// HTML elements
const aiText = document.getElementById("aiText");
const statusText = document.getElementById("statusText");
const recordBtn = document.getElementById("recordBtn");
const agentPhoto = document.getElementById("agentPhoto");

// AI Introduction lines
const introLines = [
  "Hello! I'm InteleX, your AI interviewer.",
  "We'll start with a short voice-based personality test.",
  "Please read the paragraph below aloud when I say Begin."
];

// --------------- FUNCTION: SPEAK USING BROWSER VOICE ---------------
function speak(text, callback) {
  aiText.textContent = text;

  const synth = window.speechSynthesis;
  const utter = new SpeechSynthesisUtterance(text);
  utter.pitch = 1.05;
  utter.rate = 1.1; // slightly faster for natural tone

  // Pick an English voice if available
  const voices = synth.getVoices();
  if (voices && voices.length > 0) {
    utter.voice = voices.find(v => v.lang && v.lang.includes('en')) || voices[0];
  }

  agentPhoto.classList.add("speaking");
  synth.speak(utter);

  utter.onend = () => {
    agentPhoto.classList.remove("speaking");
    if (callback) callback();
  };
}

// --------------- FUNCTION: PLAY INTRO SEQUENCE ---------------
function playIntro(index = 0) {
  if (index < introLines.length) {
    speak(introLines[index], () => playIntro(index + 1));
  } else {
    setTimeout(() => {
      speak("Begin reading now.", enableRecording);
    }, 800);
  }
}

// --------------- FUNCTION: ENABLE RECORDING BUTTON ---------------
function enableRecording() {
  recordBtn.disabled = false;
  statusText.textContent = "You may start recording now 🎤";
}

// --------------- INITIATE INTRO WHEN VOICES READY ---------------
window.speechSynthesis.onvoiceschanged = () => playIntro();

// ==================== AUDIO RECORDING ====================
let mediaRecorder;
let audioChunks = [];
let isRecording = false;

recordBtn.addEventListener("click", async () => {
  if (!isRecording) startRecording();
  else stopRecording();
});

async function startRecording() {
  try {
    recordBtn.textContent = "Stop Recording";
    statusText.textContent = "Recording... please read clearly.";
    isRecording = true;

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
    mediaRecorder.onstop = uploadAudio;
    mediaRecorder.start();
  } catch (err) {
    console.error("Microphone access error:", err);
    statusText.textContent = "⚠️ Microphone access denied.";
  }
}

function stopRecording() {
  recordBtn.textContent = "Start Recording";
  statusText.textContent = "Processing audio...";
  isRecording = false;
  mediaRecorder.stop();
}

function uploadAudio() {
  const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
  audioChunks = [];
  const formData = new FormData();
  formData.append("audio", audioBlob);

  fetch("/upload-audio", { method: "POST", body: formData })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        statusText.textContent = "✅ Audio saved! Redirecting...";
        setTimeout(() => window.location.href = data.redirect, 900);
      } else {
        statusText.textContent = "⚠️ Upload failed";
      }
    })
    .catch(() => {
      statusText.textContent = "⚠️ Error uploading.";
    });
}
