import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Target, MousePointer, Briefcase, TrendingUp } from 'lucide-react';

interface EvaluationData {
    summary: {
        ctr_percent: number;
        application_rate_percent: number;
        acceptance_rate_percent: number;
        total_interactions: number;
    };
    quality_metrics: {
        precision: number;
        recall: number;
        f1_score: number;
    };
    conversion_funnel: {
        viewed: number;
        applied: number;
        hired: number;
        view_to_apply_percent: number;
        apply_to_hire_percent: number;
    };
    top_jobs: any[];
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
        { name: 'Viewed', value: data.conversion_funnel.viewed, fill: '#6366f1' },
        { name: 'Applied', value: data.conversion_funnel.applied, fill: '#8b5cf6' },
        { name: 'Hired', value: data.conversion_funnel.hired, fill: '#10b981' },
    ];

    return (
        <div className="space-y-8">
            {/* Key Performance Indicators */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <MetricCard
                    icon={<MousePointer size={20} />}
                    label="CTR"
                    value={`${data.summary.ctr_percent}%`}
                    subtext="Click-through rate on recommendations"
                    color="bg-blue-50 text-blue-600"
                />
                <MetricCard
                    icon={<Briefcase size={20} />}
                    label="Application Rate"
                    value={`${data.summary.application_rate_percent}%`}
                    subtext="Views resulting in applications"
                    color="bg-purple-50 text-purple-600"
                />
                <MetricCard
                    icon={<Target size={20} />}
                    label="Precision"
                    value={data.quality_metrics.precision}
                    subtext="Relevance of recommendations"
                    color="bg-emerald-50 text-emerald-600"
                />
                <MetricCard
                    icon={<TrendingUp size={20} />}
                    label="F1 Score"
                    value={data.quality_metrics.f1_score}
                    subtext="Balance of precision and recall"
                    color="bg-amber-50 text-amber-600"
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
                            <span className="block text-slate-500">View → Apply</span>
                            <span className="font-bold text-slate-800">{data.conversion_funnel.view_to_apply_percent}%</span>
                        </div>
                        <div className="bg-slate-50 p-3 rounded-lg">
                            <span className="block text-slate-500">Apply → Hire</span>
                            <span className="font-bold text-slate-800">{data.conversion_funnel.apply_to_hire_percent}%</span>
                        </div>
                    </div>
                </div>

                {/* Top Jobs */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="text-lg font-bold mb-6 text-slate-800">Top Performing Jobs</h3>
                    <div className="overflow-auto max-h-[340px]">
                        <table className="w-full text-sm text-left">
                            <thead className="text-xs text-slate-500 uppercase bg-slate-50 sticky top-0">
                                <tr>
                                    <th className="px-4 py-3">Job ID</th>
                                    <th className="px-4 py-3">Views</th>
                                    <th className="px-4 py-3">Applications</th>
                                    <th className="px-4 py-3">Eng. Rate</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {data.top_jobs.map((job: any) => (
                                    <tr key={job.job_id} className="hover:bg-slate-50">
                                        <td className="px-4 py-3 font-mono text-xs truncate max-w-[100px]" title={job.job_id}>
                                            {job.job_id.substring(0, 8)}...
                                        </td>
                                        <td className="px-4 py-3">{job.views}</td>
                                        <td className="px-4 py-3">{job.applications}</td>
                                        <td className="px-4 py-3 text-emerald-600 font-medium">{job.engagement_rate}%</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
};
