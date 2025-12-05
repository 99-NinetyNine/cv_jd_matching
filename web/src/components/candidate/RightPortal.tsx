import React from 'react';
import { Target, AlertCircle, CheckCircle, TrendingUp, Loader, Sparkles } from 'lucide-react';

interface RightPortalProps {
    data: {
        status?: string;
        qualityScores?: {
            overall_score?: number;
            issues?: string[];
        };
        streamingText?: string;
        complete?: boolean;
    };
    onProceed: () => void;
    isComplete: boolean;
}

export const RightPortal: React.FC<RightPortalProps> = ({ data, onProceed, isComplete }) => {
    const score = data.qualityScores?.overall_score || 0;
    const issues = data.qualityScores?.issues || [];

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

    return (
        <div className="p-6 h-full">
            <div className="mb-6">
                <h3 className="text-xl font-bold text-purple-900 mb-2 flex items-center gap-2">
                    <Target size={24} />
                    CV Quality Review
                </h3>
                <p className="text-sm text-purple-700">Analyzing your CV for improvements</p>
            </div>

            {/* Loading State */}
            {data.status === 'analyzing' && !isComplete && (
                <div className="flex flex-col items-center justify-center py-12">
                    <div className="w-16 h-16 bg-purple-500 rounded-full flex items-center justify-center mb-4">
                        <Loader size={32} className="text-white animate-spin" />
                    </div>
                    <p className="text-purple-700 font-medium">Analyzing your CV...</p>
                </div>
            )}

            {/* Quality Score Display */}
            {data.qualityScores && (
                <div className="space-y-6">
                    {/* Overall Score */}
                    <div className={`${getScoreBgColor(score)} rounded-xl p-6 border-2 border-purple-200`}>
                        <div className="flex items-center justify-between mb-4">
                            <h4 className="font-bold text-gray-900">Overall Quality Score</h4>
                            <div className={`text-4xl font-bold ${getScoreColor(score)}`}>
                                {score}
                                <span className="text-2xl">/100</span>
                            </div>
                        </div>
                        <div className="w-full bg-white rounded-full h-3 overflow-hidden">
                            <div
                                className={`h-full transition-all duration-1000 ${score >= 80
                                        ? 'bg-green-500'
                                        : score >= 60
                                            ? 'bg-yellow-500'
                                            : 'bg-red-500'
                                    }`}
                                style={{ width: `${score}%` }}
                            />
                        </div>
                    </div>

                    {/* Issues */}
                    {issues.length > 0 && (
                        <div className="bg-white rounded-xl p-6 border border-purple-200">
                            <h4 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                                <AlertCircle size={20} className="text-orange-500" />
                                Areas for Improvement
                            </h4>
                            <ul className="space-y-3">
                                {issues.map((issue, index) => (
                                    <li
                                        key={index}
                                        className="flex items-start gap-3 p-3 bg-orange-50 rounded-lg border border-orange-200"
                                    >
                                        <div className="w-6 h-6 bg-orange-500 text-white rounded-full flex items-center justify-center flex-shrink-0 text-sm font-bold">
                                            {index + 1}
                                        </div>
                                        <span className="text-gray-800 flex-1">{issue}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Streaming Analysis */}
                    {data.streamingText && (
                        <div className="bg-gradient-to-br from-purple-100 to-pink-100 rounded-xl p-6 border border-purple-200">
                            <h4 className="font-bold text-gray-900 mb-3 flex items-center gap-2">
                                <Sparkles size={20} className="text-purple-600" />
                                AI Analysis
                            </h4>
                            <p className="text-gray-800 whitespace-pre-wrap leading-relaxed">
                                {data.streamingText}
                            </p>
                        </div>
                    )}

                    {/* Recommendations */}
                    {isComplete && score < 100 && (
                        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-200">
                            <h4 className="font-bold text-gray-900 mb-3 flex items-center gap-2">
                                <TrendingUp size={20} className="text-blue-600" />
                                Quick Wins
                            </h4>
                            <ul className="space-y-2 text-sm text-gray-700">
                                <li className="flex items-start gap-2">
                                    <CheckCircle size={16} className="text-green-500 mt-0.5 flex-shrink-0" />
                                    <span>Add quantifiable achievements to work experience</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <CheckCircle size={16} className="text-green-500 mt-0.5 flex-shrink-0" />
                                    <span>Include relevant certifications and courses</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <CheckCircle size={16} className="text-green-500 mt-0.5 flex-shrink-0" />
                                    <span>Optimize keywords for ATS systems</span>
                                </li>
                            </ul>
                        </div>
                    )}

                    {/* Proceed Button */}
                    {isComplete && (
                        <div className="sticky bottom-0 bg-gradient-to-r from-purple-600 to-pink-600 rounded-xl p-6 text-center shadow-xl">
                            <h4 className="text-white font-bold text-lg mb-2">Ready to Find Matches?</h4>
                            <p className="text-white/90 text-sm mb-4">
                                Your CV has been reviewed. Let's find the perfect jobs for you!
                            </p>
                            <button
                                onClick={onProceed}
                                className="w-full px-6 py-3 bg-white text-purple-600 font-bold rounded-lg hover:bg-purple-50 transition-all shadow-lg hover:shadow-xl transform hover:scale-105"
                            >
                                Give Me Predictions 🚀
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* Empty State */}
            {!data.qualityScores && data.status !== 'analyzing' && (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                    <div className="w-20 h-20 bg-purple-100 rounded-full flex items-center justify-center mb-4">
                        <Target size={40} className="text-purple-600" />
                    </div>
                    <h4 className="text-lg font-bold text-gray-900 mb-2">Quality Check Ready</h4>
                    <p className="text-gray-600 text-sm">Waiting for analysis to begin...</p>
                </div>
            )}
        </div>
    );
};
