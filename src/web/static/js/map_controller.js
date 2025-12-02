/**
 * Seasonal Map Controller
 * Handles Leaflet initialization, Day/Night rendering, and user interaction.
 */

window.MapController = {
    map: null,
    terminatorLayer: null, // Now a LayerGroup instead of a Polygon
    markerLayer: null,
    
    // State
    currentSubsolar: { lat: 0, lon: 0 },
    selectedLocation: { lat: 48.8566, lon: 2.3522 }, // Default Paris

    init: function() {
        console.log("MapController: Starting...");
        
        // 1. Initialize Leaflet
        // CartoDB Dark Matter tiles look best for this sci-fi aesthetic
        this.map = L.map('map', {
            zoomControl: false,
            attributionControl: false,
            minZoom: 2,
            maxBounds: [[-90, -360], [90, 360]], // Allow panning across copies
            worldCopyJump: false // We handle wrapping manually via ghost polygons
        }).setView([20, 0], 2);

        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            subdomains: 'abcd',
            maxZoom: 19
        }).addTo(this.map);

        // 2. Events
        this.map.on('click', (e) => this.handleMapClick(e));

        // 3. Initial Draw
        this.updateTerminator(); 
        
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
     * Uses the Great Circle equation projected to Mercator.
     * Draws 3 copies (Center, Left, Right) to support infinite panning.
     */
    drawTerminator: function(sunLat, sunLon) {
        if (this.terminatorLayer) {
            this.map.removeLayer(this.terminatorLayer);
        }

        // 1. Compute the sine wave for the terminator line
        // We generate the path for the MAIN world (-180 to 180)
        const mainPath = this.computeTerminatorPath(sunLat, sunLon);
        
        // 2. Define the "Night" Polygon Closure
        // If Sun is North (Summer), Night is South -> Close via Bottom
        // If Sun is South (Winter), Night is North -> Close via Top
        const closureLat = (sunLat >= 0) ? -90 : 90;
        
        // Add "closing" points to wrap the polygon around the dark pole
        // We clone the path to avoid reference issues when shifting later
        const centerCoords = [...mainPath];
        centerCoords.push([closureLat, 180]);
        centerCoords.push([closureLat, -180]);

        // 3. Create Ghost Polygons (Shift Longitude by +/- 360)
        // This ensures the shadow exists when the user pans to the repeated world
        const leftCoords = centerCoords.map(pt => [pt[0], pt[1] - 360]);
        const rightCoords = centerCoords.map(pt => [pt[0], pt[1] + 360]);

        // 4. Style Options
        const polyStyle = {
            color: 'transparent',    // No border line
            fillColor: '#000',       // Pure Black
            fillOpacity: 0.65,       // Stronger shadow for contrast
            interactive: false,
            smoothFactor: 1.0
        };

        // 5. Group and Add to Map
        const centerPoly = L.polygon(centerCoords, polyStyle);
        const leftPoly = L.polygon(leftCoords, polyStyle);
        const rightPoly = L.polygon(rightCoords, polyStyle);

        this.terminatorLayer = L.layerGroup([centerPoly, leftPoly, rightPoly]).addTo(this.map);
    },

    /**
     * Math Logic: Calculates the Latitude of the terminator for every degree of Longitude.
     * Formula: tan(lat) = - cos(lon - sunLon) * cot(sunLat)
     */
    computeTerminatorPath: function(sunLat, sunLon) {
        const path = [];
        const D2R = Math.PI / 180;
        const R2D = 180 / Math.PI;

        // Avoid division by zero at equinoxes (sunLat = 0)
        const effectiveSunLat = (Math.abs(sunLat) < 0.1) ? (sunLat >= 0 ? 0.1 : -0.1) : sunLat;
        const sunPhi = effectiveSunLat * D2R;
        const tanSunPhi = Math.tan(sunPhi);

        // Iterate across the map width (-180 to 180)
        for (let i = -180; i <= 180; i++) {
            const lon = i;
            const lambda = lon * D2R;
            const sunLambda = sunLon * D2R;

            const deltaLambda = lambda - sunLambda;
            
            // tan(lat) = - cos(deltaLambda) / tan(sunLat)
            let tanLat = -Math.cos(deltaLambda) / tanSunPhi;
            
            // ArcTan to get latitude
            let lat = Math.atan(tanLat) * R2D;
            
            path.push([lat, lon]);
        }
        return path;
    },

    /**
     * Handles user clicking the map -> Select location.
     */
    handleMapClick: function(e) {
        // Wrap longitude to -180/180 standard for API calls
        let lon = e.latlng.lng;
        while (lon > 180) lon -= 360;
        while (lon < -180) lon += 360;
        
        const lat = e.latlng.lat;
        
        this.selectedLocation = { lat, lon };
        
        // 1. Update UI Text
        document.getElementById('loc-lat').innerText = lat.toFixed(4) + "° N";
        document.getElementById('loc-lon').innerText = lon.toFixed(4) + "° E";
        document.getElementById('loc-name').innerText = "Selected Location";
        
        // 2. Update Marker
        if (this.markerLayer) this.map.removeLayer(this.markerLayer);
        this.markerLayer = L.marker([lat, lon]).addTo(this.map);
        
        // 3. Bind Popup with Analysis Button
        // [Image of popup modal with charts]
        const popupContent = `
            <div style="text-align:center; font-family: 'Inter', sans-serif; color:#333;">
                <b>Coordinates</b><br>
                ${lat.toFixed(4)}, ${lon.toFixed(4)}<br>
                <button onclick="window.Widgets.openAnalysisModal()" 
                    style="margin-top:8px; background:#ffca28; color:#000; border:none; padding:6px 10px; border-radius:4px; cursor:pointer; font-weight:bold;">
                    <i class="fa-solid fa-chart-line"></i> Analyze Sun Path
                </button>
            </div>
        `;
        
        this.markerLayer.bindPopup(popupContent).openPopup();

        // 4. Trigger Widget Updates
        if (window.Widgets) {
            window.Widgets.updateLocation(lat, lon);
        }
    }
};