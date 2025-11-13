// ---- AUTO CAMERA START ----
window.addEventListener("load", async () => {
    const video = document.getElementById("preview");

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        video.srcObject = stream;
        document.getElementById("vidStatus").innerText = "";
        startGreeting();   // Auto greeting
    } catch (err) {
        console.error("Camera Error:", err);
        document.getElementById("vidStatus").innerText = "Camera access blocked.";
    }
});

// ---- AUTO GREETING ----
function startGreeting() {
    const greetingText = "Hello! I am InteleX. Your interview will begin now. Please listen carefully to the instructions.";

    // Update question box for user
    document.getElementById("viQuestion").innerText = "Preparing your interview...";

    // Speak greeting using same system used in audio test
    fetch("/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: greetingText })
    });

    // After greeting → load first question
    setTimeout(loadFirstQuestion, 4500);
}

// ---- LOAD FIRST QUESTION ----
async function loadFirstQuestion() {
    const res = await fetch("/next-question");
    const data = await res.json();

    document.getElementById("viQuestion").innerText = data.question;

    // Speak question
    fetch("/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: data.question })
    });

    startTimers();
}

// ---- TIMERS ----
let totalTime = 300; // 5 min
let pauseTime = 5;

function startTimers() {
    setInterval(() => {
        if (totalTime > 0) totalTime--;
        document.getElementById("totalTimerDisplay").innerText =
            new Date(totalTime * 1000).toISOString().substr(14, 5);
    }, 1000);

    setInterval(() => {
        if (pauseTime > 0) pauseTime--;
        document.getElementById("pauseTimerDisplay").innerText = pauseTime + "s";
    }, 1000);
}
