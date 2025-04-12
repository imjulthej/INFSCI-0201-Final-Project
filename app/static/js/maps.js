// Initialize all maps on the page
function initAllMaps() {
    document.querySelectorAll('.event-map').forEach(mapContainer => {
        const lat = parseFloat(mapContainer.dataset.lat);
        const lng = parseFloat(mapContainer.dataset.lng);
        const location = mapContainer.dataset.location;
        
        if (lat && lng) {
            const map = L.map(mapContainer).setView([lat, lng], 15);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);
            
            L.marker([lat, lng]).addTo(map)
                .bindPopup(location)
                .openPopup();
        }
    });
}

// Geocode an address and return coordinates
async function geocodeAddress(address) {
    try {
        const response = await fetch(`https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(address)}&key=${window.GOOGLE_MAPS_API_KEY}`);
        const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            return {
                lat: data.results[0].geometry.location.lat,
                lng: data.results[0].geometry.location.lng
            };
        }
        return null;
    } catch (error) {
        console.error('Geocoding error:', error);
        return null;
    }
}

// Initialize event creation map
function initEventCreationMap() {
    const mapElement = document.getElementById('event-map');
    if (!mapElement) return;
    
    const initialLat = parseFloat(mapElement.dataset.lat) || 0;
    const initialLng = parseFloat(mapElement.dataset.lng) || 0;
    
    const map = L.map('event-map').setView([initialLat, initialLng], initialLat && initialLng ? 15 : 2);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    let marker = null;
    
    if (initialLat && initialLng) {
        marker = L.marker([initialLat, initialLng]).addTo(map);
    }
    
    // Update location fields when map is clicked
    map.on('click', function(e) {
        if (marker) {
            map.removeLayer(marker);
        }
        
        marker = L.marker(e.latlng).addTo(map);
        document.getElementById('latitude').value = e.latlng.lat;
        document.getElementById('longitude').value = e.latlng.lng;
    });
    
    // Geocode address when location field changes
    document.getElementById('location').addEventListener('change', async function() {
        const address = this.value;
        if (!address) return;
        
        const coords = await geocodeAddress(address);
        if (coords) {
            map.setView([coords.lat, coords.lng], 15);
            
            if (marker) {
                map.removeLayer(marker);
            }
            
            marker = L.marker([coords.lat, coords.lng]).addTo(map);
            document.getElementById('latitude').value = coords.lat;
            document.getElementById('longitude').value = coords.lng;
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    initAllMaps();
    
    if (document.getElementById('event-map')) {
        initEventCreationMap();
    }
});