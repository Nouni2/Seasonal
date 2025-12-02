/**
 * Seasonal Widgets Controller
 * Handles Clock, Ephemeris, Day/Night Bar, and Analysis Plotting.
 */

window.Widgets = {
    // Current State
    lat: 48.8566,
    lon: 2.3522,
    timer: null,

    init: function() {
        console.log("Widgets: Starting...");
        
        // 1. Setup Listeners
        document.getElementById('btn-now').addEventListener('click', () => this.resetTime());
        document.getElementById('btn-run-analysis').addEventListener('click', () => this.runAnalysis());
        document.getElementById('btn-close-modal').addEventListener('click', () => {
             document.getElementById('analysis-modal').classList.add('hidden');
        });
        
        // Open modal on click of location name (optional feature)
        document.getElementById('loc-name').addEventListener('click', () => this.openAnalysisModal());

        // 2. Start Clock Loop
        this.updateClock(); // Immediate
        setInterval(() => this.updateClock(), 1000); // Every second
        
        // 3. Initial Data Fetch
        this.updateLocation(this.lat, this.lon);
    },

    /**
     * Called when map is clicked. Updates all local data.
     */
    updateLocation: function(lat, lon) {
        this.lat = lat;
        this.lon = lon;
        this.fetchDayEvents();
        this.updateEphemeris(); // Immediate update
    },

    /**
     * Updates the digital clock and fetches Ephemeris (Alt/Az).
     */
    updateClock: function() {
        const now = new Date();
        const iso = now.toISOString();
        
        // Update Text
        const timeStr = iso.split('T')[1].split('.')[0] + " UTC";
        document.getElementById('utc-clock').innerText = timeStr;
        document.getElementById('date-display').innerText = iso.split('T')[0];
        
        // Fetch Ephemeris (Throttle this? Maybe every 5 seconds is enough, but 1s is cool)
        // For smoothness, we can optimize later.
        this.updateEphemeris(iso);
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
            
        } catch (e) {
            console.error(e);
        }
    },

    /**
     * Fetches Sunrise/Sunset/Day Length for the 24h Bar.
     */
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
            
            // Update Text
            document.getElementById('txt-sunrise').innerHTML = `<i class="fa-solid fa-sunrise"></i> ${data.sunrise_utc || '--:--'}`;
            document.getElementById('txt-sunset').innerHTML = `<i class="fa-solid fa-sunset"></i> ${data.sunset_utc || '--:--'}`;
            document.getElementById('txt-duration').innerText = data.duration_hours.toFixed(2) + "h";
            
            // Draw Bar
            this.renderDayBar(data);

        } catch (e) {
            console.error("Day Events Error", e);
        }
    },

    renderDayBar: function(data) {
        const container = document.getElementById('day-bar');
        container.innerHTML = ''; // Clear
        
        if (data.day_type === 'POLAR_DAY') {
            container.innerHTML = '<div class="segment day" style="width: 100%"></div>';
            return;
        }
        if (data.day_type === 'POLAR_NIGHT') {
             container.innerHTML = '<div class="segment night" style="width: 100%"></div>';
             return;
        }
        
        // Normal Day
        // Parse "HH:MM:SS" into decimal hours
        const parseH = (s) => {
            const p = s.split(':');
            return parseInt(p[0]) + parseInt(p[1])/60;
        };
        
        const rise = parseH(data.sunrise_utc);
        const set = parseH(data.sunset_utc);
        
        // Logic for converting time to % width
        // Case: Rise < Set (Normal day inside 24h)
        if (rise < set) {
            const startPct = (rise / 24) * 100;
            const widthPct = ((set - rise) / 24) * 100;
            
            const seg = document.createElement('div');
            seg.className = 'segment day';
            seg.style.left = startPct + '%';
            seg.style.width = widthPct + '%';
            container.appendChild(seg);
        }
        // Handle wrapping (Day crosses midnight) if necessary, 
        // but current solver returns discrete day events.
    },

    /**
     * Opens modal and triggers Plotly.
     */
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
        
        document.getElementById('analysis-plot').innerHTML = "Computing Physics...";
        
        const res = await fetch('/api/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(req)
        });
        const data = await res.json();
        
        // Plotly
        const xData = data.map(d => d.date);
        const yData = data.map(d => d.hours);
        
        Plotly.newPlot('analysis-plot', [{
            x: xData,
            y: yData,
            type: 'scatter',
            mode: 'lines',
            line: {color: '#ffca28', width: 3}
        }], {
            margin: { t: 20, r: 20, l: 40, b: 40 },
            paper_bgcolor: '#111',
            plot_bgcolor: '#111',
            font: { color: '#aaa' },
            xaxis: { gridcolor: '#333' },
            yaxis: { gridcolor: '#333', title: 'Day Length (Hours)' }
        });
    },
    
    resetTime: function() {
        // Logic to reset date picker to now
    }
};