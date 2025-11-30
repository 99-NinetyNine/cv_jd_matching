import React from 'react';
import { useNavigate } from 'react-router-dom';

const HirerDashboard = () => {
    const navigate = useNavigate();

    const handleLogout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('role');
        navigate('/login');
    };

    return (
        <div className="min-h-screen bg-slate-50">
            <nav className="bg-white shadow-sm border-b border-slate-200 px-6 py-4 flex justify-between items-center">
                <h1 className="text-xl font-bold text-slate-800">Hirer Dashboard</h1>
                <button
                    onClick={handleLogout}
                    className="text-slate-600 hover:text-slate-900 font-medium"
                >
                    Logout
                </button>
            </nav>
            <div className="max-w-7xl mx-auto px-6 py-8">
                <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                    <h2 className="text-lg font-semibold mb-4">Welcome, Hirer</h2>
                    <p className="text-slate-600">This is the hirer dashboard. You can manage job postings and view candidates here.</p>

                    <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        <div
                            onClick={() => navigate('/hirer/post-job')}
                            className="p-6 border border-slate-200 rounded-lg hover:border-indigo-500 transition-colors cursor-pointer"
                        >
                            <h3 className="font-medium text-slate-900 mb-2">Post a Job</h3>
                            <p className="text-sm text-slate-500">Create a new job listing to find candidates.</p>
                        </div>
                        <div className="p-6 border border-slate-200 rounded-lg hover:border-indigo-500 transition-colors cursor-pointer">
                            <h3 className="font-medium text-slate-900 mb-2">View Candidates</h3>
                            <p className="text-sm text-slate-500">Browse and search for potential candidates.</p>
                        </div>
                        <div className="p-6 border border-slate-200 rounded-lg hover:border-indigo-500 transition-colors cursor-pointer">
                            <h3 className="font-medium text-slate-900 mb-2">Analytics</h3>
                            <p className="text-sm text-slate-500">View performance metrics for your job postings.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default HirerDashboard;
