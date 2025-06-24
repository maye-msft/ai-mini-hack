const form = document.getElementById('video-form');
const promptInput = document.getElementById('prompt');
const durationInput = document.getElementById('duration');
const progressBar = document.getElementById('progress');
const progressStatus = document.getElementById('progress-status');
const videoPlayer = document.getElementById('video-player');
const videoPlaceholder = document.getElementById('video-placeholder');
const generateBtn = document.getElementById('generate-btn');

let pollInterval = null;

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const prompt = promptInput.value.trim();
    const duration = parseInt(durationInput.value, 10);
    if (!prompt || !duration) {
        alert('Please enter a prompt and duration.');
        return;
    }
    generateBtn.disabled = true;
    progressBar.value = 0;
    progressStatus.textContent = 'Submitting job...';
    videoPlayer.style.display = 'none';
    videoPlaceholder.style.display = 'flex';
    videoPlaceholder.textContent = 'Generating video...';

    try {
        const res = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, duration })
        });
        if (!res.ok) throw new Error('Failed to submit job');
        const data = await res.json();
        pollJobStatus(data.job_id);
    } catch (err) {
        progressStatus.textContent = 'Error: ' + err.message;
        generateBtn.disabled = false;
    }
});

function pollJobStatus(jobId) {
    let progress = 10;
    progressBar.value = progress;
    progressStatus.textContent = 'Job submitted. Waiting for processing...';
    pollInterval = setInterval(async () => {
        try {
            const res = await fetch(`/api/status/${jobId}`);
            if (!res.ok) throw new Error('Failed to get status');
            const data = await res.json();
            if (data.status === 'succeeded') {
                clearInterval(pollInterval);
                progressBar.value = 100;
                progressStatus.textContent = 'Video generation succeeded!';
                showVideo(data.video_url);
                generateBtn.disabled = false;
            } else if (data.status === 'failed') {
                clearInterval(pollInterval);
                progressBar.value = 0;
                progressStatus.textContent = 'Video generation failed.';
                generateBtn.disabled = false;
            } else {
                progress = Math.min(progress + 10, 90);
                progressBar.value = progress;
                progressStatus.textContent = `Status: ${data.status}`;
            }
        } catch (err) {
            clearInterval(pollInterval);
            progressStatus.textContent = 'Error: ' + err.message;
            generateBtn.disabled = false;
        }
    }, 3000);
}

function showVideo(videoUrl) {
    videoPlayer.src = videoUrl;
    videoPlayer.style.display = 'block';
    videoPlaceholder.style.display = 'none';
}
