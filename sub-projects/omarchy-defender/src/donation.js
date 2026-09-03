/**
 * Omarchy Defender - Donation System Client
 * Handles donation modal, Stripe checkout, and sticky notes display
 */

(function() {
  'use strict';

  // State
  const state = {
    selectedAmount: 10,
    notes: [],
    notesLoaded: false,
    mode: 'donate' // 'donate' or 'testimonial'
  };

  // DOM Elements
  const elements = {
    modal: document.getElementById('donationModal'),
    form: document.getElementById('donationForm'),
    amountBtns: document.querySelectorAll('.amount-btn'),
    customAmount: document.querySelector('.custom-amount'),
    customInput: document.getElementById('customAmount'),
    noteInput: document.getElementById('donorNote'),
    charCount: document.getElementById('noteCharCount'),
    notesContainer: document.getElementById('donationNotes')
  };

  // Initialize
  function init() {
    setupAmountButtons();
    setupNoteCounter();
    setupFormSubmit();
    setupBackdropClose();
    loadDonationNotes();

    // Check for donation success/cancel URL params
    checkDonationStatus();

    // Expose function to open modal
    window.openDonationModal = openModal;

    // Refresh notes periodically
    setInterval(loadDonationNotes, 5 * 60 * 1000);
  }

  // Close modal when clicking outside (on backdrop)
  function setupBackdropClose() {
    if (!elements.modal) return;

    elements.modal.addEventListener('click', (e) => {
      // If click is on the dialog itself (backdrop), close it
      if (e.target === elements.modal) {
        elements.modal.close();
      }
    });
  }

  // Setup amount button selection
  function setupAmountButtons() {
    elements.amountBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        // Remove selection from all
        elements.amountBtns.forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');

        const amount = btn.dataset.amount;

        if (amount === 'custom') {
          elements.customAmount.hidden = false;
          elements.customInput.focus();
          state.selectedAmount = parseFloat(elements.customInput.value) || 10;
        } else {
          elements.customAmount.hidden = true;
          state.selectedAmount = parseFloat(amount);
        }
      });
    });

    // Update state when custom amount changes
    if (elements.customInput) {
      elements.customInput.addEventListener('input', () => {
        state.selectedAmount = parseFloat(elements.customInput.value) || 10;
      });
    }
  }

  // Setup note character counter
  function setupNoteCounter() {
    if (elements.noteInput && elements.charCount) {
      elements.noteInput.addEventListener('input', () => {
        elements.charCount.textContent = elements.noteInput.value.length;
      });
    }
  }

  // Setup form submission
  function setupFormSubmit() {
    if (!elements.form) return;

    elements.form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const email = document.getElementById('donorEmail')?.value;
      const note = document.getElementById('donorNote')?.value;
      const displayNote = document.getElementById('displayNote')?.checked;
      const receiveUpdates = document.getElementById('receiveUpdates')?.checked;

      const submitBtn = elements.form.querySelector('.btn-donate');
      const originalText = submitBtn.textContent;
      submitBtn.textContent = 'Processing...';
      submitBtn.disabled = true;

      try {
        const response = await fetch('/api/donate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            amount: state.selectedAmount,
            email,
            note,
            displayNote,
            receiveUpdates
          })
        });

        const data = await response.json();

        if (data.url) {
          // Redirect to Stripe Checkout
          window.location.href = data.url;
        } else {
          throw new Error(data.error || 'Failed to create checkout session');
        }

      } catch (error) {
        console.error('Donation error:', error);
        submitBtn.textContent = 'Error - Try Again';
        submitBtn.disabled = false;
        setTimeout(() => {
          submitBtn.textContent = originalText;
        }, 3000);
      }
    });
  }

  // Open donation modal with optional mode
  function openModal(mode = 'donate') {
    if (!elements.modal) return;

    state.mode = mode;
    const modalTitle = elements.modal.querySelector('h2');
    const modalSubtitle = elements.modal.querySelector('.modal-subtitle');
    const amountSection = elements.modal.querySelector('.amount-buttons');
    const customSection = elements.modal.querySelector('.custom-amount');
    const submitBtn = elements.modal.querySelector('.btn-donate');

    if (mode === 'testimonial') {
      // Feedback mode - focus on the note, hide amounts
      if (modalTitle) modalTitle.textContent = 'Did it help you?';
      if (modalSubtitle) modalSubtitle.textContent = 'Tell us how this game helped you learn!';
      if (amountSection) amountSection.style.display = 'none';
      if (customSection) customSection.hidden = true;
      if (submitBtn) submitBtn.textContent = 'Share';
      state.selectedAmount = 0;
      // Update the textarea label for feedback mode
      const noteLabel = elements.modal.querySelector('label[for="donorNote"]');
      if (noteLabel) noteLabel.textContent = 'How did it help? (200 chars max)';
    } else {
      // Donate mode - show everything
      if (modalTitle) modalTitle.textContent = 'Support Omarchy Defender';
      if (modalSubtitle) modalSubtitle.textContent = 'Help keep the Gnomes at bay!';
      if (amountSection) amountSection.style.display = '';
      if (submitBtn) submitBtn.textContent = 'Donate';
      state.selectedAmount = 10;
      // Reset the textarea label for donate mode
      const noteLabel = elements.modal.querySelector('label[for="donorNote"]');
      if (noteLabel) noteLabel.textContent = 'Thank-you note (optional, 200 chars max)';
    }

    elements.modal.showModal();
  }

  // Check URL params for donation status
  function checkDonationStatus() {
    const params = new URLSearchParams(window.location.search);

    if (params.has('donated')) {
      // Show thank you message
      showThankYou();
      // Clean URL
      window.history.replaceState({}, '', window.location.pathname);
    }

    if (params.has('cancelled')) {
      // Clean URL
      window.history.replaceState({}, '', window.location.pathname);
    }
  }

  // Show thank you message
  function showThankYou() {
    const thankYou = document.createElement('div');
    thankYou.className = 'thank-you-toast';
    thankYou.innerHTML = `
      <div class="thank-you-content">
        <h3>THANK YOU, COMMANDER!</h3>
        <p>Your support helps keep the Gnomes at bay.</p>
      </div>
    `;
    thankYou.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: #0a0a0a;
      border: 2px solid #00ff41;
      padding: 2rem;
      z-index: 1000;
      text-align: center;
      color: #00ff41;
      font-family: 'Courier New', monospace;
      box-shadow: 0 0 50px rgba(0, 255, 65, 0.3);
      animation: fadeInUp 0.5s ease-out;
    `;

    document.body.appendChild(thankYou);

    setTimeout(() => {
      thankYou.style.opacity = '0';
      thankYou.style.transition = 'opacity 0.5s';
      setTimeout(() => thankYou.remove(), 500);
    }, 4000);
  }

  // Load and display donation notes
  async function loadDonationNotes() {
    if (!elements.notesContainer) return;

    try {
      const response = await fetch('/api/notes');
      const data = await response.json();

      if (data.notes && data.notes.length > 0) {
        state.notes = data.notes;
        displayNotes();
      }

    } catch (error) {
      console.warn('Could not load donation notes:', error);
    }
  }

  // Display sticky notes on screen
  function displayNotes() {
    if (!elements.notesContainer || state.notes.length === 0) return;

    // Clear existing notes
    elements.notesContainer.innerHTML = '';

    // Position notes on left and right sides
    const viewportHeight = window.innerHeight;
    const noteHeight = 120; // Approximate height
    const padding = 100;

    state.notes.forEach((note, index) => {
      const noteEl = document.createElement('div');
      noteEl.className = `sticky-note ${index % 2 === 0 ? 'left' : 'right'}`;

      // Calculate vertical position
      const yPos = padding + (index * (noteHeight + 20)) % (viewportHeight - padding * 2);

      noteEl.style.top = `${yPos}px`;
      noteEl.style.transform = `rotate(${note.rotation}deg)`;

      noteEl.innerHTML = `
        <div class="note-content">${escapeHtml(note.content)}</div>
        <div class="note-amount">$${note.amount}</div>
      `;

      elements.notesContainer.appendChild(noteEl);
    });
  }

  // Escape HTML to prevent XSS
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
