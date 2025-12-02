/**
 * Seasonal Widgets Controller
 * Handles Clock, Ephemeris, Day/Night Bar, Analysis Plotting, and View Switching.
 */

window.Widgets = {
    // Current State
    lat: 48.8566,
    lon: 2.3522,
    currentView: '2D', // '2D' or '3D'
    subsolar: { lat: 0, lon: 0 }, // Store solar position for 3D engine

    init: function() {
        console.log("Widgets: Starting...");
        
        // 1. Setup Listeners
        document.getElementById('btn-now').addEventListener('click', () => this.resetTime());
        document.getElementById('btn-run-analysis').addEventListener('click', () => this.runAnalysis());
        document.getElementById('btn-close-modal').addEventListener('click', () => {
             document.getElementById('analysis-modal').classList.add('hidden');
        });
        
        // View Toggle
        document.getElementById('btn-view-toggle').addEventListener('click', () => this.toggleView());

        // Location Click
        document.getElementById('loc-name').addEventListener('click', () => this.openAnalysisModal());

        // 2. Start Clock Loop
        this.updateClock(); 
        setInterval(() => this.updateClock(), 1000); 
        
        // 3. Initial Data
        this.updateLocation(this.lat, this.lon);
        this.fetchSubsolar(); // Need this for 3D lighting immediately
    },

    /**
     * Switches between Leaflet (Map) and Three.js (Globe).
     */
    toggleView: async function() {
        const btn = document.getElementById('btn-view-toggle');
        const loader = document.getElementById('view-loader');
        const mapDiv = document.getElementById('map');
        const globeDiv = document.getElementById('globe-container');

        // 1. Show Loader
        loader.classList.remove('hidden');
        
        // Fake delay to allow loader to render and engine to initialize
        await new Promise(r => setTimeout(r, 600));

        if (this.currentView === '2D') {
            // SWITCH TO 3D
            this.currentView = '3D';
            btn.innerHTML = '<i class="fa-solid fa-map"></i> Switch to 2D View';
            
            // Init Engine
            if (window.GlobeController) {
                window.GlobeController.init();
                // Update Sun Light
                await this.fetchSubsolar(); 
                window.GlobeController.updateSunPosition(this.subsolar.lat, this.subsolar.lon);
                // Fly Camera
                window.GlobeController.flyTo(this.lat, this.lon);
            }
            
            mapDiv.classList.add('hidden');
            globeDiv.classList.remove('hidden');

        } else {
            // SWITCH TO 2D
            this.currentView = '2D';
            btn.innerHTML = '<i class="fa-solid fa-earth-americas"></i> Switch to 3D View';
            
            globeDiv.classList.add('hidden');
            mapDiv.classList.remove('hidden');
            
            // Re-center Leaflet just in case
            if (window.MapController && window.MapController.map) {
                window.MapController.map.invalidateSize();
                window.MapController.map.setView([this.lat, this.lon]);
            }
        }

        // Hide Loader
        loader.classList.add('hidden');
    },

    // --- Standard Methods (Clock, Data) ---

    updateLocation: function(lat, lon) {
        this.lat = lat;
        this.lon = lon;
        this.fetchDayEvents();
        this.updateEphemeris();
        
        // If in 3D mode, move the earth
        if (this.currentView === '3D' && window.GlobeController) {
            window.GlobeController.flyTo(lat, lon);
        }
    },

    fetchSubsolar: async function() {
        // We need this data for the 3D Sun Vector
        try {
            const nowIso = new Date().toISOString();
            const res = await fetch('/api/subsolar', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ datetime_str: nowIso })
            });
            const data = await res.json();
            this.subsolar = { lat: data.lat, lon: data.lon };
        } catch (e) { console.error(e); }
    },

    updateClock: function() {
        const now = new Date();
        const iso = now.toISOString();
        
        const timeStr = iso.split('T')[1].split('.')[0] + " UTC";
        document.getElementById('utc-clock').innerHTML = `
            ${timeStr} 
            <span style="font-size:0.5em; color:#888; display:block; margin-top:4px;">
                ${this.estimateLocalTime(now)} (Local Mean)
            </span>
        `;
        document.getElementById('date-display').innerText = iso.split('T')[0];
        
        // Update physics
        this.updateEphemeris(iso);
        
        // If 3D, keep sun updated
        if (this.currentView === '3D' && now.getSeconds() === 0) {
            this.fetchSubsolar().then(() => {
                if(window.GlobeController) 
                    window.GlobeController.updateSunPosition(this.subsolar.lat, this.subsolar.lon);
            });
        }
    },

    estimateLocalTime: function(dateObj) {
        const offsetHours = this.lon / 15.0;
        const utcMs = dateObj.getTime() + (dateObj.getTimezoneOffset() * 60000);
        const localMs = utcMs + (offsetHours * 3600000);
        const localDate = new Date(localMs);
        const h = localDate.getHours().toString().padStart(2, '0');
        const m = localDate.getMinutes().toString().padStart(2, '0');
        return `~${h}:${m}`;
    },

    updateEphemeris: async function(isoStr) {
        if (!isoStr) isoStr = new Date().toISOString();
        try {
            const res = await fetch('/api/ephemeris', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    lat: this.lat, lon: this.lon, datetime_str: isoStr
                })
            });
            const data = await res.json();
            document.getElementById('val-alt').innerText = data.altitude.toFixed(2) + "°";
            document.getElementById('val-az').innerText = data.azimuth.toFixed(2) + "°";
        } catch (e) { console.error(e); }
    },

    fetchDayEvents: async function() {
        const isoStr = new Date().toISOString();
        const bar = document.getElementById('day-bar');
        bar.innerHTML = '<div class="loading-bar"></div>';
        try {
            const res = await fetch('/api/day-events', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    lat: this.lat, lon: this.lon, datetime_str: isoStr
                })
            });
            const data = await res.json();
            document.getElementById('txt-sunrise').innerHTML = `<i class="fa-solid fa-sunrise"></i> ${data.sunrise_utc || '--:--'}`;
            document.getElementById('txt-sunset').innerHTML = `<i class="fa-solid fa-sunset"></i> ${data.sunset_utc || '--:--'}`;
            document.getElementById('txt-duration').innerText = data.duration_hours.toFixed(2) + "h";
            this.renderDayBar(data);
        } catch (e) { console.error("Day Events Error", e); }
    },

    renderDayBar: function(data) {
        const container = document.getElementById('day-bar');
        container.innerHTML = ''; 
        if (data.day_type === 'POLAR_DAY') {
            container.innerHTML = '<div class="segment day" style="width: 100%"></div>';
            return;
        }
        if (data.day_type === 'POLAR_NIGHT') {
             container.innerHTML = '<div class="segment night" style="width: 100%"></div>';
             return;
        }
        const parseH = (s) => {
            if (!s) return 0;
            const p = s.split(':');
            return parseInt(p[0]) + parseInt(p[1])/60;
        };
        const rise = parseH(data.sunrise_utc);
        const set = parseH(data.sunset_utc);
        const createSeg = (start, width) => {
            const seg = document.createElement('div');
            seg.className = 'segment day';
            seg.style.left = (start / 24 * 100) + '%';
            seg.style.width = (width / 24 * 100) + '%';
            container.appendChild(seg);
        };
        if (rise < set) {
            createSeg(rise, set - rise);
        } else {
            createSeg(0, set);
            createSeg(rise, 24 - rise);
        }
    },

    openAnalysisModal: function() {
        document.getElementById('analysis-modal').classList.remove('hidden');
        document.getElementById('modal-loc-name').innerText = `${this.lat.toFixed(2)}, ${this.lon.toFixed(2)}`;
    },

    runAnalysis: async function() {
        const days = document.getElementById('analysis-range').value;
        const now = new Date();
        const end = new Date();
        end.setDate(now.getDate() + parseInt(days));
        const req = {
            lat: this.lat, lon: this.lon,
            start_date: now.toISOString().split('T')[0],
            end_date: end.toISOString().split('T')[0]
        };
        document.getElementById('analysis-plot').innerHTML = '<div style="display:flex; height:100%; align-items:center; justify-content:center;">Computing Physics...</div>';
        const res = await fetch('/api/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(req)
        });
        const data = await res.json();
        const xData = data.map(d => d.date);
        const yData = data.map(d => d.hours);
        Plotly.newPlot('analysis-plot', [{
            x: xData,
            y: yData,
            type: 'scatter',
            mode: 'lines',
            line: {color: '#ffca28', width: 3},
            fill: 'tozeroy',
            fillcolor: 'rgba(255, 202, 40, 0.1)'
        }], {
            margin: { t: 20, r: 20, l: 40, b: 40 },
            paper_bgcolor: '#1a1a20',
            plot_bgcolor: '#1a1a20',
            font: { color: '#aaa', family: 'Inter' },
            xaxis: { gridcolor: '#333', showgrid: true },
            yaxis: { gridcolor: '#333', title: 'Day Length (Hours)', showgrid: true }
        });
    },
    
    resetTime: function() {
        const now = new Date();
        const datePicker = document.getElementById('date-picker');
        if (datePicker) {
            datePicker.value = now.toISOString().split('T')[0];
        }
        this.updateClock();
        this.fetchDayEvents();
    }
};