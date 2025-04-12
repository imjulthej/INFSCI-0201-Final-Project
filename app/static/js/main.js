document.addEventListener('DOMContentLoaded', function() {
    // Initialize date pickers
    const dateInputs = document.querySelectorAll('input[type="datetime-local"]');
    dateInputs.forEach(input => {
        if (!input.value) {
            const now = new Date();
            const timezoneOffset = now.getTimezoneOffset() * 60000;
            const localISOTime = (new Date(now - timezoneOffset)).toISOString().slice(0, 16);
            input.value = localISOTime;
        }
    });

    // Handle map initialization for event pages
    if (document.getElementById('map')) {
        initEventMap();
    }

    // Handle form submissions with AJAX where needed
    document.querySelectorAll('form.ajax-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            fetch(this.action, {
                method: this.method,
                body: formData,
                headers: {
                    'Accept': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Handle success
                    alert(data.message);
                    if (data.redirect) {
                        window.location.href = data.redirect;
                    }
                } else {
                    // Handle error
                    alert(data.error || 'An error occurred');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while processing your request');
            });
        });
    });
});

function initEventMap() {
    const mapElement = document.getElementById('map');
    const lat = parseFloat(mapElement.dataset.lat);
    const lng = parseFloat(mapElement.dataset.lng);
    const location = mapElement.dataset.location;
    
    if (lat && lng) {
        const map = L.map('map').setView([lat, lng], 15);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
        
        L.marker([lat, lng]).addTo(map)
            .bindPopup(location)
            .openPopup();
    } else if (location) {
        // Geocode the address if coordinates aren't available
        fetch(`https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(location)}&key=${mapElement.dataset.apiKey}`)
            .then(response => response.json())
            .then(data => {
                if (data.results && data.results.length > 0) {
                    const location = data.results[0].geometry.location;
                    const map = L.map('map').setView([location.lat, location.lng], 15);
                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    }).addTo(map);
                    
                    L.marker([location.lat, location.lng]).addTo(map)
                        .bindPopup(location)
                        .openPopup();
                }
            });
    }
}

// Export calendar event
function exportCalendar(eventId, service) {
    fetch(`/events/${eventId}/export/${service}`)
        .then(response => {
            if (service === 'apple') {
                return response.blob();
            }
            window.location.href = response.url;
        })
        .then(blob => {
            if (service === 'apple') {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `event-${eventId}.ics`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
            }
        });
}