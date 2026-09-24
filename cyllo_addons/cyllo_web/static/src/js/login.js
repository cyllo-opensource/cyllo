/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";


const MAX_TOASTS = 2;

/**
 * Show a toast notification on the login page.
 * - Max MAX_TOASTS visible at once; oldest is evicted when cap is exceeded.
 * - Duplicate messages shake & reset the timer instead of stacking.
 * @param {string} message  - text to display
 * @param {string} type     - 'error' | 'success' | 'warning'
 * @param {number} duration - ms before auto-dismiss (default 3500)
 */
function showToast(message, type = 'error', duration = 3500) {
    const container = document.getElementById('cy-toast-container');
    if (!container) return;

    // --- Deduplicate: same message already visible? shake + reset timer ---
    const existing = [...container.querySelectorAll('.cy-toast')].find(
        t => t.querySelector('.cy-toast__msg')?.textContent === message
    );
    if (existing) {
        clearTimeout(existing._dismissTimer);
        existing.classList.add('cy-toast--shake');
        existing.addEventListener('animationend', () =>
            existing.classList.remove('cy-toast--shake'), { once: true });
        existing._dismissTimer = setTimeout(() => dismissToast(existing), duration);
        return;
    }

    // --- Cap: evict oldest toast when limit is exceeded ---
    const current = container.querySelectorAll('.cy-toast');
    if (current.length >= MAX_TOASTS) {
        dismissToast(current[0]);
    }

    const iconMap = { error: '<i class="ri-error-warning-line"></i>', success: '<i class="ri-checkbox-circle-line"></i>', warning: '<i class="ri-alert-line"></i>' };

    const toast = document.createElement('div');
    toast.className = `cy-toast cy-toast--${type}`;
    toast.innerHTML = `
        <span class="cy-toast__icon">${iconMap[type] || '<i class="ri-information-line"></i>'}</span>
        <span class="cy-toast__msg">${message}</span>
        <button class="cy-toast__close" aria-label="Close">✕</button>
    `;

    toast.querySelector('.cy-toast__close').addEventListener('click', () => dismissToast(toast));
    container.appendChild(toast);

    // Trigger enter animation
    requestAnimationFrame(() => toast.classList.add('cy-toast--visible'));

    // Auto-dismiss
    toast._dismissTimer = setTimeout(() => dismissToast(toast), duration);
}

function dismissToast(toast) {
    clearTimeout(toast._dismissTimer);
    toast.classList.remove('cy-toast--visible');
    toast.addEventListener('transitionend', () => toast.remove(), { once: true });
}


publicWidget.registry.LoginBehavior = publicWidget.Widget.extend({
    selector: '.cy-instance-login',
    events: {
        'click #continue_button': '_onContinueButtonClick',
    },

    start: function () {
        this._super.apply(this, arguments);
        const self = this;
        this.isAlreadyLoggedIn = this.el.dataset.alreadyLoggedIn === '1';
        const $emailInput = this.$('#login');

        if (this.isAlreadyLoggedIn) {
            $emailInput.attr('disabled', true);
            showToast('You are already logged in. Please log out before logging in again.', 'warning');
        }

        // Show server-side auth error (wrong password) as a toast on page load
        const serverError = document.getElementById('cy-server-error');
        if (serverError && !this.isAlreadyLoggedIn) {
            const msg = serverError.textContent.trim() || 'Invalid username or password';
            showToast(msg, 'error');
        }

        document.getElementById("login").addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                if (self.isAlreadyLoggedIn) {
                    return;
                }
                self._onContinueButtonClick(event);
            }
        });
    },

    _onContinueButtonClick: function (ev) {
        ev.preventDefault();

        if (this.isAlreadyLoggedIn) {
            showToast('You are already logged in. Please log out before logging in again.', 'warning');
            return;
        }

        const $continueButton = this.$('#continue_button');
        const $emailInput = this.$('#login');
        const $passwordGroup = this.$('#password_group');
        const $loginButton = this.$('#login_button');

        const email = $emailInput.val().trim();

        if (!email) {
            showToast('Email is required', 'error');
            $emailInput.addClass('cy-input--error').focus();
            return;
        }

        $passwordGroup.addClass('fade-in');
        $loginButton.removeClass('cy-hidden');
        $continueButton.addClass('cy-hidden');
        this.$('#password').focus();
    }

});

publicWidget.registry.Signup = publicWidget.Widget.extend({

    selector: '.cy-instance-signup',
    events: {
        'click #signup_button': '_onButtonClick',
    },

    start: function () {
        this._super.apply(this, arguments);

        // Show server-side auth error as a toast on page load
        const serverError = document.getElementById('cy-server-error');
        if (serverError) {
            const msg = serverError.textContent.trim();
            if (msg) {
                showToast(msg, 'error');
            }
        }
    },

    _onButtonClick: function (ev) {
        ev.preventDefault();

        const $emailInput = this.$('#login');
        const $nameInput = this.$('#name');
        const $passwordInput = this.$('#password');
        const $confirmPasswordInput = this.$('#confirm_password');
        const $errorDisplay = this.$('.cy-password-error');

        const email = $emailInput.val() ? $emailInput.val().trim() : '';
        const name = $nameInput.val() ? $nameInput.val().trim() : '';
        const password = $passwordInput.val() || '';
        const confirm_password = $confirmPasswordInput.val() || '';

        $errorDisplay.text('').removeClass('cy-input-error').hide();
        this.$('.cy-input').removeClass('cy-input--error');

        if (!email) {
            showToast('Email is required', 'error');
            $emailInput.addClass('cy-input--error').focus();
            return;
        }

        if (!name) {
            showToast('Name is required', 'error');
            $nameInput.addClass('cy-input--error').focus();
            return;
        }

        if (!password) {
            showToast('Password is required', 'error');
            $passwordInput.addClass('cy-input--error').focus();
            return;
        }

        if (password !== confirm_password) {
            showToast('Passwords do not match', 'error');
            $confirmPasswordInput.addClass('cy-input--error').focus();
            return;
        }

        const form = this.$('form[role="form"]')[0];
        if (form) {
            form.submit();
        }
    }

});

publicWidget.registry.ResetPassword = publicWidget.Widget.extend({

    selector: '.cy-instance-reset-password',
    events: {
        'click #reset_password_button': '_onButtonClick',
    },

    start: function () {
        this._super.apply(this, arguments);
        const $loginInput = this.$('#login');

        const serverError = document.getElementById('cy-server-error');
        if (serverError) {
            const msg = serverError.textContent.trim();
            if (msg) {
                $loginInput.addClass('cy-input--error').focus();
                showToast(msg, 'error');
            }
        }
    },

    _onButtonClick: function (ev) {
        ev.preventDefault();

        const $loginInput = this.$('#login');
        if ($loginInput.length) {
            const login = $loginInput.val() ? $loginInput.val().trim() : '';
            if (!login) {
                showToast('Email is required', 'error');
                $loginInput.addClass('cy-input--error').focus();
                return;
            }
        }

        const form = this.$('form[role="form"]')[0];
        if (form) {
            form.submit();
        }
    }

});
