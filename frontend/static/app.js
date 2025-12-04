/**
 * Ragify Frontend Application
 * Alpine.js based SPA
 */

function ragifyApp() {
    return {
        // State
        user: null,
        authEnabled: false,
        showLoginModal: false,

        // Dashboard
        stats: { collections: 0, documents: 0, chunks: 0 },
        status: { ollama: 'error', qdrant: 'error' },
        jobs: [],

        // Collections
        collections: [],
        showCreateCollection: false,
        newCollectionName: '',

        // Upload
        uploadCollection: '',
        uploadQueue: [],
        uploading: false,
        dragOver: false,
        showFolderError: false,

        // Search
        searchCollection: '',
        searchQuery: '',
        searchResults: [],
        searching: false,

        // Toasts
        toasts: [],
        toastId: 0,

        // Initialize
        async init() {
            await this.checkAuth();
            await this.loadCollections();
            await this.loadStatus();
            await this.loadJobs();

            // Poll for job updates
            setInterval(() => this.loadJobs(), 5000);
        },

        // Auth
        async checkAuth() {
            try {
                const res = await fetch('/auth/status');
                const data = await res.json();
                this.authEnabled = data.enabled === true;
                if (data.authenticated) {
                    this.user = { username: data.username };
                }
            } catch (e) {
                console.error('Auth check failed:', e);
            }
        },

        // Collections
        async loadCollections() {
            try {
                const res = await fetch('/api/collections', { credentials: 'include' });
                const data = await res.json();
                this.collections = data.collections || [];

                // Update stats
                this.stats.collections = this.collections.length;
                this.stats.chunks = this.collections.reduce((sum, c) => sum + (c.points_count || 0), 0);
                this.stats.documents = this.collections.reduce((sum, c) => sum + (c.documents_count || 0), 0);

                // Set default upload/search collection if not set or invalid
                if (this.collections.length > 0) {
                    const collectionNames = this.collections.map(c => c.name);
                    if (!this.uploadCollection || !collectionNames.includes(this.uploadCollection)) {
                        this.uploadCollection = this.collections[0].name;
                    }
                    if (!this.searchCollection || !collectionNames.includes(this.searchCollection)) {
                        this.searchCollection = this.collections[0].name;
                    }
                }
            } catch (e) {
                console.error('Failed to load collections:', e);
            }
        },

        async createCollection() {
            if (!this.newCollectionName) return;

            try {
                const res = await fetch('/api/collections', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: this.newCollectionName }),
                    credentials: 'include'
                });

                if (res.ok) {
                    this.showToast('Collection created', 'success');
                    this.showCreateCollection = false;
                    this.newCollectionName = '';
                    await this.loadCollections();
                } else {
                    const data = await res.json().catch(() => ({}));
                    this.showToast(data.detail || 'Failed to create collection', 'error');
                }
            } catch (e) {
                this.showToast(`Failed to create collection: ${e.message || 'Network error'}`, 'error');
            }
        },

        async confirmDeleteCollection(name) {
            if (!confirm(`Delete collection "${name}"? This cannot be undone.`)) return;

            try {
                const res = await fetch(`/api/collections/${name}`, { method: 'DELETE', credentials: 'include' });
                if (res.ok) {
                    this.showToast('Collection deleted', 'success');
                    await this.loadCollections();
                } else {
                    const data = await res.json().catch(() => ({}));
                    this.showToast(data.detail || 'Failed to delete collection', 'error');
                }
            } catch (e) {
                this.showToast(`Failed to delete collection: ${e.message || 'Network error'}`, 'error');
            }
        },

        // Status
        async loadStatus() {
            try {
                const res = await fetch('/health');
                const data = await res.json();
                this.status = data.components || { ollama: 'error', qdrant: 'error' };
            } catch (e) {
                this.status = { ollama: 'error', qdrant: 'error' };
            }
        },

        // Jobs
        async loadJobs() {
            try {
                const res = await fetch('/api/jobs?limit=10', { credentials: 'include' });
                const data = await res.json();
                this.jobs = data.jobs || [];
            } catch (e) {
                console.error('Failed to load jobs:', e);
            }
        },

        // Upload - simplified: files only, no folder handling
        handleDrop(event) {
            this.dragOver = false;

            // Check if any dropped item is a folder
            const items = event.dataTransfer.items;
            for (const item of items) {
                const entry = item.webkitGetAsEntry && item.webkitGetAsEntry();
                if (entry && entry.isDirectory) {
                    this.showFolderError = true;
                    return; // Block upload
                }
            }

            this.addFilesToQueue(event.dataTransfer.files);
        },

        handleFileSelect(event) {
            this.addFilesToQueue(event.target.files);
            event.target.value = ''; // Reset input
        },

        addFilesToQueue(files) {
            for (const file of files) {
                // Avoid duplicates by name
                if (!this.uploadQueue.find(f => f.name === file.name)) {
                    this.uploadQueue.push(file);
                }
            }
        },

        async startUpload() {
            if (this.uploadQueue.length === 0 || this.uploading) return;
            this.uploading = true;

            try {
                // Upload each file - ZIP files go to /api/upload-zip, others to /api/upload
                for (const file of this.uploadQueue) {
                    await this.uploadFile(file);
                }
            } catch (e) {
                this.showToast(`Upload failed: ${e.message || 'Unknown error'}`, 'error');
            }

            this.uploadQueue = [];
            this.uploading = false;
            await this.loadJobs();
        },

        async uploadFile(file) {
            const isZip = file.name.toLowerCase().endsWith('.zip');
            const endpoint = isZip ? '/api/upload-zip' : '/api/upload';

            const formData = new FormData();
            formData.append('file', file);
            formData.append('collection', this.uploadCollection);

            const res = await fetch(endpoint, {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });

            if (res.ok) {
                const data = await res.json();
                const jobInfo = data.job_id ? ` (Job: ${data.job_id.slice(0,8)})` : '';
                this.showToast(`Uploaded: ${file.name}${jobInfo}`, 'success');
            } else {
                const error = await res.json().catch(() => ({}));
                throw new Error(error.detail || res.statusText);
            }
        },

        // Search
        async performSearch() {
            if (!this.searchQuery || this.searching) return;

            this.searching = true;
            this.searchResults = [];

            try {
                const res = await fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: this.searchQuery,
                        collection: this.searchCollection,
                        limit: 10
                    }),
                    credentials: 'include'
                });

                if (res.ok) {
                    const data = await res.json();
                    this.searchResults = data.results || [];
                    if (this.searchResults.length === 0) {
                        this.showToast('No results found', 'info');
                    }
                } else {
                    const data = await res.json().catch(() => ({}));
                    this.showToast(data.detail || 'Search failed', 'error');
                }
            } catch (e) {
                this.showToast(`Search failed: ${e.message || 'Network error'}`, 'error');
            }

            this.searching = false;
        },

        // Toasts
        showToast(message, type = 'info') {
            const id = ++this.toastId;
            const toast = { id, message, type, visible: true };
            this.toasts.push(toast);

            // Auto-dismiss after 3 seconds
            setTimeout(() => {
                toast.visible = false;
                setTimeout(() => {
                    this.toasts = this.toasts.filter(t => t.id !== id);
                }, 300);
            }, 3000);
        }
    };
}
