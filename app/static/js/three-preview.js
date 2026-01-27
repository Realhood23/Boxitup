/**
 * Three.js 3D Preview for Enclosure Generator
 * Renders a 3D visualization of the enclosure with components and holes
 */

class EnclosurePreview3D {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = null;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.enclosureMesh = null;
        this.lidMesh = null;
        this.componentMeshes = [];
        this.holeMeshes = [];
        this.gridHelper = null;
        this.animationId = null;

        // Settings
        this.showLid = true;
        this.explodedView = false;
        this.explodeDistance = 30;
        this.wireframe = false;

        // Colors
        this.colors = {
            enclosure: 0x4a9eff,
            lid: 0x3b82f6,
            component: 0xffc864,
            selectedComponent: 0x22c55e,
            hole: 0xff6464,
            grid: 0x444444,
            background: 0x1a1a2e
        };
    }

    init() {
        this.container = document.getElementById(this.containerId);
        if (!this.container) {
            console.error('Container not found:', this.containerId);
            return false;
        }

        const width = this.container.clientWidth;
        const height = this.container.clientHeight;

        // Create scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(this.colors.background);

        // Create camera
        this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 2000);
        this.camera.position.set(150, 100, 150);
        this.camera.lookAt(0, 0, 0);

        // Create renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.container.appendChild(this.renderer.domElement);

        // Add orbit controls
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = false;
        this.controls.minDistance = 50;
        this.controls.maxDistance = 500;
        this.controls.maxPolarAngle = Math.PI / 1.5;

        // Add lights
        this.addLights();

        // Add grid
        this.addGrid();

        // Handle resize
        window.addEventListener('resize', () => this.onResize());

        // Start animation loop
        this.animate();

        return true;
    }

    addLights() {
        // Ambient light
        const ambient = new THREE.AmbientLight(0xffffff, 0.4);
        this.scene.add(ambient);

        // Main directional light
        const directional = new THREE.DirectionalLight(0xffffff, 0.8);
        directional.position.set(100, 150, 100);
        directional.castShadow = true;
        directional.shadow.mapSize.width = 2048;
        directional.shadow.mapSize.height = 2048;
        directional.shadow.camera.near = 10;
        directional.shadow.camera.far = 500;
        directional.shadow.camera.left = -100;
        directional.shadow.camera.right = 100;
        directional.shadow.camera.top = 100;
        directional.shadow.camera.bottom = -100;
        this.scene.add(directional);

        // Fill light
        const fill = new THREE.DirectionalLight(0xffffff, 0.3);
        fill.position.set(-50, 50, -50);
        this.scene.add(fill);

        // Rim light
        const rim = new THREE.DirectionalLight(0x6666ff, 0.2);
        rim.position.set(0, -50, -100);
        this.scene.add(rim);
    }

    addGrid() {
        this.gridHelper = new THREE.GridHelper(200, 20, 0x555555, 0x333333);
        this.gridHelper.position.y = -1;
        this.scene.add(this.gridHelper);
    }

    onResize() {
        if (!this.container || !this.camera || !this.renderer) return;

        const width = this.container.clientWidth;
        const height = this.container.clientHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());

        if (this.controls) {
            this.controls.update();
        }

        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        }
    }

    /**
     * Update the 3D view with enclosure data
     * @param {Object} data - { enclosure, components, holes, componentDimensions }
     */
    update(data) {
        // Clear existing meshes
        this.clearMeshes();

        const { enclosure, components, holes, componentDimensions, selectedComponentId } = data;

        if (!enclosure) return;

        // Create enclosure body
        this.createEnclosure(enclosure);

        // Create lid
        if (enclosure.lid_type && enclosure.lid_type !== 'none') {
            this.createLid(enclosure);
        }

        // Create components
        if (components && components.length > 0) {
            components.forEach(comp => {
                const dims = componentDimensions?.[comp.component_id] || { length: 25, width: 18, height: 10 };
                const isSelected = comp.id === selectedComponentId;
                this.createComponent(comp, dims, isSelected);
            });
        }

        // Create holes visualization
        if (holes && holes.length > 0) {
            holes.forEach(hole => this.createHoleMarker(hole, enclosure));
        }

        // Center camera on enclosure
        this.centerCamera(enclosure);
    }

    createEnclosure(enclosure) {
        const length = enclosure.inner_length || 100;
        const width = enclosure.inner_width || 60;
        const height = enclosure.inner_height || 30;
        const wallThickness = enclosure.wall_thickness || 2;
        const cornerRadius = enclosure.corner_radius || 0;

        // Outer dimensions
        const outerLength = length + wallThickness * 2;
        const outerWidth = width + wallThickness * 2;
        const outerHeight = height + wallThickness;

        let geometry;

        if (enclosure.shape === 'cylinder') {
            // Cylinder enclosure
            const outerRadius = Math.max(outerLength, outerWidth) / 2;
            const innerRadius = outerRadius - wallThickness;

            const outerGeo = new THREE.CylinderGeometry(outerRadius, outerRadius, outerHeight, 32);
            const innerGeo = new THREE.CylinderGeometry(innerRadius, innerRadius, height, 32);

            // Use CSG to subtract inner from outer (simplified - just show outer for now)
            geometry = outerGeo;
        } else if (cornerRadius > 0) {
            // Rounded box
            geometry = this.createRoundedBoxGeometry(outerLength, outerHeight, outerWidth, cornerRadius, 4);
        } else {
            // Regular box
            geometry = new THREE.BoxGeometry(outerLength, outerHeight, outerWidth);
        }

        const material = new THREE.MeshPhongMaterial({
            color: this.colors.enclosure,
            transparent: true,
            opacity: 0.7,
            side: THREE.DoubleSide,
            wireframe: this.wireframe
        });

        this.enclosureMesh = new THREE.Mesh(geometry, material);
        this.enclosureMesh.position.set(length / 2, outerHeight / 2, width / 2);
        this.enclosureMesh.castShadow = true;
        this.enclosureMesh.receiveShadow = true;

        this.scene.add(this.enclosureMesh);

        // Add inner volume visualization (darker)
        const innerGeometry = new THREE.BoxGeometry(length, height, width);
        const innerMaterial = new THREE.MeshPhongMaterial({
            color: 0x2a5a9f,
            transparent: true,
            opacity: 0.3,
            wireframe: this.wireframe
        });
        const innerMesh = new THREE.Mesh(innerGeometry, innerMaterial);
        innerMesh.position.set(length / 2, (height / 2) + wallThickness, width / 2);
        this.scene.add(innerMesh);
        this.componentMeshes.push(innerMesh); // Track for cleanup
    }

    createLid(enclosure) {
        const length = enclosure.inner_length || 100;
        const width = enclosure.inner_width || 60;
        const wallThickness = enclosure.wall_thickness || 2;
        const lidThickness = wallThickness;

        const outerLength = length + wallThickness * 2;
        const outerWidth = width + wallThickness * 2;

        const geometry = new THREE.BoxGeometry(outerLength, lidThickness, outerWidth);
        const material = new THREE.MeshPhongMaterial({
            color: this.colors.lid,
            transparent: true,
            opacity: this.showLid ? 0.6 : 0.2,
            wireframe: this.wireframe
        });

        this.lidMesh = new THREE.Mesh(geometry, material);

        const baseY = (enclosure.inner_height || 30) + wallThickness + lidThickness / 2;
        const explodeOffset = this.explodedView ? this.explodeDistance : 0;

        this.lidMesh.position.set(length / 2, baseY + explodeOffset, width / 2);
        this.lidMesh.castShadow = true;

        this.scene.add(this.lidMesh);
    }

    createComponent(component, dimensions, isSelected) {
        const { length, width, height } = dimensions;
        const x = component.position?.x_mm || 0;
        const y = component.position?.y_mm || 0;
        const z = component.position?.z_mm || 0;

        const geometry = new THREE.BoxGeometry(length, height, width);
        const material = new THREE.MeshPhongMaterial({
            color: isSelected ? this.colors.selectedComponent : this.colors.component,
            transparent: true,
            opacity: 0.85
        });

        const mesh = new THREE.Mesh(geometry, material);

        // Position component in enclosure space
        // x_mm and y_mm are 2D positions from top view
        // Z position is height off bottom
        const wallThickness = 2;
        mesh.position.set(
            x + length / 2,
            z + height / 2 + wallThickness,
            y + width / 2
        );

        mesh.castShadow = true;
        mesh.receiveShadow = true;

        // Add component label
        this.addTextLabel(mesh, component.component_name || 'Component');

        this.scene.add(mesh);
        this.componentMeshes.push(mesh);
    }

    addTextLabel(mesh, text) {
        // Create a canvas texture for the label
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = 256;
        canvas.height = 64;

        context.fillStyle = 'rgba(0, 0, 0, 0.7)';
        context.fillRect(0, 0, canvas.width, canvas.height);

        context.fillStyle = '#ffffff';
        context.font = 'bold 24px Arial';
        context.textAlign = 'center';
        context.textBaseline = 'middle';

        // Truncate text if too long
        let displayText = text;
        while (context.measureText(displayText).width > 240 && displayText.length > 3) {
            displayText = displayText.slice(0, -4) + '...';
        }
        context.fillText(displayText, canvas.width / 2, canvas.height / 2);

        const texture = new THREE.CanvasTexture(canvas);
        const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
        const sprite = new THREE.Sprite(spriteMaterial);

        sprite.scale.set(25, 6.25, 1);
        sprite.position.copy(mesh.position);
        sprite.position.y += 10;

        this.scene.add(sprite);
        this.componentMeshes.push(sprite);
    }

    createHoleMarker(hole, enclosure) {
        const holeWidth = hole.width_mm || 10;
        const holeHeight = hole.height_mm || 10;
        const depth = 5;

        let geometry;
        if (hole.is_circular) {
            geometry = new THREE.CylinderGeometry(holeWidth / 2, holeWidth / 2, depth, 16);
        } else {
            geometry = new THREE.BoxGeometry(holeWidth, depth, holeHeight);
        }

        const material = new THREE.MeshPhongMaterial({
            color: this.colors.hole,
            transparent: true,
            opacity: 0.7,
            emissive: this.colors.hole,
            emissiveIntensity: 0.3
        });

        const mesh = new THREE.Mesh(geometry, material);

        // Position based on face
        const length = enclosure.inner_length || 100;
        const width = enclosure.inner_width || 60;
        const height = enclosure.inner_height || 30;
        const wallThickness = enclosure.wall_thickness || 2;

        const hx = hole.position_x_mm || 0;
        const hy = hole.position_y_mm || 0;

        switch (hole.face) {
            case 'front':
                mesh.position.set(hx + holeWidth / 2, hy + holeHeight / 2 + wallThickness, -depth / 2);
                mesh.rotation.x = Math.PI / 2;
                break;
            case 'back':
                mesh.position.set(hx + holeWidth / 2, hy + holeHeight / 2 + wallThickness, width + wallThickness * 2 + depth / 2);
                mesh.rotation.x = Math.PI / 2;
                break;
            case 'left':
                mesh.position.set(-depth / 2, hy + holeHeight / 2 + wallThickness, hx + holeWidth / 2);
                mesh.rotation.z = Math.PI / 2;
                break;
            case 'right':
                mesh.position.set(length + wallThickness * 2 + depth / 2, hy + holeHeight / 2 + wallThickness, hx + holeWidth / 2);
                mesh.rotation.z = Math.PI / 2;
                break;
            case 'top':
                mesh.position.set(hx + holeWidth / 2, height + wallThickness * 2 + depth / 2, hy + holeHeight / 2);
                break;
            case 'bottom':
                mesh.position.set(hx + holeWidth / 2, -depth / 2, hy + holeHeight / 2);
                break;
        }

        this.scene.add(mesh);
        this.holeMeshes.push(mesh);
    }

    createRoundedBoxGeometry(width, height, depth, radius, segments) {
        // Simplified rounded box using standard BoxGeometry
        // A proper implementation would use BufferGeometry with custom vertices
        return new THREE.BoxGeometry(width, height, depth);
    }

    centerCamera(enclosure) {
        const length = enclosure.inner_length || 100;
        const width = enclosure.inner_width || 60;
        const height = enclosure.inner_height || 30;

        const centerX = length / 2;
        const centerY = height / 2;
        const centerZ = width / 2;

        this.controls.target.set(centerX, centerY, centerZ);

        // Position camera based on enclosure size
        const maxDim = Math.max(length, width, height);
        const distance = maxDim * 2.5;

        this.camera.position.set(
            centerX + distance * 0.7,
            centerY + distance * 0.5,
            centerZ + distance * 0.7
        );

        this.camera.lookAt(centerX, centerY, centerZ);
        this.controls.update();
    }

    clearMeshes() {
        // Remove enclosure
        if (this.enclosureMesh) {
            this.scene.remove(this.enclosureMesh);
            this.enclosureMesh.geometry.dispose();
            this.enclosureMesh.material.dispose();
            this.enclosureMesh = null;
        }

        // Remove lid
        if (this.lidMesh) {
            this.scene.remove(this.lidMesh);
            this.lidMesh.geometry.dispose();
            this.lidMesh.material.dispose();
            this.lidMesh = null;
        }

        // Remove components
        this.componentMeshes.forEach(mesh => {
            this.scene.remove(mesh);
            if (mesh.geometry) mesh.geometry.dispose();
            if (mesh.material) {
                if (mesh.material.map) mesh.material.map.dispose();
                mesh.material.dispose();
            }
        });
        this.componentMeshes = [];

        // Remove holes
        this.holeMeshes.forEach(mesh => {
            this.scene.remove(mesh);
            mesh.geometry.dispose();
            mesh.material.dispose();
        });
        this.holeMeshes = [];
    }

    setShowLid(show) {
        this.showLid = show;
        if (this.lidMesh) {
            this.lidMesh.material.opacity = show ? 0.6 : 0.2;
        }
    }

    setExplodedView(exploded) {
        this.explodedView = exploded;
        if (this.lidMesh && this.enclosureMesh) {
            const baseY = this.enclosureMesh.position.y + this.enclosureMesh.geometry.parameters.height / 2;
            const offset = exploded ? this.explodeDistance : 0;
            this.lidMesh.position.y = baseY + this.lidMesh.geometry.parameters.height / 2 + offset;
        }
    }

    setWireframe(wireframe) {
        this.wireframe = wireframe;
        if (this.enclosureMesh) {
            this.enclosureMesh.material.wireframe = wireframe;
        }
        if (this.lidMesh) {
            this.lidMesh.material.wireframe = wireframe;
        }
    }

    resetView() {
        if (this.enclosureMesh) {
            this.centerCamera({
                inner_length: this.enclosureMesh.geometry.parameters.width || 100,
                inner_width: this.enclosureMesh.geometry.parameters.depth || 60,
                inner_height: this.enclosureMesh.geometry.parameters.height || 30
            });
        }
    }

    dispose() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }

        this.clearMeshes();

        if (this.gridHelper) {
            this.scene.remove(this.gridHelper);
            this.gridHelper.geometry.dispose();
            this.gridHelper.material.dispose();
        }

        if (this.renderer) {
            this.renderer.dispose();
            if (this.renderer.domElement && this.renderer.domElement.parentNode) {
                this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
            }
        }

        if (this.controls) {
            this.controls.dispose();
        }
    }
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EnclosurePreview3D;
}
