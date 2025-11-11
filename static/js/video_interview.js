// static/js/video_interview.js
// Updated for: agent-left / video-right layout, single TTS voice, begin->question->auto-record flow,
// two timers (total + pause), revolving avatar while speaking.

// DOM
const preview = document.getElementById('preview');
const openCameraBtn = document.getElementById('openCameraBtn');
const beginBtn = document.getElementById('beginBtn');
const submitBtn = document.getElementById('submitBtn');
const vidStatus = document.getElementById('vidStatus');
const videoTimerFill = document.getElementById('videoTimerFill');
const viQuestion = document.getElementById('viQuestion');
const aiText = document.getElementById('aiText');
const agentPhoto = document.getElementById('agentPhoto');
const totalTimerDisplay = document.getElementById('totalTimerDisplay');
const pauseTimerDisplay = document.getElementById('pauseTimerDisplay');

let candidateName = "Candidate";
let candidateSkills = [];
let previousQuestions = [];

let streamRef = null;
let mediaRecorder = null;
let recordedChunks = [];
let audioContext = null;
let analyser = null;
let dataArray = null;
let rafId = null;

let recordingState = "idle"; // idle, awaiting_speech, answering, uploading
const graceSeconds = 5;      // must start speaking within 5s else auto-submit
const answerSeconds = 300;   // 5 minutes max
const pauseAllowed = 5;      // allowed silence seconds during answer
let startTime = 0;
let silenceCounter = 0;

// UTIL: format seconds -> MM:SS
function fmtSeconds(s) {
  const mm = Math.floor(s/60).toString().padStart(2,'0');
  const ss = Math.floor(s%60).toString().padStart(2,'0');
  return `${mm}:${ss}`;
}

// TTS helper (single voice) - also toggles speaking animation
function speakOnce(text, onEnd) {
  try {
    window.speechSynthesis.cancel();
    const ut = new SpeechSynthesisUtterance(text);
    ut.rate = 1.05;
    ut.pitch = 1.02;
    const voices = window.speechSynthesis.getVoices();
    if (voices && voices.length) ut.voice = voices.find(v => v.lang && v.lang.includes('en')) || voices[0];

    // add speaking class to avatar
    agentPhoto.classList.add('speaking');
    ut.onend = () => {
      agentPhoto.classList.remove('speaking');
      if (onEnd) onEnd();
    };
    window.speechSynthesis.speak(ut);
  } catch (e) {
    // fallback: just set text and call callback
    console.warn("TTS error", e);
    agentPhoto.classList.remove('speaking');
    if (onEnd) onEnd();
  }
}

// On load: prompt to open camera
window.addEventListener('load', () => {
  const greet = `Welcome — I am InteleX. Please open your camera to begin the video interview.`;
  aiText.textContent = greet;
  speakOnce(greet);
});

// Open camera -> prepare audio analyser + enable Begin
openCameraBtn.addEventListener('click', async () => {
  openCameraBtn.disabled = true;
  try {
    streamRef = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: true });
    preview.srcObject = streamRef;
    vidStatus.textContent = "Camera open. Position your face in the center of the frame.";
    beginBtn.disabled = false;
    submitBtn.disabled = true;

    // audio analyser for VAD
    if (!audioContext) {
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const src = audioContext.createMediaStreamSource(streamRef);
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      src.connect(analyser);
      dataArray = new Uint8Array(analyser.fftSize);
    }

    // speak short instructions (concise)
    const i1 = "Camera is open. Position your face in the centre of the frame.";
    const i2 = "When you press Begin I will ask the first question. You will have five seconds to start speaking, otherwise your answer will be submitted automatically.";
    aiText.textContent = i1 + " " + i2;
    speakOnce(i1, () => speakOnce(i2));
  } catch (err) {
    console.error("Camera error:", err);
    vidStatus.textContent = "⚠️ Camera access denied or unavailable.";
    openCameraBtn.disabled = false;
  }
});

// Begin: fetch question, speak it, then start auto-recording flow
beginBtn.addEventListener('click', async () => {
  if (!streamRef) { vidStatus.textContent = "Open the camera first."; return; }
  beginBtn.disabled = true;
  viQuestion.textContent = "Thinking...";
  try {
    const r = await fetch('/next-question', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ name: candidateName, skills: candidateSkills, previous: previousQuestions, short: true })
    });
    const data = await r.json();
    if (!data.success) {
      viQuestion.textContent = "⚠️ Could not fetch question.";
      beginBtn.disabled = false;
      return;
    }
    const q = data.question || "Tell me about a project you are proud of.";
    previousQuestions.push(q);
    // keep only the first sentence for crisp HR phrasing
    const shortQ = q.split(/(?<=[.?!])\s+/)[0].trim() || q;
    viQuestion.textContent = shortQ;

    // speak question once, then start recording flow
    speakOnce(shortQ, () => beginAutoRecordingFlow());
  } catch (err) {
    console.error("LLM error", err);
    viQuestion.textContent = "⚠️ LLM error.";
    beginBtn.disabled = false;
  }
});

// Start recording flow: wants to capture video + audio, wait for user speech within graceSeconds
async function beginAutoRecordingFlow() {
  recordedChunks = [];
  try {
    mediaRecorder = new MediaRecorder(streamRef, { mimeType: 'video/webm;codecs=vp9,opus' });
  } catch (e) {
    try { mediaRecorder = new MediaRecorder(streamRef); } catch (err) {
      console.error("MediaRecorder not supported", err);
      vidStatus.textContent = "⚠️ Recording not supported.";
      beginBtn.disabled = false;
      return;
    }
  }
  mediaRecorder.ondataavailable = e => { if (e.data && e.data.size) recordedChunks.push(e.data); };
  mediaRecorder.onstop = onAnswerStop;

  mediaRecorder.start();
  recordingState = "awaiting_speech";
  vidStatus.textContent = `Speak within ${graceSeconds} seconds to begin your answer...`;
  startTime = Date.now();

  // reset timers UI
  totalTimerDisplay.textContent = fmtSeconds(answerSeconds);
  pauseTimerDisplay.textContent = `0s`;
  videoTimerFill.style.width = '0%';

  monitorSpeechStart(graceSeconds);
}

// monitorSpeechStart: detect amplitude above threshold within graceSeconds
function monitorSpeechStart(grace) {
  const threshold = 8;
  const start = Date.now();
  function analyze() {
    analyser.getByteTimeDomainData(dataArray);
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
      const v = (dataArray[i] - 128);
      sum += v * v;
    }
    const rms = Math.sqrt(sum / dataArray.length);
    if (rms > threshold) {
      // speech started -> transition to answering
      recordingState = "answering";
      vidStatus.textContent = `Answering... you have ${Math.floor(answerSeconds/60)} minutes remaining`;
      startAnswerTimer(answerSeconds);
      return;
    } else {
      const elapsed = (Date.now() - start) / 1000;
      const left = grace - elapsed;
      vidStatus.textContent = `Please start speaking within ${Math.max(0, Math.ceil(left))}s...`;
      if (elapsed >= grace) {
        // no speech -> auto-submit
        try { if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop(); } catch(e){}
        recordingState = "uploading";
        return;
      }
      rafId = requestAnimationFrame(analyze);
    }
  }
  rafId = requestAnimationFrame(analyze);
}

// startAnswerTimer: updates total timer + pause timer, auto-submits on long pause or timeout
function startAnswerTimer(durationSeconds) {
  const started = Date.now();
  let lastSpoken = Date.now();
  silenceCounter = 0;

  function monitor() {
    analyser.getByteTimeDomainData(dataArray);
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
      const v = (dataArray[i] - 128);
      sum += v * v;
    }
    const rms = Math.sqrt(sum / dataArray.length);
    const speechThreshold = 8;

    if (rms > speechThreshold) {
      lastSpoken = Date.now();
      silenceCounter = 0;
    } else {
      silenceCounter = Math.floor((Date.now() - lastSpoken) / 1000);
    }

    const elapsed = Math.floor((Date.now() - started) / 1000);
    const timeLeft = Math.max(durationSeconds - elapsed, 0);
    totalTimerDisplay.textContent = fmtSeconds(timeLeft);
    pauseTimerDisplay.textContent = `${silenceCounter}s`;

    const pct = Math.round(((durationSeconds - timeLeft) / durationSeconds) * 100);
    videoTimerFill.style.width = pct + '%';

    // if silence longer than allowed -> auto-stop/submit
    if (silenceCounter >= pauseAllowed) {
      if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
      recordingState = "uploading";
      return;
    }

    if (timeLeft <= 0) {
      if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
      recordingState = "uploading";
      return;
    }

    rafId = requestAnimationFrame(monitor);
  }

  rafId = requestAnimationFrame(monitor);
}

// onAnswerStop: upload blob to server
async function onAnswerStop() {
  if (rafId) cancelAnimationFrame(rafId);
  videoTimerFill.style.width = '0%';
  vidStatus.textContent = "Uploading answer...";
  const blob = new Blob(recordedChunks, { type: 'video/webm' });
  const fd = new FormData();
  fd.append('video', blob, 'answer.webm');

  try {
    const res = await fetch('/upload-video', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.success) {
      vidStatus.textContent = "✅ Answer uploaded.";
      submitBtn.disabled = false;
    } else {
      vidStatus.textContent = "⚠️ Upload failed.";
    }
  } catch (err) {
    console.error("Upload error", err);
    vidStatus.textContent = "⚠️ Upload error.";
  } finally {
    // reset
    beginBtn.disabled = false;
    submitBtn.disabled = false;
    recordingState = "idle";
  }
}

// Submit button: explicit upload / finalize (allows manual submit too)
submitBtn.addEventListener('click', () => {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  } else {
    vidStatus.textContent = "No recording in progress.";
  }
});

// if user clicks "leave" or navigates away ensure stopping
window.addEventListener('beforeunload', () => {
  try { if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop(); } catch(e){}
});

// expose some debug hooks if needed
window.__VI = {
  beginAutoRecordingFlow,
  monitorSpeechStart
};
