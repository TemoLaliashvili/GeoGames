document.addEventListener('DOMContentLoaded', function() {

    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'csrf_token';
        input.value = csrfToken;
        form.appendChild(input);
    });

    const ratingStars = document.querySelectorAll('.rating-star');
    if (ratingStars) {
        ratingStars.forEach(star => {
            star.addEventListener('click', function() {
                const rating = this.dataset.rating;
                document.getElementById('score').value = rating;

                ratingStars.forEach(s => {
                    if (s.dataset.rating <= rating) {
                        s.classList.add('text-warning');
                        s.classList.add('bi-star-fill');
                        s.classList.remove('bi-star');
                    } else {
                        s.classList.remove('text-warning');
                        s.classList.remove('bi-star-fill');
                        s.classList.add('bi-star');
                    }
                });
            });
        });
    }

    const avatarInput = document.getElementById('avatar');
    if (avatarInput) {
        const avatarPreview = document.getElementById('avatar-preview');
        avatarInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    avatarPreview.src = event.target.result;
                }
                reader.readAsDataURL(file);
            }
        });
    }
});

function setRating(star) {
    const rating = star.dataset.rating;
    document.getElementById('score-field').value = rating;

    const stars = document.querySelectorAll('.rating-stars i');
    stars.forEach(s => {
        if (s.dataset.rating <= rating) {
            s.classList.add('text-warning');
            s.classList.add('bi-star-fill');
            s.classList.remove('bi-star');
        } else {
            s.classList.remove('text-warning');
            s.classList.remove('bi-star-fill');
            s.classList.add('bi-star');
        }
    });
}
