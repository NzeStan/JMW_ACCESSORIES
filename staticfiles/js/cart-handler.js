// cart-handler.js

class CartHandler {
    constructor() {
        this.initialize();
    }

    initialize() {
        // Cart form handling
        document.addEventListener('submit', this.handleFormSubmit.bind(this));
        // Product grid loading
        this.setupProductLoadMore();
        // Custom input handling
        this.setupCustomInputs();
    }

    setupProductLoadMore() {
        const loadMoreButtons = document.querySelectorAll('[data-load-more]');
        loadMoreButtons.forEach(button => {
            button.addEventListener('click', this.handleLoadMore.bind(this));
        });
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
        
        customNameField.classList.toggle('hidden', !isChecked);
        const customNameInput = customNameField.querySelector('input');
        if (!isChecked) {
            customNameInput.value = '';
        }
    }

    async handleLoadMore(event) {
        const button = event.target;
        const section = button.closest('section');
        const productType = section.getAttribute('data-product-type');
        const isExpanded = button.getAttribute('data-expanded') === 'true';
        const categorySlug = button.getAttribute('data-category') || '';

        try {
            this.setLoadingState(button, true);
            
            const response = await fetch(`/products/load-more/?type=${productType}&action=${isExpanded ? 'collapse' : 'expand'}${categorySlug ? `&category=${categorySlug}` : ''}`);
            const html = await response.text();
            
            section.outerHTML = html;
            this.setupProductLoadMore(); // Reattach events
            
        } catch (error) {
            console.error('Error loading products:', error);
            // Show error message using existing Django messages framework
            window.location.reload(); // Fallback
        } finally {
            this.setLoadingState(button, false);
        }
    }

    handleFormSubmit(event) {
        const form = event.target;
        
        // Only handle cart-related forms
        if (!form.matches('#add-to-cart-form')) {
            return;
        }
        
        event.preventDefault();
        this.processCartAddition(form);
    }

    async processCartAddition(form) {
        const button = form.querySelector('button[type="submit"]');
        this.setLoadingState(button, true);

        try {
            const formData = new FormData(form);
            // Transform inputs to uppercase where needed
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
                // Don't show success notification - let Django messages handle it
                this.showSuccessState(button);
            } else {
                // Let Django messages handle the error
                this.showErrorState(button);
                window.location.reload(); // Refresh to show Django message
            }
        } catch (error) {
            console.error('Error processing cart addition:', error);
            this.showErrorState(button);
            window.location.reload(); // Refresh to show Django message
        }
    }

    transformFormDataToUppercase(formData) {
        const upperCaseFields = ['call_up_number', 'custom_name_text'];
        upperCaseFields.forEach(field => {
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
            element.classList.add('loading');
            element.dataset.originalText = element.innerHTML;
            element.innerHTML = 'Processing...';
        } else {
            element.disabled = false;
            element.classList.remove('loading');
            if (element.dataset.originalText) {
                element.innerHTML = element.dataset.originalText;
            }
        }
    }

    showSuccessState(button) {
        button.classList.remove('btn-primary', 'loading');
        button.classList.add('btn-success');
        button.innerHTML = '<span class="flex items-center gap-2"><svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" /></svg>Added to Cart</span>';
        
        setTimeout(() => {
            this.resetButton(button);
        }, 2000);
    }

    showErrorState(button) {
        button.classList.remove('btn-primary', 'loading');
        button.classList.add('btn-error');
        button.innerHTML = '<span class="flex items-center gap-2"><svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>Error</span>';
        
        setTimeout(() => {
            this.resetButton(button);
        }, 2000);
    }

    resetButton(button) {
        button.className = button.dataset.originalClasses || 'btn btn-primary w-full';
        button.innerHTML = button.dataset.originalText || 'Add to Cart';
        button.disabled = false;
    }

    updateCartCount(newCount) {
        const cartCount = document.querySelector('.indicator-item');
        if (cartCount) {
            cartCount.textContent = newCount;
            
            const cartIcon = cartCount.parentElement;
            cartIcon.classList.add('animate-bounce');
            setTimeout(() => {
                cartIcon.classList.remove('animate-bounce');
            }, 1000);
        }
    }
}

// Initialize the cart handler when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new CartHandler();
});