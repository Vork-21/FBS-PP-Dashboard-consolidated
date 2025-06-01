/**
 * Unified Frontend JavaScript for Payment Plan Analysis System
 * Streamlined to work with consolidated backend API
 */

class PaymentPlanApp {
    constructor() {
        this.apiBase = '/api';
        this.currentData = null;
        this.currentView = 'dashboard';
        this.filters = {
            class: null,
            status: null,
            customer: null
        };
        
        // Initialize on DOM load
        document.addEventListener('DOMContentLoaded', () => this.init());
    }

    async init() {
        console.log('🚀 Initializing Payment Plan Analysis System');
        
        this.setupEventListeners();
        this.setupFileDragAndDrop();
        this.initializeToasts();
        
        // Load data if results exist
        if (this.hasResults()) {
            await this.loadCurrentView();
        }
        
        console.log('✅ Application initialized');
    }

    // ============================================================================
    // CORE DATA MANAGEMENT
    // ============================================================================

    async loadCurrentView() {
        try {
            this.showLoading(true);
            
            const params = new URLSearchParams();
            if (this.filters.class) params.append('class_filter', this.filters.class);
            
            const response = await fetch(`${this.apiBase}/data?view=${this.currentView}&${params}`);
            
            if (!response.ok) {
                throw new Error(`Failed to load ${this.currentView} data`);
            }
            
            this.currentData = await response.json();
            this.renderCurrentView();
            
        } catch (error) {
            console.error('Error loading view:', error);
            this.showToast('Error loading data', 'danger');
        } finally {
            this.showLoading(false);
        }
    }

    async analyzeFile(file) {
        try {
            this.showLoading(true, 'Analyzing file...');
            
            const formData = new FormData();
            formData.append('file', file);
            if (this.filters.class) {
                formData.append('class_filter', this.filters.class);
            }
            
            const response = await fetch(`${this.apiBase}/analyze`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Analysis failed');
            }
            
            const result = await response.json();
            
            this.showToast('Analysis completed successfully!', 'success');
            
            // Reload the page to show results
            setTimeout(() => window.location.reload(), 1000);
            
        } catch (error) {
            console.error('Analysis error:', error);
            this.showToast(`Analysis failed: ${error.message}`, 'danger');
        } finally {
            this.showLoading(false);
        }
    }

    // ============================================================================
    // VIEW RENDERING
    // ============================================================================

    renderCurrentView() {
        if (!this.currentData) return;

        switch (this.currentView) {
            case 'dashboard':
                this.renderDashboard();
                break;
            case 'quality':
                this.renderQuality();
                break;
            case 'collections':
                this.renderCollections();
                break;
            case 'projections':
                this.renderProjections();
                break;
        }
    }

    renderDashboard() {
        // Update summary metrics
        this.updateSummaryCards(this.currentData.summary_metrics || {});
        
        // Update customer table
        this.updateCustomerTable(this.currentData.payment_plan_details || []);
        
        // Update charts
        this.updateDashboardCharts();
    }

    renderQuality() {
        const data = this.currentData;
        
        // Update quality overview
        this.updateQualityOverview(data.quality_metrics || {});
        
        // Update issue breakdown
        this.updateIssueBreakdown(data.issue_breakdown || {});
        
        // Update problematic customers
        this.updateProblematicCustomers(data.problematic_customers || []);
    }

    renderCollections() {
        const data = this.currentData;
        
        // Update collections summary
        this.updateCollectionsSummary(data.summary || {});
        
        // Update priority table
        this.updatePriorityTable(data.priorities || []);
    }

    renderProjections() {
        const data = this.currentData;
        
        // Update portfolio projections
        this.updatePortfolioProjections(data.portfolio || {});
        
        // Update customer projections
        this.updateCustomerProjections(data.customers || []);
    }

    // ============================================================================
    // UI UPDATE METHODS
    // ============================================================================

    updateSummaryCards(metrics) {
        const cardUpdates = {
            'totalCustomers': metrics.customers_current + metrics.customers_behind + metrics.customers_completed,
            'totalOutstanding': this.formatCurrency(metrics.total_outstanding || 0),
            'expectedMonthly': this.formatCurrency(metrics.expected_monthly || 0),
            'customersBehind': metrics.customers_behind || 0,
            'dataQualityScore': `${metrics.data_quality_score || 0}%`
        };

        Object.entries(cardUpdates).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) element.textContent = value;
        });
    }

    updateCustomerTable(plans) {
        const tbody = document.getElementById('customerTableBody');
        if (!tbody) return;

        tbody.innerHTML = plans.map(plan => `
            <tr>
                <td><strong>${plan.customer_name}</strong></td>
                <td><small class="text-muted">${plan.plan_id}</small></td>
                <td><strong>${this.formatCurrency(plan.monthly_payment || 0)}</strong></td>
                <td><span class="badge bg-info">${plan.frequency || 'monthly'}</span></td>
                <td><strong class="text-success">${this.formatCurrency(plan.total_owed || 0)}</strong></td>
                <td>
                    <div class="progress" style="height: 15px;">
                        <div class="progress-bar bg-success" style="width: ${plan.percent_paid || 0}%"></div>
                    </div>
                    <small>${(plan.percent_paid || 0).toFixed(1)}%</small>
                </td>
                <td>
                    <span class="${(plan.months_behind || 0) > 0 ? 'text-danger fw-bold' : 'text-muted'}">
                        ${plan.months_behind || 0}
                    </span>
                </td>
                <td>
                    <span class="status-badge status-${plan.status || 'unknown'}">
                        ${(plan.status || 'unknown').charAt(0).toUpperCase() + (plan.status || 'unknown').slice(1)}
                    </span>
                </td>
                <td>
                    ${plan.class_field ? `<span class="badge bg-secondary">${plan.class_field}</span>` : '<span class="text-muted">-</span>'}
                </td>
                <td>
                    ${plan.projected_completion ? new Date(plan.projected_completion).toLocaleDateString() : '<span class="text-muted">-</span>'}
                </td>
            </tr>
        `).join('');
    }

    updateDashboardCharts() {
        // Create quality chart
        const qualityCtx = document.getElementById('qualityChart');
        if (qualityCtx && this.currentData.summary_metrics) {
            const metrics = this.currentData.summary_metrics;
            new Chart(qualityCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Current', 'Behind', 'Completed'],
                    datasets: [{
                        data: [
                            metrics.customers_current || 0,
                            metrics.customers_behind || 0,
                            metrics.customers_completed || 0
                        ],
                        backgroundColor: ['#28a745', '#dc3545', '#3498db']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }
    }

    updateQualityOverview(metrics) {
        const container = document.getElementById('qualityOverview');
        if (!container) return;
        
        container.innerHTML = `
            <div class="row">
                <div class="col-md-4 text-center">
                    <div class="h3 text-success">${metrics.clean_plans || 0}</div>
                    <div class="text-muted">Clean Plans</div>
                </div>
                <div class="col-md-4 text-center">
                    <div class="h3 text-danger">${metrics.problematic_plans || 0}</div>
                    <div class="text-muted">Problematic Plans</div>
                </div>
                <div class="col-md-4 text-center">
                    <div class="h3 text-primary">${metrics.data_quality_score || 0}%</div>
                    <div class="text-muted">Quality Score</div>
                </div>
            </div>
        `;
    }

    updateIssueBreakdown(issues) {
        const container = document.getElementById('issueBreakdown');
        if (!container) return;

        if (Object.keys(issues).length === 0) {
            container.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle me-2"></i>
                    No data quality issues found!
                </div>
            `;
            return;
        }

        let html = '<div class="row">';
        Object.entries(issues).forEach(([issueType, count]) => {
            const displayName = issueType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            const severity = this.getIssueSeverity(issueType);
            
            html += `
                <div class="col-md-6 col-lg-3 mb-3">
                    <div class="card border-${severity}">
                        <div class="card-body">
                            <h6 class="card-title">${displayName}</h6>
                            <span class="badge bg-${severity} rounded-pill">${count}</span>
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        container.innerHTML = html;
    }

    updateProblematicCustomers(customers) {
        const tbody = document.getElementById('problematicCustomersBody');
        if (!tbody) return;

        if (customers.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center">
                        <div class="alert alert-success mb-0">
                            <i class="fas fa-check-circle me-2"></i>
                            No problematic customers found!
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = customers.map(customer => `
            <tr>
                <td><strong>${customer.customer_name}</strong></td>
                <td>${this.formatCurrency(customer.total_open || 0)}</td>
                <td><span class="badge bg-secondary">1</span></td>
                <td>
                    ${customer.issues.slice(0, 3).map(issue => 
                        `<span class="badge bg-warning me-1">${issue.replace(/_/g, ' ')}</span>`
                    ).join('')}
                    ${customer.issues.length > 3 ? `<span class="text-muted">+${customer.issues.length - 3} more</span>` : ''}
                </td>
                <td>
                    <span class="badge bg-${customer.issues.some(i => ['no_payment_terms', 'invalid_amounts'].includes(i)) ? 'danger' : 'warning'}">
                        ${customer.issues.some(i => ['no_payment_terms', 'invalid_amounts'].includes(i)) ? 'Critical' : 'Warning'}
                    </span>
                </td>
                <td><span class="text-muted">-</span></td>
            </tr>
        `).join('');
    }

    updateCollectionsSummary(summary) {
        const container = document.getElementById('collectionsSummary');
        if (!container) return;
        
        container.innerHTML = `
            <div class="row">
                <div class="col-md-3 text-center">
                    <div class="h4 text-danger">${summary.customers_behind || 0}</div>
                    <div class="text-muted">Behind</div>
                </div>
                <div class="col-md-3 text-center">
                    <div class="h4 text-warning">${this.formatCurrency(summary.total_outstanding || 0)}</div>
                    <div class="text-muted">Total Owed</div>
                </div>
                <div class="col-md-3 text-center">
                    <div class="h4 text-info">${this.formatCurrency(summary.expected_monthly || 0)}</div>
                    <div class="text-muted">Expected Monthly</div>
                </div>
                <div class="col-md-3 text-center">
                    <div class="h4 text-secondary">${summary.percentage_behind || 0}%</div>
                    <div class="text-muted">% Behind</div>
                </div>
            </div>
        `;
    }

    updatePriorityTable(priorities) {
        const tbody = document.getElementById('priorityTableBody');
        if (!tbody) return;

        tbody.innerHTML = priorities.slice(0, 20).map((item, index) => {
            const priority = index + 1;
            const severityClass = item.months_behind >= 3 ? 'table-danger' : 
                                 item.months_behind >= 1 ? 'table-warning' : 'table-info';
            
            return `
                <tr class="${severityClass}">
                    <td><span class="badge bg-dark fs-6">${priority}</span></td>
                    <td><strong>${item.customer_name}</strong></td>
                    <td><small class="text-muted">${item.plan_id}</small></td>
                    <td>
                        ${item.class_field ? `<span class="badge bg-secondary">${item.class_field}</span>` : '<span class="text-muted">-</span>'}
                    </td>
                    <td><span class="fw-bold text-danger">${item.months_behind}</span></td>
                    <td><strong class="text-success">${this.formatCurrency(item.total_owed || 0)}</strong></td>
                    <td><span class="text-primary">${this.formatCurrency(item.monthly_payment || 0)}</span></td>
                    <td><span class="text-danger fw-bold">${this.formatCurrency((item.months_behind * item.monthly_payment) || 0)}</span></td>
                    <td>
                        <span class="status-badge status-behind">Behind</span>
                    </td>
                </tr>
            `;
        }).join('');
    }

    updatePortfolioProjections(portfolio) {
        // Update portfolio chart
        const ctx = document.getElementById('portfolioChart');
        if (ctx && portfolio.monthly_projections) {
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: portfolio.monthly_projections.map(month => {
                        const date = new Date(month.date);
                        return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
                    }),
                    datasets: [{
                        label: 'Expected Payments',
                        data: portfolio.monthly_projections.map(month => month.expected_payment),
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }

        // Update monthly schedule table
        const tbody = document.getElementById('monthlyScheduleTable');
        if (tbody && portfolio.monthly_projections) {
            tbody.innerHTML = portfolio.monthly_projections.map(month => {
                const date = new Date(month.date);
                const monthName = date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
                
                return `
                    <tr>
                        <td><strong>${monthName}</strong></td>
                        <td><span class="text-success fw-bold">${this.formatCurrency(month.expected_payment)}</span></td>
                        <td><span class="badge bg-info">${month.active_customers}</span></td>
                        <td><span class="badge bg-warning">${month.completing_customers || 0}</span></td>
                        <td><span class="text-secondary">${this.formatCurrency(month.cumulative_total)}</span></td>
                    </tr>
                `;
            }).join('');
        }
    }

    updateCustomerProjections(customers) {
        const container = document.getElementById('customerTimelineContainer');
        if (!container) return;

        if (customers.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info text-center">
                    <i class="fas fa-info-circle me-2"></i>
                    No customer projections available.
                </div>
            `;
            return;
        }

        let html = `
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Customer</th>
                            <th>Status</th>
                            <th>Monthly Payment</th>
                            <th>Total Owed</th>
                            <th>Plans</th>
                            <th>Completion</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        customers.forEach(customer => {
            const completionText = customer.completion_month > 0 ? 
                `${customer.completion_month} months` : 'Unknown';
            
            html += `
                <tr>
                    <td><strong>${customer.customer_name}</strong></td>
                    <td><span class="badge bg-${customer.status === 'behind' ? 'danger' : 'success'}">${customer.status}</span></td>
                    <td><strong class="text-success">${this.formatCurrency(customer.total_monthly_payment)}</strong></td>
                    <td><strong>${this.formatCurrency(customer.total_owed)}</strong></td>
                    <td><span class="badge bg-info">${customer.plan_count}</span></td>
                    <td>
                        <span class="badge ${customer.completion_month <= 12 ? 'bg-success' : customer.completion_month <= 24 ? 'bg-warning' : 'bg-info'}">
                            ${completionText}
                        </span>
                    </td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;

        container.innerHTML = html;
    }

    // ============================================================================
    // EVENT HANDLERS
    // ============================================================================

    setupEventListeners() {
        // View switching
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-view]')) {
                this.switchView(e.target.dataset.view);
            }
        });

        // Filter changes
        document.addEventListener('change', (e) => {
            if (e.target.matches('[data-filter]')) {
                this.updateFilter(e.target.dataset.filter, e.target.value);
            }
        });

        // Export buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-export]')) {
                this.exportData(e.target.dataset.export);
            }
        });
    }

    setupFileDragAndDrop() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');

        if (!uploadArea || !fileInput) return;

        // Click to upload
        uploadArea.addEventListener('click', () => fileInput.click());
        
        // File selection
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.analyzeFile(e.target.files[0]);
            }
        });

        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.analyzeFile(files[0]);
            }
        });
    }

    // ============================================================================
    // UTILITY METHODS
    // ============================================================================

    async switchView(view) {
        this.currentView = view;
        await this.loadCurrentView();
    }

    updateFilter(filterType, value) {
        this.filters[filterType] = value === 'all' ? null : value;
        this.loadCurrentView();
    }

    async exportData(format) {
        try {
            const params = new URLSearchParams({
                format_type: format,
                view: this.currentView
            });
            
            if (this.filters.class) {
                params.append('class_filter', this.filters.class);
            }

            const response = await fetch(`${this.apiBase}/export/${format}?${params}`);
            
            if (!response.ok) {
                throw new Error('Export failed');
            }

            // Trigger download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `export_${format}_${new Date().toISOString().split('T')[0]}.${format}`;
            a.click();
            window.URL.revokeObjectURL(url);

            this.showToast(`Export completed successfully`, 'success');

        } catch (error) {
            console.error('Export error:', error);
            this.showToast('Export failed', 'danger');
        }
    }

    hasResults() {
        return document.body.dataset.hasResults === 'true';
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount || 0);
    }

    getIssueSeverity(issueType) {
        const critical = ['no_payment_terms', 'invalid_amounts'];
        const warning = ['multiple_payment_terms', 'future_dated', 'missing_class'];
        
        if (critical.includes(issueType)) return 'danger';
        if (warning.includes(issueType)) return 'warning';
        return 'info';
    }

    // ============================================================================
    // UI UTILITIES
    // ============================================================================

    showLoading(show, message = 'Loading...') {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.style.display = show ? 'flex' : 'none';
            const messageEl = overlay.querySelector('.loading-message');
            if (messageEl) messageEl.textContent = message;
        }
    }

    initializeToasts() {
        // Create toast container if it doesn't exist
        if (!document.getElementById('toast-container')) {
            const container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'position-fixed top-0 end-0 p-3';
            container.style.zIndex = '1080';
            document.body.appendChild(container);
        }
    }

    showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        const toastId = 'toast-' + Date.now();
        
        const icons = {
            success: 'fas fa-check-circle',
            danger: 'fas fa-exclamation-triangle',
            warning: 'fas fa-exclamation-circle',
            info: 'fas fa-info-circle'
        };
        
        const toastHtml = `
            <div id="${toastId}" class="toast align-items-center text-white bg-${type}" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="${icons[type]} me-2"></i>${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', toastHtml);
        
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
        toast.show();
        
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }

    async clearResults() {
        if (confirm('Are you sure you want to clear all analysis results?')) {
            try {
                const response = await fetch(`${this.apiBase}/clear`, { method: 'POST' });
                if (response.ok) {
                    window.location.href = '/';
                }
            } catch (error) {
                console.error('Error clearing results:', error);
                this.showToast('Error clearing results', 'danger');
            }
        }
    }
}

// Initialize the application
const app = new PaymentPlanApp();

// Make key functions globally available for backward compatibility
window.showToast = (message, type) => app.showToast(message, type);
window.formatCurrency = (amount) => app.formatCurrency(amount);
window.clearResults = () => app.clearResults();

console.log('📦 Unified Payment Plan Analysis System loaded');