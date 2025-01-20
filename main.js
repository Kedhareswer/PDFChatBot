document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const uploadStatus = document.getElementById('uploadStatus');
    const questionInput = document.getElementById('questionInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatMessages = document.getElementById('chatMessages');
    const keywordsList = document.getElementById('keywordsList');
    const confidenceBar = document.getElementById('confidenceBar');

    // File Upload Handling
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        handleFileUpload(file);
    });

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        handleFileUpload(file);
    });

    async function handleFileUpload(file) {
        if (!file || !file.name.endsWith('.pdf')) {
            uploadStatus.innerHTML = 'Please upload a PDF file';
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            uploadStatus.innerHTML = 'Uploading...';
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (data.success) {
                uploadStatus.innerHTML = 'PDF processed successfully!';
                document.getElementById('chatSection').style.display = 'flex';
            } else {
                uploadStatus.innerHTML = data.error || 'Upload failed';
            }
        } catch (error) {
            uploadStatus.innerHTML = 'Error uploading file';
            console.error(error);
        }
    }

    // Chat Handling
    sendBtn.addEventListener('click', sendQuestion);
    questionInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendQuestion();
    });

    async function sendQuestion() {
        const question = questionInput.value.trim();
        if (!question) return;

        // Add user message to chat
        addMessage(question, 'user');
        questionInput.value = '';

        try {
            const response = await fetch('/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question })
            });
            const data = await response.json();

            // Add bot response to chat
            addMessage(data.answer, 'bot');

            // Update confidence meter
            updateConfidence(data.confidence);

            // Update keywords
            updateKeywords(data.keywords);
        } catch (error) {
            addMessage('Sorry, there was an error processing your question.', 'bot');
            console.error(error);
        }
    }

    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', `${sender}-message`);
        messageDiv.textContent = text;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function updateConfidence(confidence) {
        const percentage = confidence * 100;
        confidenceBar.style.width = `${percentage}%`;
    }

    function updateKeywords(keywords) {
        keywordsList.innerHTML = keywords
            .map(keyword => `<div class="keyword">${keyword}</div>`)
            .join('');
    }
});