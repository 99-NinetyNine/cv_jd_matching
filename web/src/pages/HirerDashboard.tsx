import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Briefcase, Users, CheckCircle, XCircle, Clock, Eye, ChevronDown, ChevronUp, Crown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../utils/api';

interface Application {
    id: number;
    cv_id: string;
    job_id: string;
    prediction_id: string;
    status: string;
    applied_at: string;
    candidate: {
        name: string;
        email: string;
        summary: string;
        skills: any[];
        work: any[];
    } | null;
}

interface Location {
    address?: string;
    postalCode?: string;
    city?: string;
    countryCode?: string;
    region?: string;
}

interface Job {
    id: number;
    job_id: string;
    title: string;
    company: string;
    location?: Location;
    created_at: string;
}

const HirerDashboard = () => {
    const navigate = useNavigate();
    const [jobs, setJobs] = useState<Job[]>([]);
    const [selectedJob, setSelectedJob] = useState<string | null>(null);
    const [applications, setApplications] = useState<Application[]>([]);
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [expandedCandidates, setExpandedCandidates] = useState<Set<number>>(new Set());
    const [loading, setLoading] = useState(false);
    const [isPremium, setIsPremium] = useState<boolean>(() => {
        const stored = localStorage.getItem('isPremium');
        return stored === 'true';
    });

    const togglePremium = () => {
        const newPremiumStatus = !isPremium;
        setIsPremium(newPremiumStatus);
        localStorage.setItem('isPremium', newPremiumStatus.toString());
    };

    useEffect(() => {
        fetchJobs();
    }, []);

    useEffect(() => {
        if (selectedJob) {
            fetchApplications(selectedJob);
        }
    }, [selectedJob, statusFilter]);

    const fetchJobs = async () => {
        try {
            const response = await api.get('/jobs');
            setJobs(response.data.jobs);
        } catch (error) {
            console.error('Failed to fetch jobs:', error);
        }
    };

    const fetchApplications = async (jobId: string) => {
        setLoading(true);
        try {
            const params = statusFilter !== 'all' ? { status_filter: statusFilter } : {};
            const response = await api.get(`/jobs/${jobId}/applications`, { params });
            setApplications(response.data.applications);
        } catch (error) {
            console.error('Failed to fetch applications:', error);
        } finally {
            setLoading(false);
        }
    };

    const logInteraction = async (jobId: string, applicationId: number, action: 'shortlisted' | 'interviewed' | 'hired' | 'rejected') => {
        try {
            await api.post('/interactions/log', {
                job_id: jobId,
                action: action,
                application_id: applicationId,
                metadata: {
                    source: 'hirer_dashboard',
                    timestamp: new Date().toISOString()
                }
            });
            console.log(`✓ Logged: ${action} for application ${applicationId}`);
        } catch (error) {
            console.error('Failed to log interaction:', error);
        }
    };

    const handleAccept = async (jobId: string, applicationId: number) => {
        try {
            await logInteraction(jobId, applicationId, 'hired');
            fetchApplications(jobId);  // Refresh
        } catch (error) {
            console.error('Failed to accept application:', error);
        }
    };

    const handleReject = async (jobId: string, applicationId: number) => {
        try {
            await logInteraction(jobId, applicationId, 'rejected');
            fetchApplications(jobId);  // Refresh
        } catch (error) {
            console.error('Failed to reject application:', error);
        }
    };

    const handleShortlist = async (jobId: string, applicationId: number) => {
        try {
            await logInteraction(jobId, applicationId, 'shortlisted');
            fetchApplications(jobId);  // Refresh to show updated status
        } catch (error) {
            console.error('Failed to shortlist application:', error);
        }
    };

    const handleInterview = async (jobId: string, applicationId: number) => {
        try {
            await logInteraction(jobId, applicationId, 'interviewed');
            fetchApplications(jobId);  // Refresh to show updated status
        } catch (error) {
            console.error('Failed to mark as interviewed:', error);
        }
    };

    const toggleCandidate = (id: number) => {
        const newExpanded = new Set(expandedCandidates);
        if (newExpanded.has(id)) {
            newExpanded.delete(id);
        } else {
            newExpanded.add(id);
        }
        setExpandedCandidates(newExpanded);
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('role');
        navigate('/login');
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'pending': return 'bg-yellow-50 text-yellow-700 border-yellow-200';
            case 'shortlisted': return 'bg-indigo-50 text-indigo-700 border-indigo-200';
            case 'interviewed': return 'bg-blue-50 text-blue-700 border-blue-200';
            case 'accepted': return 'bg-green-50 text-green-700 border-green-200';
            case 'rejected': return 'bg-red-50 text-red-700 border-red-200';
            default: return 'bg-slate-50 text-slate-700 border-slate-200';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'pending': return <Clock size={16} />;
            case 'accepted': return <CheckCircle size={16} />;
            case 'rejected': return <XCircle size={16} />;
            default: return null;
        }
    };

    return (
        <div className="min-h-screen bg-slate-50">
            {/* Navigation */}
            <nav className="bg-white shadow-sm border-b border-slate-200 px-6 py-4 flex justify-between items-center sticky top-0 z-10">
                <div className="flex items-center gap-2 font-bold text-xl">
                    <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white">
                        <Briefcase size={18} />
                    </div>
                    Hirer Dashboard
                </div>
                <div className="flex items-center gap-4">
                    <button
                        onClick={togglePremium}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all ${isPremium
                            ? 'bg-gradient-to-r from-yellow-400 to-yellow-600 text-white shadow-md'
                            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                            }`}
                    >
                        <Crown size={16} />
                        {isPremium ? 'Premium' : 'Go Premium'}
                    </button>
                    <button
                        onClick={() => navigate('/hirer/post-job')}
                        className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium text-sm"
                    >
                        Post Job
                    </button>
                    <button
                        onClick={handleLogout}
                        className="text-slate-600 hover:text-slate-900 font-medium"
                    >
                        Logout
                    </button>
                </div>
            </nav>

            <div className="max-w-7xl mx-auto px-6 py-8">
                <div className="grid grid-cols-12 gap-6">
                    {/* Jobs Sidebar */}
                    <div className="col-span-4">
                        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                <Briefcase size={20} />
                                My Jobs ({jobs.length})
                            </h2>
                            <div className="space-y-2">
                                {jobs.map(job => (
                                    <button
                                        key={job.job_id}
                                        onClick={() => setSelectedJob(job.job_id)}
                                        className={`w-full text-left p-4 rounded-lg border-2 transition-all ${selectedJob === job.job_id
                                            ? 'border-indigo-500 bg-indigo-50'
                                            : 'border-slate-200 hover:border-slate-300'
                                            }`}
                                    >
                                        <div className="font-medium text-slate-900">{job.title}</div>
                                        <div className="text-sm text-slate-500 mt-1">{job.company}</div>
                                        {job.location && (
                                            <div className="text-xs text-slate-400 mt-1">
                                                {[
                                                    job.location.city,
                                                    job.location.region,
                                                    job.location.countryCode
                                                ].filter(Boolean).join(', ') || 'Remote'}
                                            </div>
                                        )}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Applications Panel */}
                    <div className="col-span-8">
                        {selectedJob ? (
                            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                                <div className="flex justify-between items-center mb-6">
                                    <h2 className="text-lg font-semibold flex items-center gap-2">
                                        <Users size={20} />
                                        Applications ({applications.length})
                                    </h2>
                                    <div className="flex gap-2">
                                        {['all', 'pending', 'shortlisted', 'interviewed', 'accepted', 'rejected'].map(status => (
                                            <button
                                                key={status}
                                                onClick={() => setStatusFilter(status)}
                                                className={`px-3 py-1 rounded-lg text-sm font-medium capitalize ${statusFilter === status
                                                    ? 'bg-indigo-600 text-white'
                                                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                                                    }`}
                                            >
                                                {status}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {loading ? (
                                    <div className="text-center py-12">
                                        <div className="inline-block w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
                                    </div>
                                ) : applications.length === 0 ? (
                                    <div className="text-center py-12 text-slate-500">
                                        No applications found
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        {applications.map(app => (
                                            <motion.div
                                                key={app.id}
                                                initial={{ opacity: 0 }}
                                                animate={{ opacity: 1 }}
                                                className="border border-slate-200 rounded-lg overflow-hidden"
                                            >
                                                <div className="p-4">
                                                    <div className="flex justify-between items-start">
                                                        <div className="flex-1">
                                                            <div className="flex items-center gap-3">
                                                                <h3 className="font-semibold text-lg">
                                                                    {app.candidate?.name || 'Unknown'}
                                                                </h3>
                                                                <span className={`px-2 py-1 rounded-full text-xs font-medium border flex items-center gap-1 ${getStatusColor(app.status)}`}>
                                                                    {getStatusIcon(app.status)}
                                                                    {app.status}
                                                                </span>
                                                            </div>
                                                            <p className="text-sm text-slate-500 mt-1">
                                                                {app.candidate?.email}
                                                            </p>
                                                            <p className="text-sm text-slate-600 mt-2">
                                                                Applied: {new Date(app.applied_at).toLocaleDateString()}
                                                            </p>
                                                        </div>
                                                        <button
                                                            onClick={() => toggleCandidate(app.id)}
                                                            className="text-indigo-600 hover:text-indigo-700"
                                                        >
                                                            {expandedCandidates.has(app.id) ? <ChevronUp /> : <ChevronDown />}
                                                        </button>
                                                    </div>

                                                    {/* Action Buttons */}
                                                    {app.status === 'pending' && (
                                                        <div className="space-y-2 mt-4">
                                                            <div className="flex gap-2">
                                                                <button
                                                                    onClick={() => handleShortlist(app.job_id, app.id)}
                                                                    className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium text-sm flex items-center justify-center gap-2"
                                                                >
                                                                    <Eye size={16} /> Shortlist
                                                                </button>
                                                                <button
                                                                    onClick={() => handleInterview(app.job_id, app.id)}
                                                                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-sm flex items-center justify-center gap-2"
                                                                >
                                                                    <Clock size={16} /> Interview
                                                                </button>
                                                            </div>
                                                            <div className="flex gap-2">
                                                                <button
                                                                    onClick={() => handleAccept(app.job_id, app.id)}
                                                                    className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium text-sm flex items-center justify-center gap-2"
                                                                >
                                                                    <CheckCircle size={16} /> Hire
                                                                </button>
                                                                <button
                                                                    onClick={() => handleReject(app.job_id, app.id)}
                                                                    className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium text-sm flex items-center justify-center gap-2"
                                                                >
                                                                    <XCircle size={16} /> Reject
                                                                </button>
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>

                                                {/* Expanded Details */}
                                                <AnimatePresence>
                                                    {expandedCandidates.has(app.id) && app.candidate && (
                                                        < motion.div
                                                            initial={{ height: 0 }}
                                                            animate={{ height: 'auto' }}
                                                            exit={{ height: 0 }}
                                                            className="overflow-hidden bg-slate-50 border-t border-slate-200"
                                                        >
                                                            <div className="p-4 space-y-4">
                                                                {app.candidate.summary && (
                                                                    <div>
                                                                        <h4 className="font-medium text-sm text-slate-700 mb-1">Summary</h4>
                                                                        <p className="text-sm text-slate-600">{app.candidate.summary}</p>
                                                                    </div>
                                                                )}
                                                                {app.candidate.skills?.length > 0 && (
                                                                    <div>
                                                                        <h4 className="font-medium text-sm text-slate-700 mb-2">Skills</h4>
                                                                        <div className="flex flex-wrap gap-2">
                                                                            {app.candidate.skills.map((skill: any, idx: number) => (
                                                                                <span key={idx} className="px-2 py-1 bg-indigo-50 text-indigo-700 rounded text-xs">
                                                                                    {typeof skill === 'string' ? skill : skill.name}
                                                                                </span>
                                                                            ))}
                                                                        </div>
                                                                    </div>
                                                                )}
                                                                {app.candidate.work?.length > 0 && (
                                                                    <div>
                                                                        <h4 className="font-medium text-sm text-slate-700 mb-2">Recent Experience</h4>
                                                                        {app.candidate.work.map((work: any, idx: number) => (
                                                                            <div key={idx} className="mb-2">
                                                                                <div className="font-medium text-sm">{work.position} at {work.name}</div>
                                                                                <div className="text-xs text-slate-500">{work.startDate} - {work.endDate || 'Present'}</div>
                                                                            </div>
                                                                        ))}
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </motion.div>
                                                    )}
                                                </AnimatePresence>
                                            </motion.div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center">
                                <Eye size={48} className="mx-auto text-slate-300 mb-4" />
                                <h3 className="text-lg font-medium text-slate-900 mb-2">Select a Job</h3>
                                <p className="text-slate-500">Choose a job from the left to view applications</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default HirerDashboard;
