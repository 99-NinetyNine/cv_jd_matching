import { useState, useEffect } from 'react';
import { Activity, LayoutDashboard, RefreshCw, Briefcase, Database } from 'lucide-react';
import { HealthStatus } from '../components/admin/HealthStatus';
import { EvaluationTab } from '../components/admin/EvaluationTab';
import { PerformanceTab } from '../components/admin/PerformanceTab';
import { BatchJobsTable } from '../components/admin/BatchJobsTable';
import { CacheMetricsTab } from '../components/admin/CacheMetricsTab';
import { api } from '../utils/api';

const AdminDashboard = () => {
    const [activeTab, setActiveTab] = useState<'evaluation' | 'performance' | 'batches' | 'cache'>('evaluation');
    const [healthData, setHealthData] = useState<any>(null);
    const [evalData, setEvalData] = useState<any>(null);
    const [perfData, setPerfData] = useState<any>(null);
    const [cacheData, setCacheData] = useState<any>(null);
    const [batches, setBatches] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    const fetchData = async () => {
        try {
            // Fetch health first
            const healthRes = await api.get('/admin/system_health');
            setHealthData(healthRes.data);

            // Fetch other data in parallel
            const [evalRes, perfRes, cacheRes, batchesRes] = await Promise.all([
                api.get('/admin/evaluation_metrics'),
                api.get('/admin/performance_dashboard'),
                api.get('/admin/cache_metrics'),
                api.get('/admin/batches')
            ]);

            setEvalData(evalRes.data);
            setPerfData(perfRes.data);
            setCacheData(cacheRes.data);
            setBatches(batchesRes.data.batches || []);
        } catch (err) {
            console.error("Failed to fetch dashboard data", err);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleRefresh = () => {
        setRefreshing(true);
        fetchData();
    };

    const handleTriggerBatch = async (type: string) => {
        try {
            await api.post('/admin/batches/trigger', null, { params: { batch_type: type } });
            alert("Batch submission triggered!");
            handleRefresh();
        } catch (e) { alert("Failed to trigger batch"); }
    };

    const handleCheckBatchStatus = async () => {
        try {
            await api.post('/admin/batches/check');
            alert("Status check triggered!");
            handleRefresh();
        } catch (e) { alert("Failed to check status"); }
    };

    if (loading) return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50">
            <div className="text-center">
                <div className="w-12 h-12 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin mx-auto mb-4"></div>
                <p className="text-slate-500">Loading Dashboard...</p>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-slate-50 font-sans text-slate-900 p-8">
            <div className="max-w-7xl mx-auto">
                <div className="flex justify-between items-center mb-8">
                    <h1 className="text-3xl font-bold text-slate-800">System Administration</h1>
                    <button
                        onClick={handleRefresh}
                        className={`p-2 rounded-lg bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 transition-all ${refreshing ? 'animate-spin' : ''}`}
                        title="Refresh Data"
                    >
                        <RefreshCw size={20} />
                    </button>
                </div>

                {/* System Health Overview */}
                <HealthStatus data={healthData} loading={loading} />

                {/* Tabs */}
                <div className="flex gap-4 mb-8 border-b border-slate-200">
                    <button
                        onClick={() => setActiveTab('evaluation')}
                        className={`pb-4 px-2 font-medium text-sm flex items-center gap-2 transition-colors relative ${activeTab === 'evaluation' ? 'text-indigo-600' : 'text-slate-500 hover:text-slate-700'
                            }`}
                    >
                        <LayoutDashboard size={18} />
                        Evaluation Metrics
                        {activeTab === 'evaluation' && (
                            <div className="absolute bottom-0 left-0 w-full h-0.5 bg-indigo-600 rounded-t-full" />
                        )}
                    </button>
                    <button
                        onClick={() => setActiveTab('performance')}
                        className={`pb-4 px-2 font-medium text-sm flex items-center gap-2 transition-colors relative ${activeTab === 'performance' ? 'text-indigo-600' : 'text-slate-500 hover:text-slate-700'
                            }`}
                    >
                        <Activity size={18} />
                        System Performance
                        {activeTab === 'performance' && (
                            <div className="absolute bottom-0 left-0 w-full h-0.5 bg-indigo-600 rounded-t-full" />
                        )}
                    </button>
                    <button
                        onClick={() => setActiveTab('batches')}
                        className={`pb-4 px-2 font-medium text-sm flex items-center gap-2 transition-colors relative ${activeTab === 'batches' ? 'text-indigo-600' : 'text-slate-500 hover:text-slate-700'
                            }`}
                    >
                        <Briefcase size={18} />
                        Batch Processing
                        {activeTab === 'batches' && (
                            <div className="absolute bottom-0 left-0 w-full h-0.5 bg-indigo-600 rounded-t-full" />
                        )}
                    </button>
                    <button
                        onClick={() => setActiveTab('cache')}
                        className={`pb-4 px-2 font-medium text-sm flex items-center gap-2 transition-colors relative ${activeTab === 'cache' ? 'text-indigo-600' : 'text-slate-500 hover:text-slate-700'
                            }`}
                    >
                        <Database size={18} />
                        Cache Performance
                        {activeTab === 'cache' && (
                            <div className="absolute bottom-0 left-0 w-full h-0.5 bg-indigo-600 rounded-t-full" />
                        )}
                    </button>
                </div>

                {/* Tab Content */}
                <div className="mb-12">
                    {activeTab === 'evaluation' && (
                        <EvaluationTab data={evalData} loading={loading} />
                    )}
                    {activeTab === 'performance' && (
                        <PerformanceTab data={perfData} loading={loading} />
                    )}
                    {activeTab === 'batches' && (
                        <BatchJobsTable
                            batches={batches}
                            onTrigger={handleTriggerBatch}
                            onCheckStatus={handleCheckBatchStatus}
                        />
                    )}
                    {activeTab === 'cache' && (
                        <CacheMetricsTab data={cacheData} loading={loading} />
                    )}
                </div>
            </div>
        </div>
    );
};

export default AdminDashboard;
