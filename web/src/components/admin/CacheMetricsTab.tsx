import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { Database, Activity, HardDrive, Users, Zap, TrendingUp, AlertCircle } from 'lucide-react';

interface CacheData {
    timestamp: string;
    status: 'healthy' | 'degraded' | 'poor' | 'error';
    performance: {
        hit_rate_percent: number;
        hits: number;
        misses: number;
        total_requests: number;
        cache_latency_ms: number;
        efficiency_score: number;
    };
    memory: {
        used_memory_human: string;
        used_memory_bytes: number;
        max_memory_bytes: number;
        memory_usage_percent: number;
        fragmentation_ratio: number;
    };
    keys: {
        total_keys: number;
        by_pattern: Record<string, number>;
        evicted_keys: number;
        expired_keys: number;
    };
    connections: {
        connected_clients: number;
        blocked_clients: number;
        total_connections_received: number;
    };
    uptime: {
        uptime_seconds: number;
        uptime_days: number;
    };
    recommendations: string[];
    message?: string;
}

interface CacheMetricsTabProps {
    data: CacheData | null;
    loading: boolean;
}

const MetricCard = ({ icon, label, value, subtext, color }: any) => (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
        <div className="flex items-center gap-4 mb-3">
            <div className={`p-3 rounded-lg ${color}`}>{icon}</div>
            <div>
                <p className="text-sm text-slate-500 font-medium">{label}</p>
                <h3 className="text-2xl font-bold text-slate-800">{value}</h3>
            </div>
        </div>
        {subtext && <p className="text-xs text-slate-400 mt-1">{subtext}</p>}
    </div>
);

const StatusBadge = ({ status }: { status: string }) => {
    const styles: Record<string, string> = {
        healthy: 'bg-emerald-100 text-emerald-700',
        degraded: 'bg-amber-100 text-amber-700',
        poor: 'bg-red-100 text-red-700',
        error: 'bg-red-100 text-red-700',
    };

    return (
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${styles[status] || 'bg-slate-100 text-slate-600'}`}>
            {status.toUpperCase()}
        </span>
    );
};

export const CacheMetricsTab: React.FC<CacheMetricsTabProps> = ({ data, loading }) => {
    if (loading) return <div className="p-8 text-center">Loading Cache Metrics...</div>;

    if (!data) return null;

    if (data.status === 'error') {
        return (
            <div className="p-8 text-center">
                <AlertCircle className="mx-auto mb-4 text-red-500" size={48} />
                <h3 className="text-xl font-bold text-slate-800 mb-2">Redis Unavailable</h3>
                <p className="text-slate-600">{data.message}</p>
            </div>
        );
    }

    // Prepare data for hit/miss pie chart
    const hitMissData = [
        { name: 'Hits', value: data.performance.hits, fill: '#10b981' },
        { name: 'Misses', value: data.performance.misses, fill: '#ef4444' }
    ];

    // Prepare data for keys distribution bar chart
    const keysData = Object.entries(data.keys.by_pattern).map(([name, value]) => ({
        name: name.replace(/_/g, ' '),
        count: value
    }));

    const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444'];

    return (
        <div className="space-y-8">
            {/* Header Status */}
            <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-6 rounded-xl border border-purple-100">
                <div className="flex justify-between items-center">
                    <div>
                        <h3 className="text-lg font-bold text-slate-800">Redis Cache Status</h3>
                        <p className="text-sm text-slate-600 mt-1">
                            Last updated: {new Date(data.timestamp).toLocaleString()}
                        </p>
                    </div>
                    <StatusBadge status={data.status} />
                </div>
            </div>

            {/* Key Performance Indicators */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <MetricCard
                    icon={<TrendingUp size={20} />}
                    label="Hit Rate"
                    value={`${data.performance.hit_rate_percent}%`}
                    subtext={`${data.performance.hits} hits, ${data.performance.misses} misses`}
                    color="bg-emerald-50 text-emerald-600"
                />
                <MetricCard
                    icon={<Zap size={20} />}
                    label="Efficiency Score"
                    value={data.performance.efficiency_score}
                    subtext="Overall cache performance"
                    color="bg-blue-50 text-blue-600"
                />
                <MetricCard
                    icon={<HardDrive size={20} />}
                    label="Memory Usage"
                    value={data.memory.used_memory_human}
                    subtext={`${data.memory.memory_usage_percent}% of capacity`}
                    color="bg-purple-50 text-purple-600"
                />
                <MetricCard
                    icon={<Database size={20} />}
                    label="Total Keys"
                    value={data.keys.total_keys}
                    subtext={`${data.keys.evicted_keys} evicted`}
                    color="bg-amber-50 text-amber-600"
                />
            </div>

            {/* Performance Details */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <MetricCard
                    icon={<Activity size={20} />}
                    label="Cache Latency"
                    value={`${data.performance.cache_latency_ms}ms`}
                    subtext="Response time"
                    color="bg-green-50 text-green-600"
                />
                <MetricCard
                    icon={<Users size={20} />}
                    label="Connected Clients"
                    value={data.connections.connected_clients}
                    subtext={`${data.connections.total_connections_received} total received`}
                    color="bg-indigo-50 text-indigo-600"
                />
                <MetricCard
                    icon={<Database size={20} />}
                    label="Expired Keys"
                    value={data.keys.expired_keys}
                    subtext="Auto-expired by TTL"
                    color="bg-slate-50 text-slate-600"
                />
                <MetricCard
                    icon={<Activity size={20} />}
                    label="Uptime"
                    value={`${data.uptime.uptime_days}d`}
                    subtext={`${data.uptime.uptime_seconds}s total`}
                    color="bg-teal-50 text-teal-600"
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Hit/Miss Distribution */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="text-lg font-bold mb-6 text-slate-800">Hit/Miss Distribution</h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={hitMissData}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={({ name, percent }) => `${name}: ${((percent || 0) * 100).toFixed(1)}%`}
                                    outerRadius={80}
                                    fill="#8884d8"
                                    dataKey="value"
                                >
                                    {hitMissData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.fill} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-4">
                        <div className="text-center p-3 bg-emerald-50 rounded-lg">
                            <div className="text-2xl font-bold text-emerald-700">{data.performance.hits}</div>
                            <div className="text-xs text-emerald-600">Cache Hits</div>
                        </div>
                        <div className="text-center p-3 bg-red-50 rounded-lg">
                            <div className="text-2xl font-bold text-red-700">{data.performance.misses}</div>
                            <div className="text-xs text-red-600">Cache Misses</div>
                        </div>
                    </div>
                </div>

                {/* Keys Distribution */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="text-lg font-bold mb-6 text-slate-800">Keys by Pattern</h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={keysData} layout="vertical" margin={{ left: 10 }}>
                                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                <XAxis type="number" />
                                <YAxis dataKey="name" type="category" width={120} style={{ fontSize: '12px', textTransform: 'capitalize' }} />
                                <Tooltip />
                                <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={30}>
                                    {keysData.map((_entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Memory Details */}
            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                <h3 className="text-lg font-bold mb-6 text-slate-800">Memory Statistics</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="p-4 bg-slate-50 rounded-lg">
                        <div className="text-sm text-slate-500 mb-1">Used Memory</div>
                        <div className="text-xl font-bold text-slate-800">{data.memory.used_memory_human}</div>
                    </div>
                    <div className="p-4 bg-slate-50 rounded-lg">
                        <div className="text-sm text-slate-500 mb-1">Usage %</div>
                        <div className="text-xl font-bold text-slate-800">{data.memory.memory_usage_percent}%</div>
                    </div>
                    <div className="p-4 bg-slate-50 rounded-lg">
                        <div className="text-sm text-slate-500 mb-1">Fragmentation</div>
                        <div className="text-xl font-bold text-slate-800">{data.memory.fragmentation_ratio.toFixed(2)}</div>
                    </div>
                    <div className="p-4 bg-slate-50 rounded-lg">
                        <div className="text-sm text-slate-500 mb-1">Max Memory</div>
                        <div className="text-xl font-bold text-slate-800">
                            {data.memory.max_memory_bytes > 0
                                ? `${(data.memory.max_memory_bytes / 1024 / 1024).toFixed(0)}MB`
                                : 'Unlimited'}
                        </div>
                    </div>
                </div>
            </div>

            {/* Recommendations */}
            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                <h3 className="text-lg font-bold mb-4 text-slate-800">Recommendations</h3>
                <div className="space-y-2">
                    {data.recommendations.map((rec, index) => (
                        <div key={index} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
                            <span className="text-lg">{rec.includes('✅') ? '✅' : rec.includes('🔴') ? '🔴' : '⚠️'}</span>
                            <span className="text-sm text-slate-700">{rec.replace(/[✅🔴⚠️]/g, '').trim()}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};
