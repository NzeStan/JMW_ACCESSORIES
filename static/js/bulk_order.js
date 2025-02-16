// js/bulk_order.js
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Handle form submission
document.addEventListener('htmx:afterRequest', function(evt) {
    if (evt.detail.successful && evt.detail.xhr.response) {
        try {
            const response = JSON.parse(evt.detail.xhr.response);
            if (response.errors) {
                Object.keys(response.errors).forEach(field => {
                    const input = document.querySelector(`[name="${field}"]`);
                    if (input) {
                        input.classList.add('input-error');
                        const errorDiv = document.createElement('div');
                        errorDiv.className = 'text-error text-sm mt-1';
                        errorDiv.textContent = response.errors[field][0];
                        input.parentNode.appendChild(errorDiv);
                    }
                });
            }
        } catch (e) {
            // Response might not be JSON
            console.log('Not a JSON response');
        }
    }
});

// Add clipboard functionality
document.addEventListener('click', function(e) {
    const button = e.target.closest('[data-copy-text]');
    if (button) {
        const textToCopy = button.getAttribute('data-copy-text');
        navigator.clipboard.writeText(textToCopy)
            .catch(err => console.error('Failed to copy:', err));
    }
});

// Clear validation errors on input
document.querySelectorAll('input, select').forEach(input => {
    input.addEventListener('input', function() {
        this.classList.remove('input-error');
        const errorDiv = this.parentNode.querySelector('.text-error');
        if (errorDiv) {
            errorDiv.remove();
        }
    });
});

function copyToClipboardAndNotify(elementId) {
    const input = document.getElementById(elementId);
    const textToCopy = input.value;
    
    navigator.clipboard.writeText(textToCopy)
        .then(() => {
            const messagesContainer = document.getElementById('messages-container');
            if (messagesContainer) {
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message-alert pointer-events-auto transform transition-all duration-300 ease-in-out flex items-center w-full p-4 rounded-lg shadow-lg bg-green-100 border border-green-400 text-green-700';
                messageDiv.innerHTML = `
                    <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span class="flex-1 font-medium text-sm">Copied to clipboard!</span>
                    <button onclick="this.parentElement.remove()" class="ml-4 hover:text-opacity-75">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                `;
                messagesContainer.appendChild(messageDiv);

                // Auto-remove after 3 seconds
                setTimeout(() => {
                    messageDiv.style.opacity = '0';
                    setTimeout(() => messageDiv.remove(), 300);
                }, 3000);
            }
        })
        .catch(err => console.error('Failed to copy:', err));
}