// Basic animation example
gsap.to(".your-element", {
    duration: 1,
    x: 100,
    y: 100,
    rotation: 360
});

// Timeline example
const tl = gsap.timeline();
tl.to(".first", {duration: 1, x: 100})
  .to(".second", {duration: 1, y: 50})
  .to(".third", {duration: 1, rotation: 360});

//for messages
document.addEventListener('DOMContentLoaded', (event) => {
    const toasts = document.querySelectorAll('[id^="toast-"]');
    toasts.forEach((toast) => {
        setTimeout(() => {
            toast.remove();
        }, 5000);
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


