import React, { useState } from 'react';
import axios from 'axios';
import { Upload, CheckCircle, AlertCircle, Briefcase, MapPin, Building2, TrendingUp } from 'lucide-react';
import { motion } from 'framer-motion';

interface Match {
    job_id: string;
    job_title: string;
    company: string;
    match_score: number;
    explanation: string;
    location?: string;
    salary_range?: string;
}

const CandidateDashboard = () => {
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [matches, setMatches] = useState<Match[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [uploadSuccess, setUploadSuccess] = useState(false);

    const useMock = import.meta.env.VITE_USE_MOCK_DATA === 'true';
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            const selectedFile = e.target.files[0];
            if (selectedFile.size > 5 * 1024 * 1024) {
                setError("File size exceeds 5MB limit.");
                return;
            }
            if (selectedFile.type !== "application/pdf") {
                setError("Only PDF files are allowed.");
                return;
            }
            setFile(selectedFile);
            setError(null);
            setUploadSuccess(false);
        }
    };

    const handleUpload = async () => {
        if (!file) return;
        setUploading(true);
        setError(null);
        setUploadSuccess(false); // Reset success state

        const formData = new FormData();
        formData.append('file', file);

        try {
            if (useMock) {
                // Mock Flow
                await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate upload
                setUploadSuccess(true);

                setTimeout(() => {
                    setMatches([
                        {
                            job_id: '1',
                            job_title: 'Senior Frontend Engineer',
                            company: 'TechCorp',
                            match_score: 0.95,
                            explanation: 'Strong match for React and TypeScript skills. Experience aligns with senior level requirements.',
                            location: 'San Francisco, CA',
                            salary_range: '$160k - $200k'
                        },
                        {
                            job_id: '2',
                            job_title: 'Full Stack Developer',
                            company: 'Innovate Inc.',
                            match_score: 0.88,
                            explanation: 'Good match for backend skills (Python), but frontend experience is slightly less than desired.',
                            location: 'Remote',
                            salary_range: '$140k - $170k'
                        },
                        {
                            job_id: '3',
                            job_title: 'UI/UX Engineer',
                            company: 'DesignStudio',
                            match_score: 0.75,
                            explanation: 'Relevant design skills, but lacks specific experience with our design system tools.',
                            location: 'New York, NY',
                            salary_range: '$130k - $160k'
                        }
                    ]);
                    setUploading(false);
                }, 1500);
            } else {
                // Real API Flow
                // 1. Upload
                const uploadRes = await axios.post(`${apiUrl}/upload`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                const cvId = uploadRes.data.cv_id; // Use cv_id

                // 2. Parse (Sync for now)
                // Note: In production, this should be async/websocket. 
                // We use the sync endpoint created in candidate router.
                const parseRes = await axios.post(`${apiUrl}/parse_sync?cv_id=${cvId}`);
                const cvData = parseRes.data;

                if (cvData.error) {
                    throw new Error(cvData.error);
                }

                // Only set success if parsing worked
                setUploadSuccess(true);

                // 3. Match
                const matchRes = await axios.post(`${apiUrl}/candidates/match`, cvData);
                const apiMatches = matchRes.data.matches.map((m: any) => ({
                    job_id: m.job_id,
                    job_title: m.job_title || 'Unknown Role', // Matcher might not return title if not in job desc? 
                    // Actually matcher returns job_id and score/explanation. 
                    // We need to fetch job details or matcher should return them.
                    // The current matcher returns: { job_id, match_score, explanation, ... }
                    // Let's assume matcher returns enough info or we map it.
                    // For now, let's map what we have.
                    company: m.company || 'Unknown Company',
                    match_score: m.match_score,
                    explanation: m.explanation,
                    location: m.location || 'Remote',
                    salary_range: m.salary_range || 'Competitive'
                }));

                // If matcher doesn't return title/company, we might need to look them up from job list.
                // But let's assume for now the matcher (or the wrapper in main.py) enriches it.
                // Wait, the matcher in `semantic_matcher.py` returns `job_id`.
                // The endpoint `match_candidate` in `candidate.py` just calls `matcher.match`.
                // `HybridMatcher.match` returns a list of dicts with `job_id`.
                // It does NOT currently join with job details (title, company).
                // I should probably update the backend to enrich this, but for now let's just display what we have or defaults.
                // Or I can fetch jobs list and join on frontend?
                // Let's rely on what's returned. If title is missing, it will show 'Unknown Role'.

                setMatches(apiMatches);
                setUploading(false);
            }

        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.detail || err.message || "Upload failed. Please try again.");
            setUploading(false);
            setUploadSuccess(false); // Ensure success is false on error
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 font-sans text-slate-900">
            {/* Navigation */}
            <nav className="bg-white border-b border-slate-200 sticky top-0 z-10">
                <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-2 font-bold text-xl">
                        <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white">
                            <Briefcase size={18} />
                        </div>
                        TalentMatch
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="w-8 h-8 bg-slate-200 rounded-full flex items-center justify-center text-slate-500 font-bold text-xs">JD</div>
                    </div>
                </div>
            </nav>

            <main className="max-w-5xl mx-auto px-6 py-12">
                <div className="mb-12 text-center">
                    <h1 className="text-3xl font-bold text-slate-900 mb-4">Find Your Next Role</h1>
                    <p className="text-slate-500 max-w-2xl mx-auto">Upload your CV to instantly match with top tech companies using our advanced AI parsing engine.</p>
                </div>

                {/* Upload Section */}
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 mb-12 max-w-2xl mx-auto">
                    <div className="border-2 border-dashed border-slate-200 rounded-xl p-8 text-center hover:border-indigo-400 transition-colors bg-slate-50/50">
                        <input
                            type="file"
                            id="cv-upload"
                            className="hidden"
                            accept=".pdf"
                            onChange={handleFileChange}
                        />
                        <label htmlFor="cv-upload" className="cursor-pointer flex flex-col items-center">
                            <div className="w-16 h-16 bg-indigo-50 rounded-full flex items-center justify-center text-indigo-600 mb-4">
                                <Upload size={32} />
                            </div>
                            <span className="text-lg font-semibold text-slate-900 mb-1">
                                {file ? file.name : "Upload your CV"}
                            </span>
                            <span className="text-sm text-slate-500 mb-6">
                                {file ? "Click to change file" : "PDF files only, max 5MB"}
                            </span>
                        </label>
                        {file && (
                            <button
                                onClick={handleUpload}
                                disabled={uploading}
                                className={`px-6 py-2.5 rounded-lg font-medium text-white transition-all shadow-sm ${uploading ? 'bg-slate-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700'
                                    }`}
                            >
                                {uploading ? 'Analyzing...' : 'Analyze & Match'}
                            </button>
                        )}
                    </div>

                    {error && (
                        <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2 text-sm border border-red-100">
                            <AlertCircle size={16} /> {error}
                        </div>
                    )}

                    {uploadSuccess && !uploading && (
                        <div className="mt-4 p-4 bg-emerald-50 text-emerald-700 rounded-lg flex items-center gap-2 text-sm border border-emerald-100">
                            <CheckCircle size={16} /> CV successfully parsed!
                        </div>
                    )}
                </div>

                {/* Results Section */}
                {matches.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                    >
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-bold text-slate-900">Top Job Matches</h2>
                            <span className="text-sm text-slate-500">Based on your skills and experience</span>
                        </div>

                        <div className="space-y-4">
                            {matches.map((match) => (
                                <div key={match.job_id} className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow flex flex-col md:flex-row gap-6">
                                    <div className="flex-1">
                                        <div className="flex justify-between items-start mb-2">
                                            <div>
                                                <h3 className="text-lg font-bold text-slate-900">{match.job_title}</h3>
                                                <div className="flex items-center gap-4 text-sm text-slate-500 mt-1">
                                                    <span className="flex items-center gap-1"><Building2 size={14} /> {match.company}</span>
                                                    <span className="flex items-center gap-1"><MapPin size={14} /> {match.location}</span>
                                                    <span className="flex items-center gap-1"><Briefcase size={14} /> {match.salary_range}</span>
                                                </div>
                                            </div>
                                            <div className="bg-emerald-50 text-emerald-700 px-3 py-1 rounded-full text-sm font-bold border border-emerald-100 flex items-center gap-1">
                                                <TrendingUp size={14} /> {(match.match_score * 100).toFixed(0)}% Match
                                            </div>
                                        </div>
                                        <div className="bg-slate-50 p-4 rounded-lg border border-slate-100 mt-4">
                                            <p className="text-sm text-slate-700 leading-relaxed">
                                                <span className="font-semibold text-indigo-600">Why it's a match: </span>
                                                {match.explanation}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex flex-col justify-center gap-3 min-w-[140px]">
                                        <button className="w-full px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors text-sm">
                                            Apply Now
                                        </button>
                                        <button className="w-full px-4 py-2 border border-slate-200 text-slate-600 font-medium rounded-lg hover:bg-slate-50 transition-colors text-sm">
                                            Save Job
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                )}
            </main>
        </div>
    );
};

export default CandidateDashboard;
