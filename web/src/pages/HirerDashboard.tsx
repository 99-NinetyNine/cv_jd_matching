import React, { useState } from 'react';
import axios from 'axios';
import { Plus, Users, Briefcase, Search, MoreHorizontal, Building2, TrendingUp, Calendar } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Job {
    job_id: string;
    title: string;
    company: string;
    description: string;
    requirements: string[];
    status: 'Active' | 'Closed' | 'Draft';
    applicants: number;
    posted_date: string;
}

const HirerDashboard = () => {
    const [jobs, setJobs] = useState<Job[]>([]);
    const [loading, setLoading] = useState(true);

    const useMock = import.meta.env.VITE_USE_MOCK_DATA === 'true';
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    const mockJobs: Job[] = [
        {
            job_id: '1',
            title: 'Senior Frontend Engineer',
            company: 'TechCorp',
            description: 'We are looking for...',
            requirements: ['React', 'TypeScript'],
            status: 'Active',
            applicants: 12,
            posted_date: '2025-11-20'
        },
        {
            job_id: '2',
            title: 'Product Manager',
            company: 'TechCorp',
            description: 'Lead product...',
            requirements: ['Agile', 'Strategy'],
            status: 'Active',
            applicants: 8,
            posted_date: '2025-11-18'
        },
        {
            job_id: '3',
            title: 'Data Scientist',
            company: 'TechCorp',
            description: 'Analyze data...',
            requirements: ['Python', 'ML'],
            status: 'Draft',
            applicants: 0,
            posted_date: '2025-11-21'
        }
    ];

    React.useEffect(() => {
        const fetchJobs = async () => {
            if (useMock) {
                setJobs(mockJobs);
                setLoading(false);
                return;
            }

            try {
                const response = await axios.get(`${apiUrl}/jobs`);
                const apiJobs = response.data.map((j: any) => ({
                    ...j,
                    requirements: j.requirements || [],
                    status: j.status || 'Active',
                    applicants: j.applicants || 0,
                    posted_date: j.posted_date || new Date().toISOString().split('T')[0]
                }));
                setJobs(apiJobs);
            } catch (error) {
                console.error("Failed to fetch jobs", error);
            } finally {
                setLoading(false);
            }
        };

        fetchJobs();
    }, []);

    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newJob, setNewJob] = useState({ title: '', company: '', description: '', requirements: '' });

    const handleCreateJob = async () => {
        const jobData = {
            job_id: Date.now().toString(),
            title: newJob.title,
            company: newJob.company,
            description: newJob.description,
            requirements: newJob.requirements.split(',').map(r => r.trim()),
            status: 'Active',
            applicants: 0,
            posted_date: new Date().toISOString().split('T')[0]
        };

        if (useMock) {
            setJobs([jobData as Job, ...jobs]);
        } else {
            try {
                await axios.post(`${apiUrl}/jobs`, {
                    job_id: jobData.job_id,
                    title: jobData.title,
                    company: jobData.company,
                    description: jobData.description
                });
                setJobs([jobData as Job, ...jobs]);
            } catch (error) {
                console.error("Failed to create job", error);
            }
        }

        setShowCreateModal(false);
        setNewJob({ title: '', company: '', description: '', requirements: '' });
    };

    return (
        <div className="min-h-screen bg-slate-50 font-sans flex">
            {/* Sidebar */}
            <aside className="w-64 bg-white border-r border-slate-200 hidden md:flex flex-col sticky top-0 h-screen">
                <div className="p-6 border-b border-slate-100">
                    <div className="flex items-center gap-2 text-slate-900 font-bold text-xl">
                        <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white">
                            <Briefcase size={18} />
                        </div>
                        TalentMatch
                    </div>
                </div>
                <nav className="flex-1 p-4 space-y-1">
                    <a href="#" className="flex items-center gap-3 px-4 py-3 text-indigo-600 bg-indigo-50 rounded-lg font-medium">
                        <Briefcase size={20} /> Jobs
                    </a>
                    <a href="#" className="flex items-center gap-3 px-4 py-3 text-slate-600 hover:bg-slate-50 rounded-lg font-medium transition-colors">
                        <Users size={20} /> Candidates
                    </a>
                    <a href="#" className="flex items-center gap-3 px-4 py-3 text-slate-600 hover:bg-slate-50 rounded-lg font-medium transition-colors">
                        <TrendingUp size={20} /> Analytics
                    </a>
                </nav>
                <div className="p-4 border-t border-slate-100">
                    <div className="flex items-center gap-3 px-4 py-2">
                        <div className="w-8 h-8 bg-slate-200 rounded-full flex items-center justify-center text-slate-500 font-bold">TC</div>
                        <div>
                            <div className="text-sm font-medium text-slate-900">TechCorp Inc.</div>
                            <div className="text-xs text-slate-500">Enterprise Plan</div>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-auto">
                <header className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between sticky top-0 z-10">
                    <h1 className="text-2xl font-bold text-slate-900">Job Postings</h1>
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="bg-indigo-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-indigo-700 transition-colors flex items-center gap-2 shadow-sm"
                    >
                        <Plus size={18} /> Post New Job
                    </button>
                </header>

                <div className="p-8">
                    {/* Stats Row */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                            <div className="text-slate-500 text-sm font-medium mb-2">Total Active Jobs</div>
                            <div className="text-3xl font-bold text-slate-900">{jobs.filter(j => j.status === 'Active').length}</div>
                        </div>
                        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                            <div className="text-slate-500 text-sm font-medium mb-2">Total Applicants</div>
                            <div className="text-3xl font-bold text-slate-900">{jobs.reduce((acc, job) => acc + (job.applicants || 0), 0)}</div>
                        </div>
                        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                            <div className="text-slate-500 text-sm font-medium mb-2">Avg. Time to Hire</div>
                            <div className="text-3xl font-bold text-slate-900">--</div>
                            <div className="text-slate-400 text-xs font-medium mt-2">Not enough data</div>
                        </div>
                    </div>

                    {/* Jobs Table */}
                    <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
                        <div className="p-4 border-b border-slate-200 flex items-center gap-4">
                            <div className="relative flex-1 max-w-md">
                                <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                                <input
                                    type="text"
                                    placeholder="Search jobs..."
                                    className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                                />
                            </div>
                            <div className="flex gap-2">
                                <button className="px-3 py-2 border border-slate-200 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-50">Filter</button>
                                <button className="px-3 py-2 border border-slate-200 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-50">Sort</button>
                            </div>
                        </div>
                        <table className="w-full text-left">
                            <thead className="bg-slate-50 text-slate-500 text-xs uppercase font-semibold">
                                <tr>
                                    <th className="px-6 py-4">Job Title</th>
                                    <th className="px-6 py-4">Status</th>
                                    <th className="px-6 py-4">Applicants</th>
                                    <th className="px-6 py-4">Posted Date</th>
                                    <th className="px-6 py-4 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {loading ? (
                                    <tr><td colSpan={5} className="px-6 py-4 text-center">Loading...</td></tr>
                                ) : jobs.map((job) => (
                                    <tr key={job.job_id} className="hover:bg-slate-50 transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="font-medium text-slate-900">{job.title}</div>
                                            <div className="text-xs text-slate-500">{job.company} &bull; {job.requirements.slice(0, 2).join(', ')}</div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${job.status === 'Active' ? 'bg-emerald-100 text-emerald-800' :
                                                job.status === 'Draft' ? 'bg-slate-100 text-slate-800' :
                                                    'bg-amber-100 text-amber-800'
                                                }`}>
                                                {job.status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-2">
                                                <Users size={16} className="text-slate-400" />
                                                <span className="text-slate-700 font-medium">{job.applicants}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-slate-500 text-sm">
                                            {job.posted_date}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <button className="text-slate-400 hover:text-indigo-600 transition-colors">
                                                <MoreHorizontal size={20} />
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </main>

            {/* Create Job Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="bg-white rounded-xl shadow-xl w-full max-w-lg overflow-hidden"
                    >
                        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center">
                            <h3 className="text-lg font-bold text-slate-900">Post New Job</h3>
                            <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-slate-600">&times;</button>
                        </div>
                        <div className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Job Title</label>
                                <input
                                    type="text"
                                    className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
                                    value={newJob.title}
                                    onChange={(e) => setNewJob({ ...newJob, title: e.target.value })}
                                    placeholder="e.g. Senior Product Designer"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Company</label>
                                <input
                                    type="text"
                                    className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
                                    value={newJob.company}
                                    onChange={(e) => setNewJob({ ...newJob, company: e.target.value })}
                                    placeholder="e.g. TechCorp Inc."
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                                <textarea
                                    className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all h-32 resize-none"
                                    value={newJob.description}
                                    onChange={(e) => setNewJob({ ...newJob, description: e.target.value })}
                                    placeholder="Describe the role..."
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Requirements (comma separated)</label>
                                <input
                                    type="text"
                                    className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all"
                                    value={newJob.requirements}
                                    onChange={(e) => setNewJob({ ...newJob, requirements: e.target.value })}
                                    placeholder="e.g. React, TypeScript, Figma"
                                />
                            </div>
                        </div>
                        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end gap-3">
                            <button
                                onClick={() => setShowCreateModal(false)}
                                className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-100 rounded-lg transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleCreateJob}
                                className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors shadow-sm"
                            >
                                Create Job
                            </button>
                        </div>
                    </motion.div>
                </div>
            )}
        </div>
    );
};

export default HirerDashboard;
