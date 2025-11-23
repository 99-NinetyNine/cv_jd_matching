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
    const [parsedData, setParsedData] = useState<any>(null);
    const [reviewing, setReviewing] = useState(false);
    const [wsConnection, setWsConnection] = useState<WebSocket | null>(null);

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

    const handleConfirm = () => {
        if (wsConnection && parsedData) {
            wsConnection.send(JSON.stringify({
                action: "confirm",
                data: parsedData
            }));
            setReviewing(false);
            setUploading(true); // Back to loading state while matching
        }
    };

    const handleUpload = async () => {
        if (!file) return;
        setUploading(true);
        setError(null);
        setUploadSuccess(false);
        setMatches([]);
        setParsedData(null);
        setReviewing(false);

        const formData = new FormData();
        formData.append('file', file);

        try {
            // 1. Upload
            const uploadRes = await axios.post(`${apiUrl}/upload`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            const cvId = uploadRes.data.cv_id;

            // 2. Connect WebSocket
            const apiBase = apiUrl.replace(/^http/, 'ws');
            const ws = new WebSocket(`${apiBase}/ws/candidate/${cvId}`);
            setWsConnection(ws);

            ws.onopen = () => {
                console.log("WS Connected");
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                console.log("WS Message:", data);

                if (data.status === "parsing_started") {
                    // Show parsing status
                } else if (data.status === "parsing_complete") {
                    setUploadSuccess(true);
                    setParsedData(data.data);
                    setReviewing(true);
                    setUploading(false);
                } else if (data.status === "matching_started") {
                    // Show matching status
                } else if (data.status === "complete") {
                    setMatches(data.matches);
                    setUploading(false);
                    ws.close();
                } else if (data.status === "error") {
                    setError(data.message);
                    setUploading(false);
                    ws.close();
                }
            };

            ws.onerror = (error) => {
                console.error("WS Error:", error);
                setError("WebSocket connection failed.");
                setUploading(false);
            };

            ws.onclose = () => {
                console.log("WS Closed");
            };

        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.detail || err.message || "Upload failed. Please try again.");
            setUploading(false);
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
                {!reviewing && matches.length === 0 && (
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
                    </div>
                )}

                {/* Review Section */}
                {reviewing && parsedData && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 mb-12 max-w-3xl mx-auto"
                    >
                        <div className="flex items-center gap-2 mb-6 text-emerald-600 font-medium">
                            <CheckCircle size={20} /> CV Parsed Successfully. Please Review.
                        </div>

                        <div className="space-y-6">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Full Name</label>
                                <input
                                    type="text"
                                    value={parsedData.basics?.name || ''}
                                    onChange={(e) => setParsedData({ ...parsedData, basics: { ...parsedData.basics, name: e.target.value } })}
                                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                                <input
                                    type="email"
                                    value={parsedData.basics?.email || ''}
                                    onChange={(e) => setParsedData({ ...parsedData, basics: { ...parsedData.basics, email: e.target.value } })}
                                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Summary</label>
                                <textarea
                                    value={parsedData.basics?.summary || ''}
                                    onChange={(e) => setParsedData({ ...parsedData, basics: { ...parsedData.basics, summary: e.target.value } })}
                                    rows={4}
                                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                />
                            </div>

                            <div className="pt-4 flex justify-end gap-3">
                                <button
                                    onClick={() => setReviewing(false)}
                                    className="px-6 py-2 border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-50"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleConfirm}
                                    className="px-6 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700"
                                >
                                    Confirm & Match
                                </button>
                            </div>
                        </div>
                    </motion.div>
                )}

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
