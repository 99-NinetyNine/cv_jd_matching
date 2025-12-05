import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend } from 'recharts';
import { Database, FileText, Cpu, Layers, Zap, TrendingUp, Activity } from 'lucide-react';

interface PerformanceData {
    period: string;
    timestamp: string;
    recommendation_performance: {
        generation_time: {
            avg_ms?: number;
            median_ms?: number;
            min_ms?: number;
            max_ms?: number;
            p50_ms?: number;
            p95_ms?: number;
            p99_ms?: number;
            sample_count?: number;
            first_time_cv_count?: number;
            recurring_cv_count?: number;
            first_time_avg_ms?: number;
            recurring_avg_ms?: number;
            data_source?: string;
            note?: string;
        };
        throughput: {
            recommendations_per_hour: number;
            recommendations_last_24h: number;
            cv_uploads_per_hour: number;
            interactions_per_hour: number;
        };
        quality_metrics: {
            precision: number;
            recall: number;
            f1_score: number;
            ctr_percent: number;
            hire_rate_percent: number;
        };
    };
    database_performance: {
        latency: {
            simple_count_ms: number;
            prediction_query_ms: number;
            vector_fetch_ms: number;
        };
        query_efficiency: string;
    };
    scalability_assessment: {
        dataset_size: {
            total_cvs: number;
            total_jobs: number;
            cvs_with_embeddings: number;
            jobs_with_embeddings: number;
            embedding_coverage_percent: number;
        };
        vector_search_ready: boolean;
        estimated_capacity: {
            note: string;
            max_concurrent_recommendations: number | string;
            db_query_efficiency: string;
        };
    };
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
    batch_jobs?: {
        total: number;
        pending: number;
        processing: number;
        completed: number;
        failed: number;
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

    // Database latency chart data
    const dbLatencyData = [
        { name: 'Simple Count', ms: data.database_performance.latency.simple_count_ms },
        { name: 'Prediction Query', ms: data.database_performance.latency.prediction_query_ms },
        { name: 'Vector Fetch', ms: data.database_performance.latency.vector_fetch_ms }
    ];

    // Recommendation generation time chart data (if available)
    const genTime = data.recommendation_performance.generation_time;
    const genTimeData = genTime.avg_ms ? [
        { name: 'Min', ms: genTime.min_ms || 0 },
        { name: 'Avg (All)', ms: genTime.avg_ms || 0 },
        { name: 'Avg (New CVs)', ms: genTime.first_time_avg_ms || 0 },
        { name: 'Avg (Recurring)', ms: genTime.recurring_avg_ms || 0 },
        { name: 'P95', ms: genTime.p95_ms || 0 },
        { name: 'P99', ms: genTime.p99_ms || 0 },
        { name: 'Max', ms: genTime.max_ms || 0 }
    ] : [];

    return (
        <div className="space-y-8">
            {/* Header Info */}
            <div className="bg-gradient-to-r from-indigo-50 to-purple-50 p-4 rounded-xl border border-indigo-100">
                <p className="text-sm text-slate-600">
                    <span className="font-medium">Period:</span> {data.period} |
                    <span className="font-medium ml-4">Last Updated:</span> {new Date(data.timestamp).toLocaleString()}
                </p>
            </div>

            {/* Top-Level KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard
                    title="Avg Gen Time"
                    value={genTime.avg_ms ? `${genTime.avg_ms}ms` : 'N/A'}
                    subValue={
                        genTime.sample_count
                            ? `${genTime.sample_count} samples${genTime.first_time_cv_count ? ` (${genTime.first_time_cv_count} new, ${genTime.recurring_cv_count} recurring)` : ''}`
                            : genTime.note
                    }
                    icon={<Zap size={20} />}
                    color="bg-yellow-50 text-yellow-600"
                />
                <StatCard
                    title="Recommendations/hr"
                    value={data.recommendation_performance.throughput.recommendations_per_hour}
                    subValue={`${data.recommendation_performance.throughput.recommendations_last_24h} in 24h`}
                    icon={<TrendingUp size={20} />}
                    color="bg-blue-50 text-blue-600"
                />
                <StatCard
                    title="DB Query Efficiency"
                    value={data.database_performance.query_efficiency}
                    subValue={`Avg: ${data.database_performance.latency.simple_count_ms}ms`}
                    icon={<Database size={20} />}
                    color="bg-emerald-50 text-emerald-600"
                />
                <StatCard
                    title="F1 Score"
                    value={data.recommendation_performance.quality_metrics.f1_score}
                    subValue={`Precision: ${data.recommendation_performance.quality_metrics.precision}`}
                    icon={<Activity size={20} />}
                    color="bg-purple-50 text-purple-600"
                />
            </div>

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
                    title="CTR"
                    value={`${data.recommendation_performance.quality_metrics.ctr_percent}%`}
                    subValue="Click-through rate"
                    icon={<Cpu size={20} />}
                    color="bg-amber-50 text-amber-600"
                />
                <StatCard
                    title="Hire Rate"
                    value={`${data.recommendation_performance.quality_metrics.hire_rate_percent}%`}
                    subValue="Application to hire"
                    icon={<TrendingUp size={20} />}
                    color="bg-green-50 text-green-600"
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Database Latency Chart */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="text-lg font-bold mb-6 text-slate-800">Database Query Latency</h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={dbLatencyData} layout="vertical" margin={{ left: 10 }}>
                                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                <XAxis type="number" unit="ms" />
                                <YAxis dataKey="name" type="category" width={120} style={{ fontSize: '12px' }} />
                                <Tooltip cursor={{ fill: 'transparent' }} />
                                <Bar dataKey="ms" fill="#10b981" radius={[0, 4, 4, 0]} barSize={30} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="mt-4 p-3 bg-slate-50 rounded-lg text-sm">
                        <span className="font-medium">Assessment:</span> {data.database_performance.query_efficiency}
                    </div>
                </div>

                {/* Recommendation Generation Time */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="text-lg font-bold mb-6 text-slate-800">Recommendation Generation Time</h3>
                    {genTimeData.length > 0 ? (
                        <div className="h-64">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={genTimeData} margin={{ left: 10, right: 10 }}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="name" style={{ fontSize: '12px' }} />
                                    <YAxis unit="ms" />
                                    <Tooltip />
                                    <Legend />
                                    <Line type="monotone" dataKey="ms" stroke="#6366f1" strokeWidth={3} dot={{ r: 6 }} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    ) : (
                        <div className="h-64 flex items-center justify-center bg-slate-50 rounded-lg">
                            <p className="text-slate-500 text-sm">{genTime.note || 'No data available'}</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Scalability & Throughput */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Throughput Metrics */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="text-lg font-bold mb-6 text-slate-800">System Throughput</h3>
                    <div className="space-y-4">
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Recommendations/hour</span>
                            <span className="font-mono font-bold text-indigo-600">
                                {data.recommendation_performance.throughput.recommendations_per_hour}
                            </span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">CV Uploads/hour</span>
                            <span className="font-mono font-bold">
                                {data.recommendation_performance.throughput.cv_uploads_per_hour}
                            </span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Interactions/hour</span>
                            <span className="font-mono font-bold">
                                {data.recommendation_performance.throughput.interactions_per_hour}
                            </span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Total (24h)</span>
                            <span className="font-mono font-bold text-emerald-600">
                                {data.recommendation_performance.throughput.recommendations_last_24h}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Scalability Assessment */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="text-lg font-bold mb-6 text-slate-800">Scalability Assessment</h3>
                    <div className="space-y-4">
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Total CVs</span>
                            <span className="font-mono font-bold">{data.scalability_assessment.dataset_size.total_cvs}</span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">CV Embeddings</span>
                            <span className="font-mono font-bold text-emerald-600">
                                {data.scalability_assessment.dataset_size.cvs_with_embeddings}
                            </span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Embedding Coverage</span>
                            <span className="font-mono font-bold text-purple-600">
                                {data.scalability_assessment.dataset_size.embedding_coverage_percent}%
                            </span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Vector Search Ready</span>
                            <span className={`font-mono font-bold ${data.scalability_assessment.vector_search_ready ? 'text-green-600' : 'text-red-600'}`}>
                                {data.scalability_assessment.vector_search_ready ? 'Yes' : 'No'}
                            </span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Max Concurrent</span>
                            <span className="font-mono font-bold text-blue-600">
                                {data.scalability_assessment.estimated_capacity.max_concurrent_recommendations}
                            </span>
                        </div>
                    </div>
                </div>
            </div>

        </div>
    );
};
