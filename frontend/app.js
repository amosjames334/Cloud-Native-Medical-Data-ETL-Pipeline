// Configuration
const CONFIG = {
    // Update this to your Airflow URL
    // For local: http://localhost:8080
    // For Kubernetes port-forward: http://localhost:8080
    airflowUrl: window.location.hostname === 'localhost'
        ? 'http://localhost:8080'
        : '/airflow',
    dagId: 'medical_etl_pipeline',
    refreshInterval: 5000, // 5 seconds
    username: '', // Will be set from user input or config
    password: '', // Will be set from user input or config
};

// State
let state = {
    dagRuns: [],
    selectedRunId: null,
    tasks: [],
    stats: {
        successRate: 0,
        totalRuns: 0,
        avgDuration: 0,
        lastRun: null
    },
    connected: false,
    refreshTimer: null,
    chart: null
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    // Check for stored credentials
    const storedUsername = localStorage.getItem('airflow_username');
    const storedPassword = localStorage.getItem('airflow_password');

    if (storedUsername && storedPassword) {
        CONFIG.username = storedUsername;
        CONFIG.password = storedPassword;
    } else {
        // Prompt for credentials
        promptForCredentials();
    }

    // Set up event listeners
    setupEventListeners();

    // Initialize chart
    initializeChart();

    // Load initial data
    await loadDashboardData();

    // Start auto-refresh
    startAutoRefresh();
}

function promptForCredentials() {
    const username = prompt('Enter Airflow username:', 'admin');
    const password = prompt('Enter Airflow password:');

    if (username && password) {
        CONFIG.username = username;
        CONFIG.password = password;
        localStorage.setItem('airflow_username', username);
        localStorage.setItem('airflow_password', password);
    }
}

function setupEventListeners() {
    document.getElementById('refreshBtn').addEventListener('click', () => {
        loadDashboardData();
    });

    document.getElementById('triggerBtn').addEventListener('click', () => {
        openTriggerModal();
    });

    document.getElementById('dagRunFilter').addEventListener('change', (e) => {
        filterDagRuns(e.target.value);
    });

    document.getElementById('logSearch').addEventListener('input', (e) => {
        searchLogs(e.target.value);
    });

    document.getElementById('clearLogsBtn').addEventListener('click', () => {
        clearLogs();
    });

    // Set today's date as default for execution date
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('executionDate').value = today;
}

// API Functions
async function makeAirflowRequest(endpoint, method = 'GET', body = null) {
    const url = `${CONFIG.airflowUrl}/api/v1${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic ' + btoa(`${CONFIG.username}:${CONFIG.password}`)
    };

    try {
        const response = await fetch(url, {
            method,
            headers,
            body: body ? JSON.stringify(body) : null
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        updateConnectionStatus(true);
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        updateConnectionStatus(false);
        throw error;
    }
}

async function getDagRuns(limit = 20) {
    try {
        const data = await makeAirflowRequest(
            `/dags/${CONFIG.dagId}/dagRuns?limit=${limit}&order_by=-execution_date`
        );
        return data.dag_runs || [];
    } catch (error) {
        showToast('Failed to fetch DAG runs', 'error');
        return [];
    }
}

async function getTaskInstances(dagRunId) {
    try {
        const data = await makeAirflowRequest(
            `/dags/${CONFIG.dagId}/dagRuns/${dagRunId}/taskInstances`
        );
        return data.task_instances || [];
    } catch (error) {
        showToast('Failed to fetch task instances', 'error');
        return [];
    }
}

async function triggerDag(conf = {}) {
    try {
        const data = await makeAirflowRequest(
            `/dags/${CONFIG.dagId}/dagRuns`,
            'POST',
            { conf }
        );
        showToast('DAG triggered successfully!', 'success');
        await loadDashboardData();
        return data;
    } catch (error) {
        showToast('Failed to trigger DAG: ' + error.message, 'error');
        throw error;
    }
}

async function getTaskLogs(dagRunId, taskId, taskTryNumber = 1) {
    try {
        const data = await makeAirflowRequest(
            `/dags/${CONFIG.dagId}/dagRuns/${dagRunId}/taskInstances/${taskId}/logs/${taskTryNumber}`
        );
        return data;
    } catch (error) {
        console.error('Failed to fetch logs:', error);
        return null;
    }
}

// Dashboard Functions
async function loadDashboardData() {
    try {
        // Load DAG runs
        state.dagRuns = await getDagRuns();

        // Calculate stats
        calculateStats();

        // Render UI
        renderDagRuns();
        renderStats();
        updateChart();

        // Load tasks for selected run
        if (state.selectedRunId) {
            await loadTaskInstances(state.selectedRunId);
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

function calculateStats() {
    if (state.dagRuns.length === 0) {
        state.stats = {
            successRate: 0,
            totalRuns: 0,
            avgDuration: 0,
            lastRun: null
        };
        return;
    }

    const successCount = state.dagRuns.filter(r => r.state === 'success').length;
    state.stats.successRate = ((successCount / state.dagRuns.length) * 100).toFixed(1);
    state.stats.totalRuns = state.dagRuns.length;

    // Calculate average duration
    const completedRuns = state.dagRuns.filter(r => r.end_date);
    if (completedRuns.length > 0) {
        const totalDuration = completedRuns.reduce((sum, run) => {
            const start = new Date(run.start_date);
            const end = new Date(run.end_date);
            return sum + (end - start);
        }, 0);
        const avgMs = totalDuration / completedRuns.length;
        state.stats.avgDuration = formatDuration(avgMs);
    }

    // Last run
    if (state.dagRuns[0]) {
        state.stats.lastRun = formatRelativeTime(state.dagRuns[0].execution_date);
    }
}

function renderStats() {
    document.getElementById('successRate').textContent = `${state.stats.successRate}%`;
    document.getElementById('totalRuns').textContent = state.stats.totalRuns;
    document.getElementById('avgDuration').textContent = state.stats.avgDuration || '--';
    document.getElementById('lastRun').textContent = state.stats.lastRun || '--';
}

function renderDagRuns() {
    const container = document.getElementById('dagRunsList');

    if (state.dagRuns.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <p>No DAG runs found</p>
            </div>
        `;
        return;
    }

    container.innerHTML = state.dagRuns.map(run => `
        <div class="dag-run-item ${state.selectedRunId === run.dag_run_id ? 'selected' : ''}" 
             onclick="selectDagRun('${run.dag_run_id}')">
            <div class="dag-run-header">
                <span class="dag-run-id">${run.dag_run_id}</span>
                <span class="status-badge ${run.state}">${run.state}</span>
            </div>
            <div class="dag-run-meta">
                <span>📅 ${formatDateTime(run.execution_date)}</span>
                ${run.end_date ? `<span>⏱️ ${calculateDuration(run.start_date, run.end_date)}</span>` : ''}
            </div>
        </div>
    `).join('');
}

async function selectDagRun(dagRunId) {
    state.selectedRunId = dagRunId;
    renderDagRuns();
    await loadTaskInstances(dagRunId);
}

async function loadTaskInstances(dagRunId) {
    state.tasks = await getTaskInstances(dagRunId);
    renderTaskGrid();
    renderCurrentRunDetails();
    await loadErrorLogs();
}

function renderTaskGrid() {
    const container = document.getElementById('taskGrid');

    if (state.tasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <p>No tasks found</p>
            </div>
        `;
        return;
    }

    container.innerHTML = state.tasks.map(task => `
        <div class="task-item ${task.state || 'queued'}">
            <div class="task-header">
                <span class="task-name">${task.task_id}</span>
                <span class="status-badge ${task.state || 'queued'}">${task.state || 'queued'}</span>
            </div>
            <div class="task-meta">
                ${task.start_date ? `Started: ${formatDateTime(task.start_date)}` : 'Not started'}
                ${task.duration ? ` • Duration: ${formatDuration(task.duration * 1000)}` : ''}
            </div>
        </div>
    `).join('');
}

function renderCurrentRunDetails() {
    const container = document.getElementById('currentRunDetails');

    if (!state.selectedRunId) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <p>Select a DAG run to view details</p>
            </div>
        `;
        return;
    }

    const run = state.dagRuns.find(r => r.dag_run_id === state.selectedRunId);
    if (!run) return;

    const successTasks = state.tasks.filter(t => t.state === 'success').length;
    const failedTasks = state.tasks.filter(t => t.state === 'failed').length;
    const runningTasks = state.tasks.filter(t => t.state === 'running').length;

    container.innerHTML = `
        <div class="dag-run-details">
            <div class="detail-row">
                <strong>Run ID:</strong>
                <span>${run.dag_run_id}</span>
            </div>
            <div class="detail-row">
                <strong>State:</strong>
                <span class="status-badge ${run.state}">${run.state}</span>
            </div>
            <div class="detail-row">
                <strong>Execution Date:</strong>
                <span>${formatDateTime(run.execution_date)}</span>
            </div>
            <div class="detail-row">
                <strong>Start Date:</strong>
                <span>${run.start_date ? formatDateTime(run.start_date) : 'N/A'}</span>
            </div>
            <div class="detail-row">
                <strong>End Date:</strong>
                <span>${run.end_date ? formatDateTime(run.end_date) : 'Running...'}</span>
            </div>
            <div class="detail-row">
                <strong>Duration:</strong>
                <span>${run.end_date ? calculateDuration(run.start_date, run.end_date) : 'N/A'}</span>
            </div>
            <div class="detail-row">
                <strong>Tasks:</strong>
                <span>
                    ✅ ${successTasks} success • 
                    ❌ ${failedTasks} failed • 
                    ⏳ ${runningTasks} running
                </span>
            </div>
            ${run.conf && Object.keys(run.conf).length > 0 ? `
                <div class="detail-row">
                    <strong>Configuration:</strong>
                    <pre style="margin-top: 0.5rem; padding: 0.5rem; background: var(--bg-secondary); border-radius: 0.375rem; font-size: 0.75rem;">${JSON.stringify(run.conf, null, 2)}</pre>
                </div>
            ` : ''}
        </div>
    `;
}

async function loadErrorLogs() {
    const container = document.getElementById('errorLogs');
    const failedTasks = state.tasks.filter(t => t.state === 'failed');

    if (failedTasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">✓</div>
                <p>No errors to display</p>
            </div>
        `;
        return;
    }

    const logs = [];
    for (const task of failedTasks) {
        const logData = await getTaskLogs(state.selectedRunId, task.task_id, task.try_number);
        if (logData) {
            logs.push({
                task: task.task_id,
                content: logData.content || 'No log content available',
                timestamp: task.end_date
            });
        }
    }

    container.innerHTML = logs.map(log => `
        <div class="log-entry">
            <div class="log-header">
                <span>❌ ${log.task}</span>
                <span>${formatDateTime(log.timestamp)}</span>
            </div>
            <div class="log-content">${escapeHtml(log.content.slice(-500))}</div>
        </div>
    `).join('');
}

function initializeChart() {
    const ctx = document.getElementById('statsChart').getContext('2d');
    state.chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Success',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Failed',
                    data: [],
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#cbd5e1'
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#94a3b8',
                        precision: 0
                    },
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)'
                    }
                },
                x: {
                    ticks: {
                        color: '#94a3b8'
                    },
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)'
                    }
                }
            }
        }
    });
}

function updateChart() {
    if (!state.chart) return;

    // Group runs by date
    const runsByDate = {};
    state.dagRuns.forEach(run => {
        const date = run.execution_date.split('T')[0];
        if (!runsByDate[date]) {
            runsByDate[date] = { success: 0, failed: 0 };
        }
        if (run.state === 'success') {
            runsByDate[date].success++;
        } else if (run.state === 'failed') {
            runsByDate[date].failed++;
        }
    });

    // Get last 7 days
    const dates = Object.keys(runsByDate).sort().slice(-7);
    const successData = dates.map(date => runsByDate[date].success);
    const failedData = dates.map(date => runsByDate[date].failed);

    state.chart.data.labels = dates;
    state.chart.data.datasets[0].data = successData;
    state.chart.data.datasets[1].data = failedData;
    state.chart.update();
}

// UI Helper Functions
function updateConnectionStatus(connected) {
    state.connected = connected;
    const indicator = document.querySelector('.status-indicator');
    const statusText = document.getElementById('statusText');

    if (connected) {
        indicator.classList.remove('disconnected');
        statusText.textContent = 'Connected to Airflow';
    } else {
        indicator.classList.add('disconnected');
        statusText.textContent = 'Disconnected from Airflow';
    }
}

function filterDagRuns(filter) {
    const items = document.querySelectorAll('.dag-run-item');
    items.forEach(item => {
        const badge = item.querySelector('.status-badge');
        const state = badge.textContent.trim();

        if (filter === 'all' || state === filter) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

function searchLogs(query) {
    const entries = document.querySelectorAll('.log-entry');
    entries.forEach(entry => {
        const content = entry.textContent.toLowerCase();
        if (content.includes(query.toLowerCase())) {
            entry.style.display = 'block';
        } else {
            entry.style.display = 'none';
        }
    });
}

function clearLogs() {
    document.getElementById('logSearch').value = '';
    searchLogs('');
}

function openTriggerModal() {
    document.getElementById('triggerModal').classList.add('active');
}

function closeTriggerModal() {
    document.getElementById('triggerModal').classList.remove('active');
}

async function submitTriggerDAG() {
    const executionDate = document.getElementById('executionDate').value;
    const configText = document.getElementById('dagConfig').value;

    try {
        const conf = JSON.parse(configText);
        if (executionDate) {
            conf.execution_date = executionDate;
        }

        await triggerDag(conf);
        closeTriggerModal();
    } catch (error) {
        showToast('Invalid JSON configuration', 'error');
    }
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function startAutoRefresh() {
    if (state.refreshTimer) {
        clearInterval(state.refreshTimer);
    }

    state.refreshTimer = setInterval(() => {
        loadDashboardData();
    }, CONFIG.refreshInterval);
}

// Utility Functions
function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatRelativeTime(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
}

function formatDuration(ms) {
    if (!ms) return 'N/A';
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
        return `${hours}h ${minutes % 60}m`;
    } else if (minutes > 0) {
        return `${minutes}m ${seconds % 60}s`;
    } else {
        return `${seconds}s`;
    }
}

function calculateDuration(startDate, endDate) {
    if (!startDate || !endDate) return 'N/A';
    const start = new Date(startDate);
    const end = new Date(endDate);
    return formatDuration(end - start);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Add CSS for detail-row
const style = document.createElement('style');
style.textContent = `
    .dag-run-details {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }
    
    .detail-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 0.5rem;
        background: var(--bg-secondary);
        border-radius: var(--radius-sm);
        gap: 1rem;
    }
    
    .detail-row strong {
        color: var(--text-muted);
        font-size: 0.875rem;
        min-width: 120px;
    }
    
    .detail-row span {
        text-align: right;
        flex: 1;
    }
`;
document.head.appendChild(style);
