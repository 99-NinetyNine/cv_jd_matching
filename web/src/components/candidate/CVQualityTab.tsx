import React, { useState, useCallback } from 'react';
import { Upload, FileText, Target, TrendingUp, AlertCircle, CheckCircle2, Sparkles } from 'lucide-react';
import { api } from '../../utils/api';

interface QualityScores {
    overall_score: number;
    category_scores: {
        completeness: number;
        formatting: number;
        content_quality: number;
        ats_compatibility: number;
        impact: number;
    };
    issues: string[];
    suggestions: string[];
}

type AnalysisStatus = 'idle' | 'uploading' | 'parsing' | 'scoring' | 'analyzing' | 'complete' | 'error';

export const CVQualityTab: React.FC = () => {
    const [file, setFile] = useState<File | null>(null);
    const [status, setStatus] = useState<AnalysisStatus>('idle');
    const [error, setError] = useState<string | null>(null);
    const [cvId, setCvId] = useState<string | null>(null);

    // Quality scores
    const [scores, setScores] = useState<QualityScores | null>(null);

    // Token streaming
    const [streamingText, setStreamingText] = useState<string>('');
    const [analysisComplete, setAnalysisComplete] = useState(false);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0];

            if (selectedFile.size > 5 * 1024 * 1024) {
                setError("File size exceeds 5MB limit");
                return;
            }

            if (selectedFile.type !== "application/pdf") {
                setError("Only PDF files are allowed");
                return;
            }

            setFile(selectedFile);
            setError(null);
        }
    };

    const handleAnalyze = async () => {
        if (!file) return;

        // Reset state
        setStatus('uploading');
        setError(null);
        setScores(null);
        setStreamingText('');
        setAnalysisComplete(false);

        try {
            // 1. Upload file
            const formData = new FormData();
            formData.append('file', file);

            const uploadRes = await api.post('/super-advanced/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            const uploadedCvId = uploadRes.data.cv_id;
            setCvId(uploadedCvId);

            // 2. Connect WebSocket for analysis
            const apiBase = import.meta.env.VITE_API_URL?.replace(/^http/, 'ws') || 'ws://localhost:8000';
            const ws = new WebSocket(`${apiBase}/super-advanced/ws/analyze/${uploadedCvId}`);

            ws.onopen = () => {
                console.log('✓ CV Quality WebSocket connected');
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.status === 'parsing') {
                    setStatus('parsing');
                } else if (data.status === 'scoring') {
                    setStatus('scoring');
                } else if (data.status === 'scores_ready') {
                    setScores(data.scores);
                } else if (data.status === 'analyzing') {
                    setStatus('analyzing');
                } else if (data.event === 'token') {
                    // REAL TOKEN STREAMING - append each character
                    setStreamingText(prev => prev + data.token);
                } else if (data.status === 'complete') {
                    setStatus('complete');
                    setAnalysisComplete(true);
                    if (data.data?.scores) {
                        setScores(data.data.scores);
                    }
                    ws.close();
                } else if (data.status === 'error') {
                    setError(data.message);
                    setStatus('error');
                    ws.close();
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                setError('Analysis connection failed');
                setStatus('error');
            };

            ws.onclose = () => {
                console.log('WebSocket closed');
            };

        } catch (err: any) {
            console.error('Upload error:', err);
            setError(err.response?.data?.detail || err.message || 'Upload failed');
            setStatus('error');
        }
    };

    const getScoreColor = (score: number) => {
        if (score >= 80) return 'text-green-600';
        if (score >= 60) return 'text-yellow-600';
        return 'text-red-600';
    };

    const getScoreBgColor = (score: number) => {
        if (score >= 80) return 'bg-green-100';
        if (score >= 60) return 'bg-yellow-100';
        return 'bg-red-100';
    };

    const getScoreBarColor = (score: number) => {
        if (score >= 80) return 'bg-green-500';
        if (score >= 60) return 'bg-yellow-500';
        return 'bg-red-500';
    };

    return (
        <div className="max-w-5xl mx-auto px-6 py-12">
            {/* Header */}
            <div className="text-center mb-12">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-purple-600 to-blue-600 rounded-full mb-4">
                    <Target className="w-8 h-8 text-white" />
                </div>
                <h1 className="text-3xl font-bold text-gray-900 mb-4">CV Quality Analyzer</h1>
                <p className="text-gray-600 max-w-2xl mx-auto">
                    Get instant feedback on your resume with AI-powered analysis.
                    No matching, just quality assessment with actionable suggestions.
                </p>
            </div>

            {/* Upload Section */}
            {status === 'idle' && (
                <div className="bg-white rounded-xl border-2 border-dashed border-gray-300 p-12 text-center hover:border-purple-400 transition-colors">
                    <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        Upload Your CV for Quality Check
                    </h3>
                    <p className="text-gray-600 mb-6">PDF only, max 5MB</p>

                    <input
                        type="file"
                        accept=".pdf"
                        onChange={handleFileChange}
                        className="hidden"
                        id="cv-quality-upload"
                    />
                    <label
                        htmlFor="cv-quality-upload"
                        className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 text-white font-medium rounded-lg hover:bg-purple-700 cursor-pointer transition-colors"
                    >
                        <FileText className="w-5 h-5" />
                        Choose File
                    </label>

                    {file && (
                        <div className="mt-6 p-4 bg-purple-50 rounded-lg">
                            <p className="text-sm text-gray-700 mb-4">
                                Selected: <span className="font-semibold">{file.name}</span>
                            </p>
                            <button
                                onClick={handleAnalyze}
                                className="px-8 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-blue-700 transition-all shadow-lg"
                            >
                                Analyze Quality
                            </button>
                        </div>
                    )}

                    {error && (
                        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                            <p className="text-red-700">{error}</p>
                        </div>
                    )}
                </div>
            )}

            {/* Loading States */}
            {['uploading', 'parsing', 'scoring'].includes(status) && (
                <div className="text-center py-12">
                    <div className="inline-block w-16 h-16 border-4 border-purple-200 border-t-purple-600 rounded-full animate-spin mb-4"></div>
                    <p className="text-gray-700 font-medium text-lg">
                        {status === 'uploading' && 'Uploading your CV...'}
                        {status === 'parsing' && 'Parsing CV content...'}
                        {status === 'scoring' && 'Calculating quality scores...'}
                    </p>
                </div>
            )}

            {/* Quality Scores Display */}
            {scores && (
                <div className="bg-white rounded-xl shadow-lg p-8 mb-8 border border-purple-200">
                    <div className="flex items-center gap-3 mb-6">
                        <Target className="w-6 h-6 text-purple-600" />
                        <h2 className="text-2xl font-bold text-gray-900">Quality Scores</h2>
                    </div>

                    {/* Overall Score */}
                    <div className="mb-8">
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-xl font-semibold text-gray-700">Overall Score</span>
                            <span className={`text-5xl font-bold ${getScoreColor(scores.overall_score)}`}>
                                {scores.overall_score}/100
                            </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-6 overflow-hidden">
                            <div
                                className={`h-full rounded-full transition-all duration-1000 ${getScoreBarColor(scores.overall_score)}`}
                                style={{ width: `${scores.overall_score}%` }}
                            ></div>
                        </div>
                    </div>

                    {/* Category Scores */}
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
                        {Object.entries(scores.category_scores).map(([key, score]) => (
                            <div key={key} className={`p-4 rounded-lg ${getScoreBgColor(score)}`}>
                                <div className="text-sm font-medium text-gray-700 mb-2 capitalize">
                                    {key.replace('_', ' ')}
                                </div>
                                <div className={`text-3xl font-bold ${getScoreColor(score)}`}>
                                    {score}
                                </div>
                                <div className="w-full bg-white/50 rounded-full h-2 mt-2">
                                    <div
                                        className={`h-full rounded-full ${getScoreBarColor(score)}`}
                                        style={{ width: `${score}%` }}
                                    ></div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Issues */}
                    {scores.issues.length > 0 && (
                        <div className="bg-red-50 rounded-lg p-4 mb-4 border border-red-200">
                            <div className="flex items-center gap-2 mb-3">
                                <AlertCircle className="w-5 h-5 text-red-600" />
                                <h3 className="font-semibold text-red-900">Issues Found</h3>
                            </div>
                            <ul className="space-y-2">
                                {scores.issues.map((issue, idx) => (
                                    <li key={idx} className="flex items-start gap-2 text-sm text-red-800">
                                        <span className="font-bold text-red-600">•</span>
                                        <span>{issue}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Suggestions */}
                    {scores.suggestions.length > 0 && (
                        <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                            <div className="flex items-center gap-2 mb-3">
                                <CheckCircle2 className="w-5 h-5 text-blue-600" />
                                <h3 className="font-semibold text-blue-900">Quick Wins</h3>
                            </div>
                            <ul className="space-y-2">
                                {scores.suggestions.map((suggestion, idx) => (
                                    <li key={idx} className="flex items-start gap-2 text-sm text-blue-800">
                                        <span className="font-bold text-blue-600">💡</span>
                                        <span>{suggestion}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            )}

            {/* AI Analysis with Token Streaming */}
            {status === 'analyzing' || streamingText || analysisComplete ? (
                <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-xl shadow-lg p-8 border border-purple-200">
                    <div className="flex items-center gap-3 mb-6">
                        <Sparkles className="w-6 h-6 text-purple-600 animate-pulse" />
                        <h2 className="text-2xl font-bold text-gray-900">AI Detailed Analysis</h2>
                        {status === 'analyzing' && (
                            <span className="text-sm text-purple-600 font-medium animate-pulse">
                                Streaming...
                            </span>
                        )}
                    </div>

                    <div className="bg-white rounded-lg p-6 border border-purple-200">
                        <pre className="whitespace-pre-wrap font-mono text-sm text-gray-800 leading-relaxed">
                            {streamingText}
                            {status === 'analyzing' && (
                                <span className="animate-pulse text-purple-600">▋</span>
                            )}
                        </pre>

                        {analysisComplete && (
                            <div className="mt-6 pt-6 border-t border-gray-200">
                                <div className="flex items-center gap-3 text-green-600">
                                    <CheckCircle2 className="w-6 h-6" />
                                    <span className="font-semibold">Analysis Complete!</span>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            ) : null}

            {/* Analyze Another Button */}
            {status === 'complete' && (
                <div className="text-center mt-8">
                    <button
                        onClick={() => {
                            setStatus('idle');
                            setFile(null);
                            setScores(null);
                            setStreamingText('');
                            setAnalysisComplete(false);
                            setCvId(null);
                        }}
                        className="px-8 py-3 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 transition-colors"
                    >
                        Analyze Another CV
                    </button>
                </div>
            )}
        </div>
    );
};
