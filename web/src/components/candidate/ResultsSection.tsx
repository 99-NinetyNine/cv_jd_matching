import React from 'react';
import { Building2, MapPin, Briefcase, TrendingUp, Send, Eye } from 'lucide-react';
import { motion } from 'framer-motion';

interface Match {
    job_id: string;
    job_title: string;
    company: string;
    match_score: number;
    explanation?: string | null;
    location?: string;
    salary_range?: string;
}

interface ResultsSectionProps {
    matches: Match[];
    onApply: (jobId: string) => void;
    onSave: (jobId: string) => void;
}

export const ResultsSection: React.FC<ResultsSectionProps> = ({ matches, onApply, onSave }) => {
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
                                onClick={() => onApply(match.job_id)}
                                className="w-full px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors text-sm flex items-center justify-center gap-2"
                            >
                                <Send size={14} /> Apply Now
                            </button>
                            <button
                                onClick={() => onSave(match.job_id)}
                                className="w-full px-4 py-2 border border-slate-200 text-slate-600 font-medium rounded-lg hover:bg-slate-50 transition-colors text-sm flex items-center justify-center gap-2"
                            >
                                <Eye size={14} /> Save Job
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </motion.div>
    );
};
