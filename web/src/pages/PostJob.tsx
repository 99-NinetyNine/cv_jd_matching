import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const PostJob = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [formData, setFormData] = useState({
        title: '',
        company: '',
        description: '',
        role: '',
        experience: '',
        qualifications: '',
        skills: '', // Comma separated
        salary_range: '',
        benefits: '', // Comma separated
        location: '',
        country: '',
        work_type: 'Full-Time',
        company_size: '',
        preference: '',
        contact_person: '',
        contact: '',
        job_portal: '',
        responsibilities: '', // Comma separated
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            const token = localStorage.getItem('token');
            if (!token) {
                navigate('/login');
                return;
            }

            // Process lists - skills need to be objects with name, level, keywords
            const payload = {
                ...formData,
                skills: formData.skills.split(',').map(s => ({
                    name: s.trim(),
                    level: '',
                    keywords: []
                })).filter(s => s.name),
                benefits: formData.benefits.split(',').map(s => s.trim()).filter(Boolean),
                responsibilities: formData.responsibilities.split(',').map(s => s.trim()).filter(Boolean),
                qualifications: formData.qualifications.split(',').map(s => s.trim()).filter(Boolean),
                company_size: formData.company_size ? parseInt(formData.company_size) : undefined,
                job_posting_date: new Date().toISOString()
            };

            const response = await fetch('http://localhost:8000/jobs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Failed to post job');
            }

            navigate('/hirer');
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto">
                <div className="bg-white shadow-sm rounded-lg border border-slate-200 overflow-hidden">
                    <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center">
                        <h1 className="text-xl font-bold text-slate-900">Post a New Job</h1>
                        <button
                            onClick={() => navigate('/hirer')}
                            className="text-slate-600 hover:text-slate-900"
                        >
                            Cancel
                        </button>
                    </div>

                    <form onSubmit={handleSubmit} className="p-6 space-y-6">
                        {error && (
                            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative">
                                {error}
                            </div>
                        )}

                        {/* Core Info */}
                        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                            <div className="col-span-2">
                                <label className="block text-sm font-medium text-slate-700">Job Title *</label>
                                <input
                                    type="text"
                                    name="title"
                                    required
                                    value={formData.title}
                                    onChange={handleChange}
                                    className="mt-1 block w-full rounded-md border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-700">Company Name *</label>
                                <input
                                    type="text"
                                    name="company"
                                    required
                                    value={formData.company}
                                    onChange={handleChange}
                                    className="mt-1 block w-full rounded-md border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-700">Role</label>
                                <input
                                    type="text"
                                    name="role"
                                    value={formData.role}
                                    onChange={handleChange}
                                    className="mt-1 block w-full rounded-md border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
                                />
                            </div>
                        </div>

                        {/* Description */}
                        <div>
                            <label className="block text-sm font-medium text-slate-700">Job Description *</label>
                            <textarea
                                name="description"
                                required
                                rows={4}
                                value={formData.description}
                                onChange={handleChange}
                                className="mt-1 block w-full rounded-md border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
                            />
                        </div>

                        {/* Details */}
                        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                            <div>
                                <label className="block text-sm font-medium text-slate-700">Experience</label>
                                <input
                                    type="text"
                                    name="experience"
                                    placeholder="e.g. 5 to 10 Years"
                                    value={formData.experience}
                                    onChange={handleChange}
                                    className="mt-1 block w-full rounded-md border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-700">Salary Range</label>
                                <input
                                    type="text"
                                    name="salary_range"
                                    placeholder="e.g. $55K-$84K"
                                    value={formData.salary_range}
                                    onChange={handleChange}
                                    className="mt-1 block w-full rounded-md border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-700">Location</label>
                                <input
                                    type="text"
                                    name="location"
                                    value={formData.location}
                                    onChange={handleChange}
                                    className="mt-1 block w-full rounded-md border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-700">Work Type</label>
                                <select
                                    name="work_type"
                                    value={formData.work_type}
                                    onChange={handleChange}
                                    className="mt-1 block w-full rounded-md border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
                                >
                                    <option value="Full-Time">Full-Time</option>
                                    <option value="Part-Time">Part-Time</option>
                                    <option value="Contract">Contract</option>
                                    <option value="Internship">Internship</option>
                                </select>
                            </div>
                        </div>

                        {/* Lists */}
                        <div>
                            <label className="block text-sm font-medium text-slate-700">Skills (comma separated)</label>
                            <input
                                type="text"
                                name="skills"
                                placeholder="Python, React, SQL"
                                value={formData.skills}
                                onChange={handleChange}
                                className="mt-1 block w-full rounded-md border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700">Benefits (comma separated)</label>
                            <input
                                type="text"
                                name="benefits"
                                placeholder="Health Insurance, Remote Work"
                                value={formData.benefits}
                                onChange={handleChange}
                                className="mt-1 block w-full rounded-md border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700">Responsibilities (comma separated)</label>
                            <textarea
                                name="responsibilities"
                                rows={3}
                                placeholder="Lead team, Write code, Review PRs"
                                value={formData.responsibilities}
                                onChange={handleChange}
                                className="mt-1 block w-full rounded-md border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm border p-2"
                            />
                        </div>

                        <div className="pt-4 flex justify-end">
                            <button
                                type="submit"
                                disabled={loading}
                                className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                            >
                                {loading ? 'Posting...' : 'Post Job'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default PostJob;
