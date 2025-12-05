import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, PieChart, Pie } from 'recharts';
import { Target, MousePointer, Briefcase, TrendingUp, Users, CheckCircle } from 'lucide-react';

interface EvaluationData {
    period_days: number;
    generated_at: string;
    summary: {
        total_interactions: number;
        total_saved: number;
        total_applications: number;
        total_hired: number;
        save_to_apply_percent: number;
        direct_apply_percent: number;
        acceptance_rate_percent: number;
    };
    quality_metrics: {
        precision: number;
        recall: number;
        f1_score: number;
    };
    conversion_funnel: {
        saved: number;
        applied: number;
        hired: number;
        saved_to_apply_percent: number;
        apply_to_hire_percent: number;
    };
    intrinsic_factors: {
        skills_match_weight: number;
        experience_match_weight: number;
        education_match_weight: number;
        semantic_similarity_weight: number;
        reranker_enabled: boolean;
        nlp_skills_extraction: boolean;
        semantic_skills_matching: boolean;
    };
    extrinsic_factors: {
        avg_match_score_applied: number;
        avg_match_score_hired: number;
        peak_interaction_hour: number;
        user_engagement_score: number;
    };
    top_jobs: Array<{
        job_id: string;
        saves: number;
        applications: number;
        hired: number;
        engagement_rate: number;
    }>;
    actions_breakdown: Record<string, number>;
}

interface EvaluationTabProps {
    data: EvaluationData | null;
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

export const EvaluationTab: React.FC<EvaluationTabProps> = ({ data, loading }) => {
    if (loading) return <div className="p-8 text-center">Loading Evaluation Metrics...</div>;
    if (!data) return null;

    const funnelData = [
        { name: 'Saved', value: data.conversion_funnel.saved, fill: '#f59e0b' },
        { name: 'Applied', value: data.conversion_funnel.applied, fill: '#8b5cf6' },
        { name: 'Hired', value: data.conversion_funnel.hired, fill: '#10b981' },
    ];

    // Actions breakdown pie chart
    const actionsData = Object.entries(data.actions_breakdown).map(([name, value]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        value
    }));

    const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#6366f1'];

    return (
        <div className="space-y-8">
            {/* Header Info */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-4 rounded-xl border border-blue-100">
                <p className="text-sm text-slate-600">
                    <span className="font-medium">Evaluation Period:</span> Last {data.period_days} days |
                    <span className="font-medium ml-4">Generated:</span> {new Date(data.generated_at).toLocaleString()}
                </p>
            </div>

            {/* Key Performance Indicators */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <MetricCard
                    icon={<Target size={20} />}
                    label="Precision"
                    value={data.quality_metrics.precision.toFixed(3)}
                    subtext="Relevance of recommendations"
                    color="bg-emerald-50 text-emerald-600"
                />
                <MetricCard
                    icon={<TrendingUp size={20} />}
                    label="Recall"
                    value={data.quality_metrics.recall.toFixed(3)}
                    subtext="Coverage of relevant jobs"
                    color="bg-blue-50 text-blue-600"
                />
                <MetricCard
                    icon={<MousePointer size={20} />}
                    label="F1 Score"
                    value={data.quality_metrics.f1_score.toFixed(3)}
                    subtext="Balanced quality metric"
                    color="bg-purple-50 text-purple-600"
                />
                <MetricCard
                    icon={<CheckCircle size={20} />}
                    label="Acceptance Rate"
                    value={`${data.summary.acceptance_rate_percent}%`}
                    subtext="Applications accepted by hirers"
                    color="bg-amber-50 text-amber-600"
                />
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <MetricCard
                    icon={<Users size={20} />}
                    label="Total Interactions"
                    value={data.summary.total_interactions}
                    subtext="All user actions tracked"
                    color="bg-slate-50 text-slate-600"
                />
                <MetricCard
                    icon={<Briefcase size={20} />}
                    label="Applications"
                    value={data.summary.total_applications}
                    subtext={`${data.summary.total_hired} hired`}
                    color="bg-blue-50 text-blue-600"
                />
                <MetricCard
                    icon={<MousePointer size={20} />}
                    label="Save → Apply"
                    value={`${data.summary.save_to_apply_percent}%`}
                    subtext="Saved jobs that led to applications"
                    color="bg-purple-50 text-purple-600"
                />
                <MetricCard
                    icon={<TrendingUp size={20} />}
                    label="Direct Apply"
                    value={`${data.summary.direct_apply_percent}%`}
                    subtext="Applications without saving"
                    color="bg-green-50 text-green-600"
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Conversion Funnel */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="text-lg font-bold mb-6 text-slate-800">Conversion Funnel</h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={funnelData} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                <XAxis type="number" />
                                <YAxis dataKey="name" type="category" width={80} />
                                <Tooltip cursor={{ fill: 'transparent' }} />
                                <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={40}>
                                    {funnelData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.fill} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-4 text-center text-sm">
                        <div className="bg-slate-50 p-3 rounded-lg">
                            <span className="block text-slate-500">Saved → Apply</span>
                            <span className="font-bold text-slate-800">{data.conversion_funnel.saved_to_apply_percent}%</span>
                        </div>
                        <div className="bg-slate-50 p-3 rounded-lg">
                            <span className="block text-slate-500">Apply → Hire</span>
                            <span className="font-bold text-slate-800">{data.conversion_funnel.apply_to_hire_percent}%</span>
                        </div>
                    </div>
                </div>

                {/* Actions Breakdown */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="text-lg font-bold mb-6 text-slate-800">User Actions Breakdown</h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={actionsData}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={({ name, percent }) => `${name}: ${((percent || 0) * 100).toFixed(0)}%`}
                                    outerRadius={80}
                                    fill="#8884d8"
                                    dataKey="value"
                                >
                                    {actionsData.map((_entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Top Performing Jobs */}
            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                <h3 className="text-lg font-bold mb-6 text-slate-800">Top Performing Jobs</h3>
                <div className="overflow-auto max-h-[400px]">
                    <table className="w-full text-sm text-left">
                        <thead className="text-xs text-slate-500 uppercase bg-slate-50 sticky top-0">
                            <tr>
                                <th className="px-4 py-3">Job ID</th>
                                <th className="px-4 py-3">Saves</th>
                                <th className="px-4 py-3">Applications</th>
                                <th className="px-4 py-3">Hired</th>
                                <th className="px-4 py-3">Engagement Rate</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {data.top_jobs.map((job) => (
                                <tr key={job.job_id} className="hover:bg-slate-50">
                                    <td className="px-4 py-3 font-mono text-xs truncate max-w-[100px]" title={job.job_id}>
                                        {job.job_id.substring(0, 8)}...
                                    </td>
                                    <td className="px-4 py-3">{job.saves}</td>
                                    <td className="px-4 py-3 font-medium">{job.applications}</td>
                                    <td className="px-4 py-3 text-green-600 font-medium">{job.hired}</td>
                                    <td className="px-4 py-3">
                                        <span className="px-2 py-1 bg-emerald-50 text-emerald-700 rounded-full text-xs font-medium">
                                            {job.engagement_rate}%
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Intrinsic & Extrinsic Factors */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Intrinsic Factors */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="text-lg font-bold mb-6 text-slate-800">Intrinsic Factors (System Design)</h3>
                    <div className="space-y-3">
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Skills Match Weight</span>
                            <span className="font-mono font-bold">{data.intrinsic_factors.skills_match_weight}</span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Experience Weight</span>
                            <span className="font-mono font-bold">{data.intrinsic_factors.experience_match_weight}</span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Education Weight</span>
                            <span className="font-mono font-bold">{data.intrinsic_factors.education_match_weight}</span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Semantic Weight</span>
                            <span className="font-mono font-bold">{data.intrinsic_factors.semantic_similarity_weight}</span>
                        </div>
                      
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Reranker Enabled</span>
                            <span className={`font-bold ${data.intrinsic_factors.reranker_enabled ? 'text-green-600' : 'text-red-600'}`}>
                                {data.intrinsic_factors.reranker_enabled ? 'Yes' : 'No'}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Extrinsic Factors */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="text-lg font-bold mb-6 text-slate-800">Extrinsic Factors (User Behavior)</h3>
                    <div className="space-y-3">
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Avg Match Score (Applied)</span>
                            <span className="font-mono font-bold text-blue-600">
                                {data.extrinsic_factors.avg_match_score_applied.toFixed(3)}
                            </span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Avg Match Score (Hired)</span>
                            <span className="font-mono font-bold text-green-600">
                                {data.extrinsic_factors.avg_match_score_hired.toFixed(3)}
                            </span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">Peak Interaction Hour</span>
                            <span className="font-mono font-bold">
                                {data.extrinsic_factors.peak_interaction_hour}:00
                            </span>
                        </div>
                        <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                            <span className="text-slate-600">User Engagement Score</span>
                            <span className="font-mono font-bold text-purple-600">
                                {data.extrinsic_factors.user_engagement_score.toFixed(3)}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
