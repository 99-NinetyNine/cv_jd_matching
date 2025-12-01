import React, { useState, useCallback, memo } from 'react';
import axios from 'axios';
import { Upload, CheckCircle, AlertCircle, Briefcase, MapPin, Building2, TrendingUp, ChevronDown, ChevronUp, Plus, Trash2, Eye, Send, Crown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Match {
    job_id: string;
    job_title: string;
    company: string;
    match_score: number;
    explanation?: string | null;
    location?: string;
    salary_range?: string;
}

type ProcessingStatus = 'idle' | 'uploading' | 'parsing' | 'reviewing' | 'matching' | 'complete';

const CandidateDashboard = () => {
    const [file, setFile] = useState<File | null>(null);
    const [status, setStatus] = useState<ProcessingStatus>('idle');
    const [matches, setMatches] = useState<Match[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [parsedData, setParsedData] = useState<any>(null);
    const [wsConnection, setWsConnection] = useState<WebSocket | null>(null);
    const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['basics']));
    const [cvId, setCvId] = useState<string | null>(null);
    const [predictionId, setPredictionId] = useState<string | null>(null);
    const [isPremium, setIsPremium] = useState<boolean>(() => {
        const stored = localStorage.getItem('isPremium');
        return stored === 'true';
    });

    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    const togglePremium = () => {
        const newPremiumStatus = !isPremium;
        setIsPremium(newPremiumStatus);
        localStorage.setItem('isPremium', newPremiumStatus.toString());
    };

    const toggleSection = useCallback((section: string) => {
        setExpandedSections(prev => {
            const newExpanded = new Set(prev);
            if (newExpanded.has(section)) {
                newExpanded.delete(section);
            } else {
                newExpanded.add(section);
            }
            return newExpanded;
        });
    }, []);

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
        }
    };

    const handleConfirm = () => {
        if (wsConnection && parsedData) {
            wsConnection.send(JSON.stringify({
                action: "confirm",
                data: parsedData
            }));
            setStatus('matching');
        }
    };

    const logInteraction = async (jobId: string, action: 'viewed' | 'applied' | 'saved') => {
        if (!cvId) return;

        try {
            await axios.post(`${apiUrl}/interact`, {
                user_id: cvId, // Using CV ID as user identifier for now
                job_id: jobId,
                action: action,
                strategy: 'pgvector',
                prediction_id: predictionId,
                cv_id: cvId
            });
            console.log(`✓ Logged: ${action} for job ${jobId}`);
        } catch (err) {
            console.error('Failed to log interaction:', err);
        }
    };

    const handleApply = async (jobId: string) => {
        await logInteraction(jobId, 'applied');
        // Silent - no alert
    };

    const handleSaveJob = async (jobId: string) => {
        await logInteraction(jobId, 'saved');
        // Silent - no alert
    };

    const handleUpload = async () => {
        if (!file) return;
        setStatus('uploading');
        setError(null);
        setMatches([]);
        setParsedData(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            // 1. Upload
            const uploadRes = await axios.post(`${apiUrl}/upload`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            const uploadedCvId = uploadRes.data.cv_id;
            setCvId(uploadedCvId);

            // 2. Connect WebSocket
            const apiBase = apiUrl.replace(/^http/, 'ws');
            const ws = new WebSocket(`${apiBase}/ws/candidate/${uploadedCvId}`);
            setWsConnection(ws);

            ws.onopen = () => {
                console.log("WS Connected");
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                console.log("WS Message:", data);

                if (data.status === "parsing_started") {
                    setStatus('parsing');
                } else if (data.status === "parsing_complete") {
                    setParsedData(data.data);
                    setStatus('reviewing');
                } else if (data.status === "matching_started") {
                    setStatus('matching');
                } else if (data.status === "complete") {
                    setMatches(data.matches);
                    setStatus('complete');
                    // Store prediction_id from backend
                    if (data.prediction_id) {
                        setPredictionId(data.prediction_id);
                        console.log(`✓ Prediction ID: ${data.prediction_id}`);
                    }
                    // Log 'viewed' for all matches with prediction_id
                    data.matches.forEach((match: Match) => {
                        logInteraction(match.job_id, 'viewed');
                    });
                    ws.close();
                } else if (data.status === "error") {
                    setError(data.message);
                    setStatus('idle');
                    ws.close();
                }
            };

            ws.onerror = (error) => {
                console.error("WS Error:", error);
                setError("WebSocket connection failed.");
                setStatus('idle');
            };

            ws.onclose = () => {
                console.log("WS Closed");
            };

        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.detail || err.message || "Upload failed. Please try again.");
            setStatus('idle');
        }
    };

    const updateBasics = useCallback((field: string, value: any) => {
        setParsedData((prev: any) => ({
            ...prev,
            basics: { ...prev.basics, [field]: value }
        }));
    }, []);

    const updateArrayItem = useCallback((section: string, index: number, field: string, value: any) => {
        setParsedData((prev: any) => {
            const newArray = [...(prev[section] || [])];
            newArray[index] = { ...newArray[index], [field]: value };
            return { ...prev, [section]: newArray };
        });
    }, []);

    const addArrayItem = useCallback((section: string, template: any) => {
        setParsedData((prev: any) => ({
            ...prev,
            [section]: [...(prev[section] || []), template]
        }));
    }, []);

    const removeArrayItem = useCallback((section: string, index: number) => {
        setParsedData((prev: any) => ({
            ...prev,
            [section]: (prev[section] || []).filter((_: any, i: number) => i !== index)
        }));
    }, []);

    const StatusIndicator = memo(() => {
        const steps = [
            { key: 'uploading', label: 'Uploading' },
            { key: 'parsing', label: 'Parsing' },
            { key: 'reviewing', label: 'Review' },
            { key: 'matching', label: 'Matching' },
            { key: 'complete', label: 'Complete' }
        ];

        const currentIndex = steps.findIndex(s => s.key === status);

        return (
            <div className="flex items-center justify-center gap-2 mb-8">
                {steps.map((step, index) => (
                    <React.Fragment key={step.key}>
                        <div className="flex flex-col items-center">
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all ${index < currentIndex ? 'bg-emerald-500 text-white' :
                                index === currentIndex ? 'bg-indigo-600 text-white animate-pulse' :
                                    'bg-slate-200 text-slate-400'
                                }`}>
                                {index < currentIndex ? '✓' : index + 1}
                            </div>
                            <span className={`text-xs mt-1 ${index <= currentIndex ? 'text-slate-700 font-medium' : 'text-slate-400'}`}>
                                {step.label}
                            </span>
                        </div>
                        {index < steps.length - 1 && (
                            <div className={`w-12 h-1 rounded ${index < currentIndex ? 'bg-emerald-500' : 'bg-slate-200'}`} />
                        )}
                    </React.Fragment>
                ))}
            </div>
        );
    });

    const CollapsibleSection = memo(({ title, isExpanded, onToggle, children }: any) => (
        <div className="border border-slate-200 rounded-lg overflow-hidden mb-4">
            <button
                onClick={onToggle}
                className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 flex items-center justify-between transition-colors"
            >
                <span className="font-semibold text-slate-700">{title}</span>
                {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </button>
            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ height: 0 }}
                        animate={{ height: 'auto' }}
                        exit={{ height: 0 }}
                        className="overflow-hidden"
                    >
                        <div className="p-4 space-y-4">
                            {children}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    ));

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
                        <div className="w-8 h-8 bg-slate-200 rounded-full flex items-center justify-center text-slate-500 font-bold text-xs">JD</div>
                    </div>
                </div>
            </nav>

            <main className="max-w-5xl mx-auto px-6 py-12">
                <div className="mb-12 text-center">
                    <h1 className="text-3xl font-bold text-slate-900 mb-4">Find Your Next Role</h1>
                    <p className="text-slate-500 max-w-2xl mx-auto">Upload your CV to instantly match with top tech companies using our advanced AI parsing engine.</p>
                </div>

                {/* Status Indicator */}
                {status !== 'idle' && status !== 'complete' && <StatusIndicator />}

                {/* Upload Section */}
                {status === 'idle' && matches.length === 0 && (
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
                                    disabled={status !== 'idle'}
                                    className={`px-6 py-2.5 rounded-lg font-medium text-white transition-all shadow-sm ${status !== 'idle' ? 'bg-slate-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700'
                                        }`}
                                >
                                    Analyze & Match
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
                {status === 'reviewing' && parsedData && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 mb-12 max-w-4xl mx-auto"
                    >
                        <div className="flex items-center gap-2 mb-6 text-emerald-600 font-medium">
                            <CheckCircle size={20} /> CV Parsed Successfully. Please Review and Edit.
                        </div>

                        {/* Basics Section */}
                        <CollapsibleSection
                            title="Basic Information"
                            isExpanded={expandedSections.has('basics')}
                            onToggle={() => toggleSection('basics')}
                        >
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-1">Full Name</label>
                                    <input
                                        type="text"
                                        value={parsedData.basics?.name || ''}
                                        onChange={(e) => updateBasics('name', e.target.value)}
                                        className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                                    <input
                                        type="email"
                                        value={parsedData.basics?.email || ''}
                                        onChange={(e) => updateBasics('email', e.target.value)}
                                        className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-1">Phone</label>
                                    <input
                                        type="tel"
                                        value={parsedData.basics?.phone || ''}
                                        onChange={(e) => updateBasics('phone', e.target.value)}
                                        className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-1">Job Title/Label</label>
                                    <input
                                        type="text"
                                        value={parsedData.basics?.label || ''}
                                        onChange={(e) => updateBasics('label', e.target.value)}
                                        className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Professional Summary</label>
                                <textarea
                                    value={parsedData.basics?.summary || ''}
                                    onChange={(e) => updateBasics('summary', e.target.value)}
                                    rows={4}
                                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                />
                            </div>
                        </CollapsibleSection>

                        {/* Work Experience */}
                        <CollapsibleSection
                            title={`Work Experience (${parsedData.work?.length || 0})`}
                            isExpanded={expandedSections.has('work')}
                            onToggle={() => toggleSection('work')}
                        >
                            {(parsedData.work || []).map((work: any, index: number) => (
                                <div key={index} className="border border-slate-200 rounded-lg p-4 relative">
                                    <button
                                        onClick={() => removeArrayItem('work', index)}
                                        className="absolute top-2 right-2 text-red-500 hover:text-red-700"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                    <div className="grid grid-cols-2 gap-3 mb-3">
                                        <input
                                            placeholder="Position"
                                            value={work.position || ''}
                                            onChange={(e) => updateArrayItem('work', index, 'position', e.target.value)}
                                            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                                        />
                                        <input
                                            placeholder="Company"
                                            value={work.name || ''}
                                            onChange={(e) => updateArrayItem('work', index, 'name', e.target.value)}
                                            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                                        />
                                        <input
                                            placeholder="Start Date"
                                            value={work.startDate || ''}
                                            onChange={(e) => updateArrayItem('work', index, 'startDate', e.target.value)}
                                            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                                        />
                                        <input
                                            placeholder="End Date"
                                            value={work.endDate || ''}
                                            onChange={(e) => updateArrayItem('work', index, 'endDate', e.target.value)}
                                            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                                        />
                                    </div>
                                    <textarea
                                        placeholder="Summary"
                                        value={work.summary || ''}
                                        onChange={(e) => updateArrayItem('work', index, 'summary', e.target.value)}
                                        rows={2}
                                        className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                                    />
                                </div>
                            ))}
                            <button
                                onClick={() => addArrayItem('work', { position: '', name: '', startDate: '', endDate: '', summary: '', highlights: [] })}
                                className="flex items-center gap-2 text-indigo-600 hover:text-indigo-700 font-medium text-sm"
                            >
                                <Plus size={16} /> Add Work Experience
                            </button>
                        </CollapsibleSection>

                        {/* Education */}
                        <CollapsibleSection
                            title={`Education (${parsedData.education?.length || 0})`}
                            isExpanded={expandedSections.has('education')}
                            onToggle={() => toggleSection('education')}
                        >
                            {(parsedData.education || []).map((edu: any, index: number) => (
                                <div key={index} className="border border-slate-200 rounded-lg p-4 relative">
                                    <button
                                        onClick={() => removeArrayItem('education', index)}
                                        className="absolute top-2 right-2 text-red-500 hover:text-red-700"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                    <div className="grid grid-cols-2 gap-3">
                                        <input
                                            placeholder="Institution"
                                            value={edu.institution || ''}
                                            onChange={(e) => updateArrayItem('education', index, 'institution', e.target.value)}
                                            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                                        />
                                        <input
                                            placeholder="Degree"
                                            value={edu.studyType || ''}
                                            onChange={(e) => updateArrayItem('education', index, 'studyType', e.target.value)}
                                            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                                        />
                                        <input
                                            placeholder="Field of Study"
                                            value={edu.area || ''}
                                            onChange={(e) => updateArrayItem('education', index, 'area', e.target.value)}
                                            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                                        />
                                        <input
                                            placeholder="End Date"
                                            value={edu.endDate || ''}
                                            onChange={(e) => updateArrayItem('education', index, 'endDate', e.target.value)}
                                            className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                                        />
                                    </div>
                                </div>
                            ))}
                            <button
                                onClick={() => addArrayItem('education', { institution: '', studyType: '', area: '', endDate: '' })}
                                className="flex items-center gap-2 text-indigo-600 hover:text-indigo-700 font-medium text-sm"
                            >
                                <Plus size={16} /> Add Education
                            </button>
                        </CollapsibleSection>

                        {/* Skills */}
                        <CollapsibleSection
                            title={`Skills (${parsedData.skills?.length || 0})`}
                            isExpanded={expandedSections.has('skills')}
                            onToggle={() => toggleSection('skills')}
                        >
                            <div className="flex flex-wrap gap-2">
                                {(parsedData.skills || []).map((skill: any, index: number) => (
                                    <div key={index} className="flex items-center gap-2 bg-indigo-50 text-indigo-700 px-3 py-1 rounded-full text-sm">
                                        <input
                                            value={typeof skill === 'string' ? skill : skill.name || ''}
                                            onChange={(e) => updateArrayItem('skills', index, 'name', e.target.value)}
                                            className="bg-transparent border-none outline-none w-24"
                                        />
                                        <button
                                            onClick={() => removeArrayItem('skills', index)}
                                            className="text-indigo-500 hover:text-indigo-700"
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                    </div>
                                ))}
                                <button
                                    onClick={() => addArrayItem('skills', { name: '', keywords: [] })}
                                    className="flex items-center gap-1 text-indigo-600 hover:text-indigo-700 font-medium text-sm px-3 py-1 border border-indigo-300 rounded-full"
                                >
                                    <Plus size={14} /> Add Skill
                                </button>
                            </div>
                        </CollapsibleSection>

                        {/* Projects */}
                        <CollapsibleSection
                            title={`Projects (${parsedData.projects?.length || 0})`}
                            isExpanded={expandedSections.has('projects')}
                            onToggle={() => toggleSection('projects')}
                        >
                            {(parsedData.projects || []).map((project: any, index: number) => (
                                <div key={index} className="border border-slate-200 rounded-lg p-4 relative">
                                    <button
                                        onClick={() => removeArrayItem('projects', index)}
                                        className="absolute top-2 right-2 text-red-500 hover:text-red-700"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                    <input
                                        placeholder="Project Name"
                                        value={project.name || ''}
                                        onChange={(e) => updateArrayItem('projects', index, 'name', e.target.value)}
                                        className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm mb-2"
                                    />
                                    <textarea
                                        placeholder="Description"
                                        value={project.description || ''}
                                        onChange={(e) => updateArrayItem('projects', index, 'description', e.target.value)}
                                        rows={2}
                                        className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                                    />
                                </div>
                            ))}
                            <button
                                onClick={() => addArrayItem('projects', { name: '', description: '', highlights: [] })}
                                className="flex items-center gap-2 text-indigo-600 hover:text-indigo-700 font-medium text-sm"
                            >
                                <Plus size={16} /> Add Project
                            </button>
                        </CollapsibleSection>

                        {/* Certificates */}
                        <CollapsibleSection
                            title={`Certificates (${parsedData.certificates?.length || 0})`}
                            isExpanded={expandedSections.has('certificates')}
                            onToggle={() => toggleSection('certificates')}
                        >
                            {(parsedData.certificates || []).map((cert: any, index: number) => (
                                <div key={index} className="flex items-center gap-2 border border-slate-200 rounded-lg p-3">
                                    <input
                                        placeholder="Certificate Name"
                                        value={cert.name || ''}
                                        onChange={(e) => updateArrayItem('certificates', index, 'name', e.target.value)}
                                        className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-sm"
                                    />
                                    <input
                                        placeholder="Issuer"
                                        value={cert.issuer || ''}
                                        onChange={(e) => updateArrayItem('certificates', index, 'issuer', e.target.value)}
                                        className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-sm"
                                    />
                                    <button
                                        onClick={() => removeArrayItem('certificates', index)}
                                        className="text-red-500 hover:text-red-700"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                            ))}
                            <button
                                onClick={() => addArrayItem('certificates', { name: '', issuer: '', date: '' })}
                                className="flex items-center gap-2 text-indigo-600 hover:text-indigo-700 font-medium text-sm"
                            >
                                <Plus size={16} /> Add Certificate
                            </button>
                        </CollapsibleSection>

                        <div className="pt-6 flex justify-end gap-3 border-t border-slate-200">
                            <button
                                onClick={() => setStatus('idle')}
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
                    </motion.div>
                )}

                {/* Loading States */}
                {(status === 'uploading' || status === 'parsing' || status === 'matching') && (
                    <div className="text-center py-12">
                        <div className="inline-block w-16 h-16 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin mb-4"></div>
                        <p className="text-slate-600 font-medium">
                            {status === 'uploading' && 'Uploading your CV...'}
                            {status === 'parsing' && 'Parsing your CV with AI...'}
                            {status === 'matching' && 'Finding the best job matches...'}
                        </p>
                    </div>
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
                                        {match.explanation ? (
                                            <div className="bg-slate-50 p-4 rounded-lg border border-slate-100 mt-4">
                                                <p className="text-sm text-slate-700 leading-relaxed">
                                                    <span className="font-semibold text-indigo-600">Why it's a match: </span>
                                                    {match.explanation}
                                                </p>
                                            </div>
                                        ) : (
                                            <div className="mt-4">
                                                <span className="text-xs text-slate-400 italic flex items-center gap-1">
                                                    <div className="w-2 h-2 bg-slate-300 rounded-full animate-pulse"></div>
                                                    AI analysis pending...
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                    <div className="flex flex-col justify-center gap-3 min-w-[140px]">
                                        <button
                                            onClick={() => handleApply(match.job_id)}
                                            className="w-full px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors text-sm flex items-center justify-center gap-2"
                                        >
                                            <Send size={14} /> Apply Now
                                        </button>
                                        <button
                                            onClick={() => handleSaveJob(match.job_id)}
                                            className="w-full px-4 py-2 border border-slate-200 text-slate-600 font-medium rounded-lg hover:bg-slate-50 transition-colors text-sm flex items-center justify-center gap-2"
                                        >
                                            <Eye size={14} /> Save Job
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
