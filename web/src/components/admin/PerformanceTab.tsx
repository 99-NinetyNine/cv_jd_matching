import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Database, FileText, Cpu, Layers } from 'lucide-react';

interface PerformanceData {
    parsing: {
        total_processed: number;
        completed: number;
        failed: number;
        pending: number;
        success_rate_percent: number;
    };
    embedding: {
        total_processed: number;
        completed: number;
        failed: number;
        pending: number;
        success_rate_percent: number;
    };
    performance_metrics: {
        averages: Record<string, number>;
        p95_percentiles: Record<string, number>;
    };
    database: {
        total_cvs: number;
        total_jobs: number;
        total_predictions: number;
        total_interactions: number;
        cvs_with_embeddings: number;
        jobs_with_embeddings: number;
    };
}

interface PerformanceTabProps {
    data: PerformanceData | null;
    loading: boolean;
}

const StatCard = ({ title, value, subValue, icon, color }: any) => (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
        <div className="flex justify-between items-start mb-4">
            <div>
                <p className="text-sm text-slate-500 font-medium mb-1">{title}</p>
                <h3 className="text-2xl font-bold text-slate-800">{value}</h3>
            </div>
            <div className={`p-2 rounded-lg ${color}`}>{icon}</div>
        </div>
        {subValue && <p className="text-xs text-slate-400">{subValue}</p>}
    </div>
);

export const PerformanceTab: React.FC<PerformanceTabProps> = ({ data, loading }) => {
    if (loading) return <div className="p-8 text-center">Loading Performance Metrics...</div>;
    if (!data) return null;

    const latencyData = Object.entries(data.performance_metrics.averages)
        .filter(([key]) => key.includes('latency'))
        .map(([key, value]) => ({
            name: key.replace('_latency_ms', '').replace('avg_', '').replace('_', ' '),
            avg: value,
            p95: data.performance_metrics.p95_percentiles[key] || 0
        }));

    return (
        <div className="space-y-8">
            {/* Pipeline Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard
                    title="Parsing Success"
                    value={`${data.parsing.success_rate_percent}%`}
                    subValue={`${data.parsing.completed} / ${data.parsing.total_processed} CVs`}
                    icon={<FileText size={20} />}
                    color="bg-blue-50 text-blue-600"
                />
                <StatCard
                    title="Embedding Success"
                    value={`${data.embedding.success_rate_percent}%`}
                    subValue={`${data.embedding.completed} / ${data.embedding.total_processed} CVs`}
                    icon={<Layers size={20} />}
                    color="bg-purple-50 text-purple-600"
                />
                <StatCard
                    title="DB Latency"
                    value={`${data.performance_metrics.averages.avg_db_latency_ms || 0}ms`}
                    subValue="Average query time"
                    icon={<Database size={20} />}
                    color="bg-emerald-50 text-emerald-600"
                />
                <StatCard
                    title="Total Predictions"
                    value={data.database.total_predictions}
                    subValue="All time generated"
                    icon={<Cpu size={20} />}
                    color="bg-amber-50 text-amber-600"
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Latency Breakdown */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="text-lg font-bold mb-6 text-slate-800">System Latency Breakdown</h3>
                    <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={latencyData} layout="vertical" margin={{ left: 40 }}>
                                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                <XAxis type="number" unit="ms" />
                                <YAxis dataKey="name" type="category" width={100} style={{ fontSize: '12px', textTransform: 'capitalize' }} />
                                <Tooltip cursor={{ fill: 'transparent' }} />
                                <Bar dataKey="avg" name="Average" fill="#6366f1" radius={[0, 4, 4, 0]} barSize={20} />
                                <Bar dataKey="p95" name="P95" fill="#cbd5e1" radius={[0, 4, 4, 0]} barSize={20} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Database Stats */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="text-lg font-bold mb-6 text-slate-800">Database Statistics</h3>
                    <div className="space-y-4">
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Total CVs</span>
                            <span className="font-mono font-bold">{data.database.total_cvs}</span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">CV Embeddings</span>
                            <span className="font-mono font-bold text-emerald-600">{data.database.cvs_with_embeddings}</span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Total Jobs</span>
                            <span className="font-mono font-bold">{data.database.total_jobs}</span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Job Embeddings</span>
                            <span className="font-mono font-bold text-emerald-600">{data.database.jobs_with_embeddings}</span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Total Interactions</span>
                            <span className="font-mono font-bold">{data.database.total_interactions}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
