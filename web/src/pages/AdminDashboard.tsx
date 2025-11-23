import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';
import { Activity, Users, FileText, Briefcase, Clock, Target, AlertTriangle } from 'lucide-react';

const AdminDashboard = () => {
    const [metrics, setMetrics] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    useEffect(() => {
        const fetchMetrics = async () => {
            try {
                const token = localStorage.getItem('token');
                const res = await axios.get(`${apiUrl}/admin/metrics`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                setMetrics(res.data);
            } catch (err) {
                console.error("Failed to fetch metrics", err);
                // Fallback or redirect to login
            } finally {
                setLoading(false);
            }
        };

        fetchMetrics();
    }, []);

    if (loading) return <div className="p-8">Loading Dashboard...</div>;

    return (
        <div className="min-h-screen bg-slate-50 font-sans text-slate-900 p-8">
            <h1 className="text-3xl font-bold mb-8">System Administration</h1>

            {/* Key Metrics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <div className="flex items-center gap-4 mb-2">
                        <div className="p-3 bg-blue-50 text-blue-600 rounded-lg"><Users size={20} /></div>
                        <div>
                            <p className="text-sm text-slate-500">Total Users</p>
                            <h3 className="text-2xl font-bold">{metrics.totalUsers}</h3>
                        </div>
                    </div>
                </div>
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <div className="flex items-center gap-4 mb-2">
                        <div className="p-3 bg-purple-50 text-purple-600 rounded-lg"><FileText size={20} /></div>
                        <div>
                            <p className="text-sm text-slate-500">Total CVs</p>
                            <h3 className="text-2xl font-bold">{metrics.totalCVs}</h3>
                        </div>
                    </div>
                </div>
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <div className="flex items-center gap-4 mb-2">
                        <div className="p-3 bg-indigo-50 text-indigo-600 rounded-lg"><Briefcase size={20} /></div>
                        <div>
                            <p className="text-sm text-slate-500">Total Jobs</p>
                            <h3 className="text-2xl font-bold">{metrics.totalJobs}</h3>
                        </div>
                    </div>
                </div>
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <div className="flex items-center gap-4 mb-2">
                        <div className="p-3 bg-amber-50 text-amber-600 rounded-lg"><Clock size={20} /></div>
                        <div>
                            <p className="text-sm text-slate-500">Avg Latency</p>
                            <h3 className="text-2xl font-bold">{metrics.avgLatency}ms</h3>
                        </div>
                    </div>
                </div>
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                {/* Latency Trend */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
                        <Activity size={18} className="text-slate-400" /> System Latency Trend
                    </h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={metrics.latencyHistory}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                <XAxis dataKey="time" stroke="#64748b" fontSize={12} />
                                <YAxis stroke="#64748b" fontSize={12} />
                                <Tooltip />
                                <Line type="monotone" dataKey="latency" stroke="#6366f1" strokeWidth={2} dot={{ r: 4 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Recommendation Quality */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
                        <Target size={18} className="text-slate-400" /> Recommendation Quality
                    </h3>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={metrics.matchQuality}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                <XAxis dataKey="name" stroke="#64748b" fontSize={12} />
                                <YAxis stroke="#64748b" fontSize={12} domain={[0, 1]} />
                                <Tooltip />
                                <Bar dataKey="value" fill="#10b981" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="mt-4 text-sm text-slate-500 bg-slate-50 p-3 rounded-lg border border-slate-100">
                        <p><strong>Precision:</strong> 65% of recommendations were relevant (clicked/applied).</p>
                        <p><strong>Recall:</strong> 40% of all relevant jobs were found.</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AdminDashboard;
