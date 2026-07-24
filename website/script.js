document.addEventListener('DOMContentLoaded', () => {
    // Terminal Typing Effect
    const terminalOutput = document.getElementById('term-output');
    const typewriter = document.getElementById('typewriter');
    const commandText = "npx cherenkov init";
    
    // Typewriter effect
    typewriter.textContent = '';
    let i = 0;
    
    setTimeout(() => {
        const typingInterval = setInterval(() => {
            if (i < commandText.length) {
                typewriter.textContent += commandText.charAt(i);
                i++;
            } else {
                clearInterval(typingInterval);
                
                // Show output after typing completes
                setTimeout(() => {
                    terminalOutput.style.display = 'block';
                    
                    // Animate lines appearing
                    const lines = terminalOutput.querySelectorAll('.line');
                    lines.forEach((line, index) => {
                        setTimeout(() => {
                            line.style.opacity = '1';
                            line.style.transform = 'translateY(0)';
                            line.style.transition = 'all 0.3s ease';
                        }, (index + 1) * 300);
                    });
                }, 400);
            }
        }, 80);
    }, 1000); // Initial delay
    
    // Copy Command Functionality
    const copyBtn = document.getElementById('copy-cmd');
    
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(commandText).then(() => {
            const originalHTML = copyBtn.innerHTML;
            copyBtn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg> Copied!`;
            copyBtn.classList.add('copied');
            
            setTimeout(() => {
                copyBtn.innerHTML = originalHTML;
                copyBtn.classList.remove('copied');
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy text: ', err);
        });
    });
    
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});
