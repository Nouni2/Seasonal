/**
 * Seasonal Globe Controller
 * Handles 3D Earth rendering, OrbitControls, and Raycasting for location selection.
 */

window.GlobeController = {
    initialized: false,
    scene: null,
    camera: null,
    renderer: null,
    controls: null, // OrbitControls
    raycaster: null,
    mouse: null,
    
    earthGroup: null, 
    earthMesh: null, // We need direct access to mesh for raycasting
    cloudMesh: null, // [NEW] Cloud layer
    sunLight: null,
    
    // Config
    radius: 5,
    
    init: function() {
        if (this.initialized) return;
        console.log("GlobeController: Initializing 3D Engine...");
        
        const container = document.getElementById('globe-container');
        const w = window.innerWidth;
        const h = window.innerHeight;

        // 1. Scene & Camera
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 1000);
        this.camera.position.z = 18; 

        // 2. Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        this.renderer.setSize(w, h);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        
        // Tone mapping for realistic lighting
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.outputEncoding = THREE.sRGBEncoding;
        
        container.appendChild(this.renderer.domElement);

        // 3. Orbit Controls (Interaction)
        if (THREE.OrbitControls) {
            this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
            this.controls.enableDamping = true;
            this.controls.dampingFactor = 0.05;
            this.controls.rotateSpeed = 0.5;
            this.controls.enablePan = false;
            this.controls.minDistance = 6;
            this.controls.maxDistance = 50;
        } else {
            console.error("OrbitControls not loaded!");
        }

        // 4. Raycaster (Click Detection)
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        
        let downPos = { x: 0, y: 0 };
        container.addEventListener('pointerdown', (e) => {
            downPos.x = e.clientX;
            downPos.y = e.clientY;
        });
        container.addEventListener('pointerup', (e) => {
            if (Math.abs(e.clientX - downPos.x) < 5 && Math.abs(e.clientY - downPos.y) < 5) {
                this.onGlobeClick(e);
            }
        });

        // 5. Lighting
        // Ambient light must be very low so the night side is dark
        const ambient = new THREE.AmbientLight(0xffffff, 0.02); 
        this.scene.add(ambient);

        // Sun Light - Bright intensity for realistic day
        this.sunLight = new THREE.DirectionalLight(0xffffff, 1.5);
        this.sunLight.position.set(20, 0, 0); 
        this.scene.add(this.sunLight);

        // 6. Earth Group
        this.earthGroup = new THREE.Group();
        this.scene.add(this.earthGroup);

        // --- ASSET LOADER ---
        const loader = new THREE.TextureLoader();
        const texPath = '/static/assets/textures/';

        // --- EARTH SURFACE (Realistic) ---
        const geometry = new THREE.SphereGeometry(this.radius, 64, 64);
        
        const mat = new THREE.MeshPhongMaterial({
            // 1. The Day Map (Satellite View)
            map: loader.load(texPath + 'earth_daymap.jpg'),
            
            // 2. The Specular Map (Shininess Control)
            specularMap: loader.load(texPath + 'earth_specular.jpg'),
            specular: new THREE.Color(0x333333), // Greyish reflection
            shininess: 15, // Realistic water shine
            
            // 3. The Normal Map (Mountains/Relief)
            normalMap: loader.load(texPath + 'earth_normal.jpg'),
            normalScale: new THREE.Vector2(0.85, 0.85),
            
            // 4. The Night Lights
            // These will show through on the dark side
            emissiveMap: loader.load(texPath + 'earth_night.jpg'),
            emissive: new THREE.Color(0xffffee),
            emissiveIntensity: 0.4 // Subtle glow, not blinding
        });

        this.earthMesh = new THREE.Mesh(geometry, mat);
        // Align textures (-90 degree rotation usually required for standard maps)
        // Note: We handle texture alignment in logic, keeping mesh default for now.
        this.earthGroup.add(this.earthMesh);

        // --- CLOUDS LAYER ---
        // A slightly larger sphere
        const cloudGeo = new THREE.SphereGeometry(this.radius * 1.015, 64, 64);
        const cloudMat = new THREE.MeshPhongMaterial({
            map: loader.load(texPath + 'earth_clouds.jpg'),
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending, // Black background becomes transparent
            side: THREE.DoubleSide,
            // Clouds shouldn't shine too much
            shininess: 0 
        });
        
        this.cloudMesh = new THREE.Mesh(cloudGeo, cloudMat);
        this.earthGroup.add(this.cloudMesh);

        // --- ATMOSPHERE GLOW ---
        const atmoGeo = new THREE.SphereGeometry(this.radius * 1.025, 64, 64);
        const atmoMat = new THREE.MeshPhongMaterial({
            color: 0x00aaff,
            transparent: true,
            opacity: 0.1,
            side: THREE.BackSide,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });
        const atmoMesh = new THREE.Mesh(atmoGeo, atmoMat);
        this.earthGroup.add(atmoMesh);

        // --- STARS ---
        const starGeo = new THREE.SphereGeometry(90, 64, 64);
        const starMat = new THREE.MeshBasicMaterial({
            map: loader.load(texPath + 'space_stars.jpg'),
            side: THREE.BackSide
        });
        const starMesh = new THREE.Mesh(starGeo, starMat);
        this.scene.add(starMesh);

        // Start Loop
        this.animate();
        this.initialized = true;
        
        window.addEventListener('resize', () => {
            this.camera.aspect = window.innerWidth / window.innerHeight;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(window.innerWidth, window.innerHeight);
        });
    },

    updateSunPosition: function(subLat, subLon) {
        if (!this.sunLight) return;
        const phi = (90 - subLat) * (Math.PI / 180);
        const theta = (subLon + 180) * (Math.PI / 180); 
        const r = 50; 
        
        const x = -(r * Math.sin(phi) * Math.cos(theta));
        const z = (r * Math.sin(phi) * Math.sin(theta));
        const y = (r * Math.cos(phi));
        
        this.sunLight.position.set(x, y, z);
    },

    flyTo: function(lat, lon) {
        if (!this.controls) return;

        const phi = (90 - lat) * (Math.PI / 180);
        const theta = (lon + 90) * (Math.PI / 180); 
        
        const dist = this.camera.position.distanceTo(new THREE.Vector3(0,0,0));
        
        const x = -(dist * Math.sin(phi) * Math.cos(theta));
        const z = (dist * Math.sin(phi) * Math.sin(theta));
        const y = (dist * Math.cos(phi));

        this.camera.position.set(x, y, z);
        this.camera.lookAt(0, 0, 0);
        this.controls.update();
    },

    onGlobeClick: function(event) {
        this.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        this.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

        this.raycaster.setFromCamera(this.mouse, this.camera);
        const intersects = this.raycaster.intersectObject(this.earthMesh);

        if (intersects.length > 0) {
            const point = intersects[0].point;
            const p = point.clone().normalize();
            
            const lat = Math.asin(p.y) * (180 / Math.PI);
            let lon = Math.atan2(-p.z, p.x) * (180 / Math.PI);
            
            lon = lon + 90; 
            
            if (lon > 180) lon -= 360;
            if (lon < -180) lon += 360;

            console.log(`Globe Click: ${lat.toFixed(2)}, ${lon.toFixed(2)}`);
            
            if (window.Widgets) {
                window.Widgets.updateLocation(lat, lon);
            }
        }
    },

    animate: function() {
        requestAnimationFrame(() => this.animate());
        
        // Slowly rotate clouds for realism
        if (this.cloudMesh) {
            this.cloudMesh.rotation.y += 0.0002;
        }

        if (this.controls) this.controls.update();
        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        }
    }
};