import React from 'react';
import { Building2, MapPin, Briefcase, TrendingUp, Send, Eye } from 'lucide-react';
import { motion } from 'framer-motion';

interface Match {
    job_id: string;
    job_title: string;
    company: string;
    match_score: number;
    explanation?: string | null;
    location?: string | any;
    salary_range?: string;
}

interface ResultsSectionProps {
    matches: Match[];
    onApply: (jobId: string) => void;
    onSave: (jobId: string) => void;
    appliedJobs?: Set<string>;
    savedJobs?: Set<string>;
}

export const ResultsSection: React.FC<ResultsSectionProps> = ({ matches, onApply, onSave, appliedJobs, savedJobs }) => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
        >
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-slate-900">Top Job Matches</h2>
                <span className="text-sm text-slate-500">Based on your skills and experience</span>
            </div>

            <div className="space-y-4">
                {matches.map((match) => {
                    const isApplied = appliedJobs?.has(match.job_id);
                    const isSaved = savedJobs?.has(match.job_id);

                    return (
                        <div key={match.job_id} className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow flex flex-col md:flex-row gap-6">
                            <div className="flex-1">
                                <div className="flex justify-between items-start mb-2">
                                    <div>
                                        <h3 className="text-lg font-bold text-slate-900">{match.job_title}</h3>
                                        <div className="flex items-center gap-4 text-sm text-slate-500 mt-1">
                                            <span className="flex items-center gap-1"><Building2 size={14} /> {match.company}</span>
                                            <span className="flex items-center gap-1">
                                                <MapPin size={14} />
                                                {typeof match.location === 'object' && match.location !== null
                                                    ? [
                                                        (match.location as any).city,
                                                        (match.location as any).region,
                                                        (match.location as any).countryCode
                                                    ].filter(Boolean).join(', ') || 'Remote'
                                                    : match.location || 'Remote'}
                                            </span>
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
                                    onClick={() => !isApplied && onApply(match.job_id)}
                                    disabled={isApplied}
                                    className={`w-full px-4 py-2 font-medium rounded-lg transition-colors text-sm flex items-center justify-center gap-2 ${isApplied
                                            ? 'bg-emerald-100 text-emerald-700 cursor-default'
                                            : 'bg-indigo-600 text-white hover:bg-indigo-700'
                                        }`}
                                >
                                    {isApplied ? <><Send size={14} /> Applied</> : <><Send size={14} /> Apply Now</>}
                                </button>
                                <button
                                    onClick={() => !isSaved && onSave(match.job_id)}
                                    disabled={isSaved}
                                    className={`w-full px-4 py-2 border font-medium rounded-lg transition-colors text-sm flex items-center justify-center gap-2 ${isSaved
                                            ? 'bg-slate-100 text-slate-500 border-slate-200 cursor-default'
                                            : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                                        }`}
                                >
                                    {isSaved ? <><Eye size={14} /> Saved</> : <><Eye size={14} /> Save Job</>}
                                </button>
                            </div>
                        </div>
                    )
                })}
            </div>
        </motion.div>
    );
};
