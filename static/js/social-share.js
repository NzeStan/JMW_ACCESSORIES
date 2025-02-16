// This class will handle all our social sharing functionality
class SocialShare {
    constructor() {
        this.copyButton = document.querySelector('[data-copy-link]');
        this.setupCopyLink();
        this.setupShareAnimations();
    }

    // Sets up the copy link functionality with a nice feedback mechanism
    setupCopyLink() {
        if (!this.copyButton) return;

        this.copyButton.addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(window.location.href);
                
                // Change button text to show feedback
                const originalText = this.copyButton.querySelector('.copy-text').textContent;
                const originalIcon = this.copyButton.querySelector('.copy-icon');
                const successIcon = this.copyButton.querySelector('.success-icon');
                
                // Show success state
                this.copyButton.querySelector('.copy-text').textContent = 'Copied!';
                originalIcon.classList.add('hidden');
                successIcon.classList.remove('hidden');
                
                // Reset after 2 seconds
                setTimeout(() => {
                    this.copyButton.querySelector('.copy-text').textContent = originalText;
                    originalIcon.classList.remove('hidden');
                    successIcon.classList.add('hidden');
                }, 2000);
            } catch (err) {
                console.error('Failed to copy link:', err);
                alert('Failed to copy link. Please try again.');
            }
        });
    }

    // Adds subtle hover animations to all share buttons
    setupShareAnimations() {
        const shareButtons = document.querySelectorAll('.share-button');
        
        shareButtons.forEach(button => {
            button.addEventListener('mouseenter', () => {
                button.style.transform = 'translateY(-2px)';
            });
            
            button.addEventListener('mouseleave', () => {
                button.style.transform = 'translateY(0)';
            });
        });
    }
}

// Initialize when the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new SocialShare();
});