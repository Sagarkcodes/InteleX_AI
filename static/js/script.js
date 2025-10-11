document.getElementById('resumeInput').addEventListener('change', function(event) {
    const file = event.target.files[0];
    if (file) {
        document.getElementById('statusMessage').textContent = `File '${file.name}' selected. Click 'Upload & Continue' to begin analysis.`;
        document.getElementById('statusMessage').style.color = 'var(--primary-color)';
    }
});