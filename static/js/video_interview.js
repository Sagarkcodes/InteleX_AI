// ==============================
// INTELEX VIDEO INTERVIEW ENGINE V4 (FIXED)
// ==============================

let stream;
let recorder;
let recordedChunks = [];

let audioContext;
let analyser;
let microphone;
let dataArray;

let isProcessing = false;
let interviewLocked = false;

let questionTimer;
let silenceTimer;

let questionSeconds = 300; // 5 minutes
let silenceSeconds = 8;

let speaking = false;


// ------------------------------
// START CAMERA (FIXED AUDIO)
// ------------------------------

async function startCamera(){

    const video = document.getElementById("camera");

    const videoStream = await navigator.mediaDevices.getUserMedia({
        video: true
    });

    const audioStream = await navigator.mediaDevices.getUserMedia({
        audio: true
    });

    stream = new MediaStream([
        ...videoStream.getVideoTracks(),
        ...audioStream.getAudioTracks()
    ]);

    console.log("Stream tracks:", stream.getTracks());

    video.srcObject = stream;

    setupAudioDetection();
}


// ------------------------------
// AUDIO ANALYSIS FOR SILENCE
// ------------------------------

function setupAudioDetection(){

    audioContext = new AudioContext();

    analyser = audioContext.createAnalyser();
    microphone = audioContext.createMediaStreamSource(stream);

    microphone.connect(analyser);

    analyser.fftSize = 512;

    dataArray = new Uint8Array(analyser.frequencyBinCount);

    detectSpeech();
}


function detectSpeech(){

    analyser.getByteFrequencyData(dataArray);

    let volume = dataArray.reduce((a,b)=>a+b) / dataArray.length;

    speaking = volume > 20;

    requestAnimationFrame(detectSpeech);
}


// ------------------------------
// SPEAK FUNCTION
// ------------------------------

function speak(text){

    return new Promise(resolve => {

        if(!text){
            resolve();
            return;
        }

        const utter = new SpeechSynthesisUtterance(text);

        utter.onend = () => resolve();

        speechSynthesis.speak(utter);

    });
}


// ------------------------------
// SHOW QUESTION
// ------------------------------

async function showQuestion(text){

    const questionBox = document.getElementById("questionText");

    questionBox.innerText = text;

    await speak(text);
}


// ------------------------------
// START INTERVIEW
// ------------------------------

async function startInterview(){

    try {

        const res = await fetch("/api/video-interview-start");
        const data = await res.json();

        await speak(data.greeting_text);
        await speak(data.instructions_text);
        await speak(data.praise_text);

        await showQuestion(data.question_text);

        startRecording();

    } catch (err) {
        console.error("Start interview error:", err);
    }
}


// ------------------------------
// START RECORDING (FINAL FIX)
// ------------------------------

function startRecording(){

    recordedChunks = [];

    const audioTracks = stream.getAudioTracks();

    if (audioTracks.length === 0) {
        console.error("❌ No audio track found");
        return;
    }

    console.log("🎤 Audio track:", audioTracks[0]);

    const audioOnlyStream = new MediaStream(audioTracks);

    let options = {};

    if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
        options.mimeType = "audio/webm;codecs=opus";
    } else if (MediaRecorder.isTypeSupported("audio/webm")) {
        options.mimeType = "audio/webm";
    } else {
        options.mimeType = "";
    }

    recorder = new MediaRecorder(audioOnlyStream, options);

    recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
            recordedChunks.push(e.data);
        }
    };

    recorder.onstart = () => {
        console.log("✅ Recording started");
    };

    recorder.onstop = () => {
        console.log("🛑 Recording stopped");
    };

    recorder.start();

    startQuestionTimer();
    startSilenceTimer();
}


// ------------------------------
// STOP RECORDING
// ------------------------------

function stopRecording(){

    return new Promise(resolve => {

        if(!recorder || recorder.state === "inactive"){
            resolve();
            return;
        }

        recorder.onstop = resolve;

        recorder.stop();

    });
}


// ------------------------------
// QUESTION TIMER
// ------------------------------

function startQuestionTimer(){

    clearInterval(questionTimer);

    questionSeconds = 300;

    updateQuestionTimerUI();

    questionTimer = setInterval(()=>{

        questionSeconds--;

        updateQuestionTimerUI();

        if(questionSeconds <= 0){

            clearInterval(questionTimer);
            submitAnswer();

        }

    },1000);
}


function updateQuestionTimerUI(){

    let minutes = Math.floor(questionSeconds / 60);
    let seconds = questionSeconds % 60;

    seconds = seconds < 10 ? "0"+seconds : seconds;

    document.getElementById("timeLeft").innerText =
        minutes + ":" + seconds;
}


// ------------------------------
// SILENCE TIMER
// ------------------------------

function startSilenceTimer(){

    clearInterval(silenceTimer);

    silenceSeconds = 8;

    silenceTimer = setInterval(()=>{

        if(speaking){

            silenceSeconds = 8;
            document.getElementById("pauseTime").innerText = "Speaking";
            return;

        }

        silenceSeconds--;

        document.getElementById("pauseTime").innerText =
            silenceSeconds + "s";

        if(silenceSeconds <= 0){

            clearInterval(silenceTimer);
            submitAnswer();

        }

    },1000);
}


// ------------------------------
// SUBMIT ANSWER
// ------------------------------

async function submitAnswer(){

    if(isProcessing || interviewLocked) return;

    isProcessing = true;
    interviewLocked = true;

    const questionBox = document.getElementById("questionText");
    const submitBtn = document.getElementById("submitAnswer");

    submitBtn.disabled = true;

    try{

        await stopRecording();

        const blob = new Blob(recordedChunks,{type: recorder.mimeType});
        console.log("Recorded blob size:", blob.size);

        const formData = new FormData();
        formData.append("audio", blob, "answer.webm");

        const res = await fetch("/next-question",{
            method:"POST",
            body:formData
        });

        const data = await res.json();

        if(data.completed){

            // 🔥 ONLY CHANGE (redirect support)
            if(data.redirect){
                window.location.href = data.redirect;
                return;
            }

            questionBox.innerText = data.message;

            await speak(data.feedback);

            isProcessing = true;
            interviewLocked = true;

            return;
        }

        await speak(data.feedback);

        await showQuestion(data.question);

        isProcessing = false;
        interviewLocked = false;

        submitBtn.disabled = false;

        startRecording();

    }
    catch(err){

        console.error("Interview error:", err);

        isProcessing = false;
        interviewLocked = false;

        submitBtn.disabled = false;

        startRecording();

    }
}


// ------------------------------
// INIT
// ------------------------------

window.addEventListener("DOMContentLoaded", async () => {

    await startCamera();

    await startInterview();

    document
        .getElementById("submitAnswer")
        .addEventListener("click", submitAnswer);

});