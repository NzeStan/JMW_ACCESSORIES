//for messages
document.addEventListener('DOMContentLoaded', function() {
    function handleMessages() {
        const messagesContainer = document.getElementById('messages-container');
        if (messagesContainer) {
            const messages = messagesContainer.getElementsByClassName('message-alert');
            Array.from(messages).forEach(function(message) {
                setTimeout(function() {
                    message.style.transform = 'translateY(10px)';
                    message.style.opacity = '0';
                    setTimeout(() => {
                        message.remove();
                    }, 300);
                }, 3000);
            });
        }
    }

    // Handle initial messages
    handleMessages();

    // Handle messages after HTMX requests
    document.addEventListener('htmx:afterSwap', function() {
        handleMessages();
    });
});

//footer (year)
document.addEventListener('DOMContentLoaded', function() {
    // Set copyright year
    const yearElement = document.getElementById('year');
    if (yearElement) {
        yearElement.textContent = new Date().getFullYear();
    }
    
});

//state and local government dropdown
document.addEventListener("DOMContentLoaded", () => {
    const stateField = document.querySelector("#id_state");
    const lgaField = document.querySelector("#id_local_government_area");

    if (stateField && lgaField) {
        stateField.addEventListener("change", (e) => {
            const selectedState = e.target.value;
            const lgas = STATES_AND_LGAS[selectedState] || [];
            lgaField.innerHTML = '<option value="">Select Local Government</option>';
            lgas.forEach((lga) => {
                const option = document.createElement("option");
                option.value = lga;
                option.textContent = lga;
                lgaField.appendChild(option);
            });
        });
    }
});

// Function to hide an element with fade-out animation
function hideWithFadeOut(selector, delay = 5000) {
    setTimeout(() => {
        const element = document.querySelector(selector);
        if (element) {
            element.style.transition = 'opacity 0.5s ease-out';
            element.style.opacity = '0';
            setTimeout(() => {
                element.style.display = 'none';
            }, 500); // Matches the transition duration
        }
    }, delay);
}

// Call the function for the swipe-indicator
hideWithFadeOut('.swipe-indicator');


document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("form");
    if (!form) return; // Ensure a form exists before proceeding

    const submitBtn = document.getElementById("submit-btn");
    const btnText = document.getElementById("btn-text");
    const spinner = document.getElementById("spinner");

    form.addEventListener("submit", function () {
        if (submitBtn) {
            submitBtn.disabled = true;
        }
        if (btnText) {
            btnText.textContent = "Processing...";
        }
        if (spinner) {
            spinner.classList.remove("hidden");
        }
    });
});