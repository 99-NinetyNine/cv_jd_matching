import React, { useState } from 'react';
import { Briefcase, Crown } from 'lucide-react';
import { StatusIndicator } from '../components/candidate/StatusIndicator';
import { UploadSection } from '../components/candidate/UploadSection';
import { ResultsSection } from '../components/candidate/ResultsSection';
import { AIInsightsDisplay } from '../components/candidate/AIInsightsDisplay';

import { AIPortalSection } from '../components/candidate/AIPortalSection';
import { api } from '../utils/api';

interface Match {
    job_id: string;
    job_title: string;
    company: string;
    match_score: number;
    explanation?: string | null;
    location?: string | any;
    salary_range?: string;
}

type ProcessingStatus = 'idle' | 'uploading' | 'parsing' | 'reviewing' | 'matching' | 'ai_analyzing' | 'complete' | 'submitted';

const CandidateDashboard = () => {
    const [file, setFile] = useState<File | null>(null);
    const [status, setStatus] = useState<ProcessingStatus>('idle');
    const [matches, setMatches] = useState<Match[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [cvId, setCvId] = useState<string | null>(null);
    const [predictionId, setPredictionId] = useState<string | null>(null);
    const [appliedJobs, setAppliedJobs] = useState<Set<string>>(new Set());
    const [savedJobs, setSavedJobs] = useState<Set<string>>(new Set());
    const [isPremium, setIsPremium] = useState<boolean>(false);

    // Premium AI Analysis State
    const [aiInsights, setAiInsights] = useState<any>(null);



    // AI Portal Modal state
    const [showAIPortal, setShowAIPortal] = useState(false);
    const [portalCvId, setPortalCvId] = useState<string | null>(null);

    const togglePremium = () => {
        const newPremiumStatus = !isPremium;
        setIsPremium(newPremiumStatus);
    };

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



    const logInteraction = async (jobId: string, action: 'viewed' | 'applied' | 'saved'): Promise<boolean> => {
        if (!cvId) return false;

        try {
            const response = await api.post('/interactions/log', {
                job_id: jobId,
                action: action,
                cv_id: cvId,
                prediction_id: predictionId,
                metadata: {
                    source: 'dashboard',
                    timestamp: new Date().toISOString()
                }
            });

            // Check if the interaction was successful
            if (response.data.status === 'success') {
                console.log(`✓ Logged: ${action} for job ${jobId}`);
                return true;
            } else if (response.data.status === 'already_exists') {
                console.log(`⚠ Already ${action}: job ${jobId}`);
                return false;
            }
            return false;
        } catch (err) {
            console.error('Failed to log interaction:', err);
            return false;
        }
    };

    const handleApply = async (jobId: string) => {
        const success = await logInteraction(jobId, 'applied');
        if (success) {
            setAppliedJobs(prev => new Set(prev).add(jobId));
        }
    };

    const handleSaveJob = async (jobId: string) => {
        const success = await logInteraction(jobId, 'saved');
        if (success) {
            setSavedJobs(prev => new Set(prev).add(jobId));
        }
    };



    const handleUpload = async () => {
        if (!file) return;
        setStatus('uploading');
        setError(null);
        setMatches([]);

        const formData = new FormData();
        formData.append('file', file);

        try {
            if (isPremium) {
                // PREMIUM FLOW: AI Portal Modal
                // 1. Upload to super-advanced endpoint
                const uploadRes = await api.post('/super-advanced/upload', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                const uploadedCvId = uploadRes.data.cv_id;
                setCvId(uploadedCvId);
                setPortalCvId(uploadedCvId);

                // 2. Open AI Portal Modal
                setShowAIPortal(true);
                setStatus('idle'); // Reset status as modal handles its own
            } else {
                // NON-PREMIUM FLOW: Simple Upload
                await api.post('/upload', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                setStatus('submitted');
            }

        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.detail || err.message || "Upload failed. Please try again.");
            setStatus('idle');
        }
    };

    const handleAIPortalComplete = (matches: any[], aiInsights?: any) => {
        console.log('✓ AI Portal Complete:', { matches, aiInsights });
        setMatches(matches);
        if (aiInsights) {
            setAiInsights(aiInsights);
        }
        setShowAIPortal(false);
        setStatus('complete');

        // Log viewed interactions
        if (matches && matches.length > 0) {
            matches.forEach((match: any) => {
                logInteraction(match.job_id || match.data?.job_id, 'viewed');
            });
        }
    };



    // Fetch recommendations on mount (only for premium/returning users really, but good to have)
    React.useEffect(() => {
        // Only fetch if we think we have a session or something, but for now let's just try
        // If non-premium, maybe we shouldn't auto-fetch?
        // But the requirement is just about the upload flow.
        // Let's keep it as is, but maybe handle 404 gracefully.

        setStatus('matching'); // Show loading state

        api.get('/recommendations')
            .then(res => {
                setMatches(res.data.recommendations);
                setPredictionId(res.data.prediction_id);
                setCvId(res.data.cv_id);

                // Use applied/saved state from API response
                if (res.data.applied_jobs) {
                    setAppliedJobs(new Set(res.data.applied_jobs));
                }
                if (res.data.saved_jobs) {
                    setSavedJobs(new Set(res.data.saved_jobs));
                }

                setStatus('complete');
            })
            .catch(err => {
                console.error("Failed to fetch recommendations:", err);
                // No CV found - show upload form
                setStatus('idle');
            });
    }, []);


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
                {status !== 'idle' && status !== 'complete' && status !== 'submitted' && (
                    <StatusIndicator status={status as any} />
                )}

                {/* AI Portal Section */}
                {showAIPortal && portalCvId && (
                    <AIPortalSection
                        cvId={portalCvId}
                        isPremium={isPremium}
                        onComplete={handleAIPortalComplete}
                    />
                )}

                {/* Upload Section - Hidden when AI Portal is active */}
                {!showAIPortal && (
                    <UploadSection
                        file={file}
                        error={error}
                        status={status}
                        onFileChange={handleFileChange}
                        onUpload={handleUpload}
                        isPremium={isPremium}
                    />
                )}

                {/* Submitted State (Non-Premium) */}
                {status === 'submitted' && (
                    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-12 mb-12 max-w-2xl mx-auto text-center">
                        <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-6">
                            <Briefcase size={32} />
                        </div>
                        <h2 className="text-2xl font-bold text-slate-900 mb-4">CV Uploaded Successfully</h2>
                        <p className="text-slate-600 mb-8">
                            Your CV has been queued for processing. We will analyze it and find the best matches for you.
                            Check back later for your results.
                        </p>
                        <button
                            onClick={() => setStatus('idle')}
                            className="px-6 py-2 border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-50"
                        >
                            Upload Another
                        </button>
                    </div>
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

                {/* AI Insights Display (Results) */}
                {aiInsights && isPremium && (
                    <AIInsightsDisplay
                        qualityScore={aiInsights.quality_score}
                        contrastiveExplanation={aiInsights.contrastive_explanation}
                        counterfactualSuggestions={aiInsights.counterfactual_suggestions}
                        cotReasoning={aiInsights.cot_reasoning}
                    />
                )}

                {/* Results Section */}
                {matches.length > 0 && (
                    <ResultsSection
                        matches={matches}
                        onApply={handleApply}
                        onSave={handleSaveJob}
                        appliedJobs={appliedJobs}
                        savedJobs={savedJobs}
                    />
                )}
            </main>


        </div>
    );
};

export default CandidateDashboard;
