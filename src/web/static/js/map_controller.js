/**
 * Seasonal Map Controller
 * Handles Leaflet initialization, Day/Night rendering, and user interaction.
 */

window.MapController = {
    map: null,
    terminatorLayer: null,
    markerLayer: null,
    
    // State
    currentSubsolar: { lat: 0, lon: 0 },
    selectedLocation: { lat: 48.8566, lon: 2.3522 }, // Default Paris

    init: function() {
        console.log("MapController: Starting...");
        
        // 1. Initialize Leaflet
        // We use a dark theme tile layer for scientific contrast
        this.map = L.map('map', {
            zoomControl: false,
            attributionControl: false,
            minZoom: 2,
            worldCopyJump: true
        }).setView([20, 0], 2);

        // CartoDB Dark Matter Tiles
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            subdomains: 'abcd',
            maxZoom: 19
        }).addTo(this.map);

        // 2. Events
        this.map.on('click', (e) => this.handleMapClick(e));

        // 3. Initial Draw
        this.updateTerminator(); // Fetch initial sun position
        
        // 4. Start Animation Loop (Update sun position every minute)
        setInterval(() => this.updateTerminator(), 60000);
    },

    /**
     * Fetches the rigorous Subsolar point from Python and draws the shade.
     */
    updateTerminator: async function() {
        const nowIso = new Date().toISOString();
        
        try {
            const response = await fetch('/api/subsolar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ datetime_str: nowIso })
            });
            const data = await response.json();
            
            this.currentSubsolar = { lat: data.lat, lon: data.lon };
            this.drawTerminator(data.lat, data.lon);
            
        } catch (err) {
            console.error("Failed to update solar position:", err);
        }
    },

    /**
     * Draws the Night Polygon based on the subsolar point.
     * We calculate the circle 90 degrees away from the sun.
     */
    drawTerminator: function(sunLat, sunLon) {
        if (this.terminatorLayer) {
            this.map.removeLayer(this.terminatorLayer);
        }

        // Generate polygon coordinates (Math heavy, but standard for day/night)
        const coordinates = this.computeTerminatorPath(sunLat, sunLon);
        
        // Create a polygon that covers the whole world...
        // ...with a "hole" where it is day? Or just polygon for night?
        // Simpler: Compute the "Night" polygon.
        
        this.terminatorLayer = L.polygon(coordinates, {
            color: 'transparent',
            fillColor: '#000',
            fillOpacity: 0.4, // Shadow intensity
            interactive: false
        }).addTo(this.map);
    },

    /**
     * Handles user clicking the map -> Select location.
     */
    handleMapClick: function(e) {
        const lat = e.latlng.lat;
        const lon = e.latlng.lng;
        
        this.selectedLocation = { lat, lon };
        
        // 1. Update UI Text
        document.getElementById('loc-lat').innerText = lat.toFixed(4) + "° N";
        document.getElementById('loc-lon').innerText = lon.toFixed(4) + "° E";
        document.getElementById('loc-name').innerText = "Selected Location";
        
        // 2. Update Marker
        if (this.markerLayer) this.map.removeLayer(this.markerLayer);
        this.markerLayer = L.marker([lat, lon]).addTo(this.map);

        // 3. Trigger Widget Updates (Clock, DayBar) via the global Widgets controller
        if (window.Widgets) {
            window.Widgets.updateLocation(lat, lon);
            // Prompt to open analysis?
            // setTimeout(() => window.Widgets.openAnalysisModal(lat, lon), 500);
        }
    },
    
    // --- Math Helper for Terminator ---
    computeTerminatorPath: function(sunLat, sunLon) {
        // Simple approximation of the great circle 90 degrees from sun
        // Returns lat/lon array for Leaflet
        const path = [];
        const R2D = 180 / Math.PI;
        const D2R = Math.PI / 180;
        
        const sunPhi = sunLat * D2R;
        const sunLambda = sunLon * D2R;
        
        // We step 360 degrees around the longitude
        for (let i = 0; i <= 360; i += 2) {
            const lambda = (i - 180) * D2R;
            
            // Spherical trig to find latitude of the terminator at this longitude
            // tan(phi) = -1 / (tan(sunPhi) * cos(lambda - sunLambda))
            // Actually: cos(arc) = sin(sunPhi)sin(phi) + cos(sunPhi)cos(phi)cos(delta_lon) = 0
            // tan(phi) = - cot(sunPhi) * cos(lambda - sunLambda)
            
            let phi = Math.atan(-1 / Math.tan(sunPhi) * Math.cos(lambda - sunLambda));
            
            path.push([phi * R2D, (i - 180)]);
        }
        
        // To make a valid polygon for "Night", we need to close it around the anti-sun pole
        // If sun is North, night is South pole.
        const antiSunLat = (sunLat > 0) ? -90 : 90;
        path.push([antiSunLat, 180]);
        path.push([antiSunLat, -180]);
        
        return path;
    }
};