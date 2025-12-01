/**
 * Ragify Frontend Application
 * Alpine.js + HTMX based SPA
 */

function ragifyApp() {
    return {
        // State
        currentView: 'dashboard',
        user: null,
        authEnabled: false,

        // Dashboard
        stats: { collections: 0, documents: 0, chunks: 0 },
        status: { ollama: 'error', qdrant: 'error' },
        jobs: [],

        // Collections
        collections: [],
        showCreateCollection: false,
        newCollectionName: '',

        // Upload
        uploadCollection: 'documentation',
        uploadQueue: [],
        uploading: false,
        dragOver: false,

        // Search
        searchCollection: 'documentation',
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
                this.authEnabled = data.enabled;
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
                const res = await fetch('/api/collections');
                const data = await res.json();
                this.collections = data.collections || [];

                // Update stats
                this.stats.collections = this.collections.length;
                this.stats.chunks = this.collections.reduce((sum, c) => sum + c.points_count, 0);

                // Set default upload/search collection
                if (this.collections.length > 0 && !this.uploadCollection) {
                    this.uploadCollection = this.collections[0].name;
                    this.searchCollection = this.collections[0].name;
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
                    body: JSON.stringify({ name: this.newCollectionName })
                });

                if (res.ok) {
                    this.showToast('Collection created', 'success');
                    this.showCreateCollection = false;
                    this.newCollectionName = '';
                    await this.loadCollections();
                } else {
                    const data = await res.json();
                    this.showToast(data.detail || 'Failed to create collection', 'error');
                }
            } catch (e) {
                this.showToast('Failed to create collection', 'error');
            }
        },

        async confirmDeleteCollection(name) {
            if (!confirm(`Delete collection "${name}"? This cannot be undone.`)) return;

            try {
                const res = await fetch(`/api/collections/${name}`, { method: 'DELETE' });
                if (res.ok) {
                    this.showToast('Collection deleted', 'success');
                    await this.loadCollections();
                } else {
                    this.showToast('Failed to delete collection', 'error');
                }
            } catch (e) {
                this.showToast('Failed to delete collection', 'error');
            }
        },

        viewCollection(name) {
            // Could expand to show documents
            this.showToast(`Viewing ${name}`, 'info');
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
                const res = await fetch('/api/jobs?limit=10');
                const data = await res.json();
                this.jobs = data.jobs || [];
            } catch (e) {
                console.error('Failed to load jobs:', e);
            }
        },

        // Upload
        handleDrop(event) {
            this.dragOver = false;
            const files = event.dataTransfer.files;
            this.addFilesToQueue(files);
        },

        handleFileSelect(event) {
            const files = event.target.files;
            this.addFilesToQueue(files);
            event.target.value = ''; // Reset input
        },

        addFilesToQueue(files) {
            for (const file of files) {
                // Avoid duplicates
                if (!this.uploadQueue.find(f => f.name === file.name)) {
                    this.uploadQueue.push(file);
                }
            }
        },

        async startUpload() {
            if (this.uploadQueue.length === 0 || this.uploading) return;

            this.uploading = true;

            for (const file of this.uploadQueue) {
                try {
                    const formData = new FormData();
                    formData.append('file', file);
                    formData.append('collection', this.uploadCollection);

                    const res = await fetch('/api/upload', {
                        method: 'POST',
                        body: formData
                    });

                    if (res.ok) {
                        this.showToast(`Uploaded: ${file.name}`, 'success');
                    } else {
                        this.showToast(`Failed: ${file.name}`, 'error');
                    }
                } catch (e) {
                    this.showToast(`Failed: ${file.name}`, 'error');
                }
            }

            this.uploadQueue = [];
            this.uploading = false;
            await this.loadJobs();
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
                    })
                });

                if (res.ok) {
                    const data = await res.json();
                    this.searchResults = data.results || [];
                    if (this.searchResults.length === 0) {
                        this.showToast('No results found', 'info');
                    }
                } else {
                    const data = await res.json();
                    this.showToast(data.detail || 'Search failed', 'error');
                }
            } catch (e) {
                this.showToast('Search failed', 'error');
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
