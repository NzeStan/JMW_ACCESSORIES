class CartHandler {
    constructor() {
        this.initialize();
        // Make handler globally accessible
        window.cartHandler = this;
    }

    initialize() {
        // Cart form handling
        document.addEventListener('submit', this.handleFormSubmit.bind(this));
        // Custom input handling
        this.setupCustomInputs();
    }

    setupCustomInputs() {
        // Handle custom name checkbox
        const customNameCheckbox = document.querySelector('input[name="custom_name"]');
        if (customNameCheckbox) {
            customNameCheckbox.addEventListener('change', this.toggleCustomNameField.bind(this));
        }

        // Setup input transformations
        const uppercaseInputs = document.querySelectorAll('[data-transform-uppercase]');
        uppercaseInputs.forEach(input => {
            input.addEventListener('input', this.handleUppercaseTransform.bind(this));
        });
    }

    handleUppercaseTransform(event) {
        const input = event.target;
        input.value = input.value.toUpperCase();
    }

    toggleCustomNameField(event) {
        const customNameField = document.getElementById('customNameField');
        const isChecked = event.target.checked;
        
        if (isChecked) {
            customNameField.style.display = 'block';
            customNameField.style.animation = 'slideIn 0.3s ease forwards';
        } else {
            customNameField.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => {
                customNameField.style.display = 'none';
                customNameField.querySelector('input').value = '';
            }, 300);
        }
    }

    async handleLoadMore(event) {
        const button = event.target;
        const section = button.closest('section');
        const productType = section.dataset.productType;
        const isExpanded = button.dataset.expanded === 'true';
        const categorySlug = button.dataset.category || '';

        try {
            // Set loading state
            button.disabled = true;
            button.innerHTML = '<span class="loading loading-spinner loading-md"></span>';

            // Make the fetch request
            const response = await fetch(`/products/load-more/?type=${productType}&action=${isExpanded ? 'collapse' : 'expand'}${categorySlug ? `&category=${categorySlug}` : ''}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            });

            if (!response.ok) throw new Error('Network response was not ok');

            const html = await response.text();
            section.outerHTML = html;

        } catch (error) {
            console.error('Error:', error);
            window.location.reload();
        }
    }

    handleFormSubmit(event) {
        const form = event.target;
        if (!form.matches('#add-to-cart-form')) return;
        event.preventDefault();
        this.processCartAddition(form);
    }

   async processCartAddition(form) {
        const button = form.querySelector('button[type="submit"]');
        this.setLoadingState(button, true);

        try {
            const formData = new FormData(form);
            this.transformFormDataToUppercase(formData);

            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCsrfToken()
                },
                credentials: 'same-origin'
            });

            const data = await response.json();
            
            if (response.ok && data.status === 'success') {
                this.updateCartCount(data.cartCount);
                this.showSuccessState(button);
                this.animateProductToCart(button);
            } else {
                this.showErrorState(button);
                window.location.reload();
            }
        } catch (error) {
            console.error('Error processing cart addition:', error);
            this.showErrorState(button);
            window.location.reload();
        }
    }

    updateCartCount(newCount) {
        const cartCounts = document.querySelectorAll('.cart-count');
        cartCounts.forEach(cartCount => {
            cartCount.textContent = newCount;
            const cartIcon = cartCount.parentElement;
            cartIcon.classList.add('animate-bounce');
            setTimeout(() => cartIcon.classList.remove('animate-bounce'), 1000);
        });
    }

    transformFormDataToUppercase(formData) {
        ['call_up_number', 'custom_name_text'].forEach(field => {
            if (formData.has(field)) {
                formData.set(field, formData.get(field).toUpperCase());
            }
        });
    }

    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }

    setLoadingState(element, isLoading) {
        if (isLoading) {
            element.disabled = true;
            element.dataset.originalText = element.innerHTML;
            element.innerHTML = '<span class="loading loading-spinner loading-md"></span>';
        } else {
            element.disabled = false;
            if (element.dataset.originalText) {
                element.innerHTML = element.dataset.originalText;
            }
        }
    }

    showSuccessState(button) {
        button.innerHTML = '<span class="flex items-center gap-2"><svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/></svg>Added to Cart</span>';
        setTimeout(() => {
            button.innerHTML = button.dataset.originalText || 'Add to Cart';
            button.disabled = false;
        }, 2000);
    }

    showErrorState(button) {
        button.innerHTML = '<span class="flex items-center gap-2"><svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"/></svg>Error</span>';
        setTimeout(() => {
            button.innerHTML = button.dataset.originalText || 'Add to Cart';
            button.disabled = false;
        }, 2000);
    }
    resetButton(button) {
        button.className = button.dataset.originalClasses || 'btn btn-primary w-full';
        button.innerHTML = button.dataset.originalText || 'Add to Cart';
        button.disabled = false;
    }
}

// Initialize the cart handler when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new CartHandler();
});