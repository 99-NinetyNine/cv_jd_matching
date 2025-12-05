import React from 'react';
import { Target, TrendingUp, Lightbulb, Brain, Award, AlertCircle } from 'lucide-react';

interface AIInsightsDisplayProps {
    qualityScore?: {
        overall_score: number;
        structure_formatting: number;
        content_completeness: number;
        ats_compatibility: number;
        keyword_optimization: number;
        professional_language: number;
        improvement_suggestions: string[];
    };
    contrastiveExplanation?: string;
    counterfactualSuggestions?: string[];
    cotReasoning?: string;
}

export const AIInsightsDisplay: React.FC<AIInsightsDisplayProps> = ({
    qualityScore,
    contrastiveExplanation,
    counterfactualSuggestions,
    cotReasoning
}) => {
    if (!qualityScore && !contrastiveExplanation && !counterfactualSuggestions && !cotReasoning) {
        return null;
    }

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
        <div className="space-y-6 mb-8">
            <div className="flex items-center gap-3 mb-4">
                <Award className="w-7 h-7 text-purple-600" />
                <h2 className="text-2xl font-bold text-gray-900">AI Premium Insights</h2>
            </div>

            {/* CV Quality Score */}
            {qualityScore && (
                <div className="bg-white rounded-lg shadow-lg p-6 border border-purple-200">
                    <div className="flex items-center gap-3 mb-4">
                        <Target className="w-6 h-6 text-purple-600" />
                        <h3 className="text-xl font-bold text-gray-900">Resume Quality Assessment</h3>
                    </div>

                    {/* Overall Score */}
                    <div className="mb-6">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-lg font-semibold text-gray-700">Overall Score</span>
                            <span className={`text-4xl font-bold ${getScoreColor(qualityScore.overall_score)}`}>
                                {qualityScore.overall_score}/100
                            </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                            <div
                                className={`h-full rounded-full transition-all duration-1000 ${
                                    qualityScore.overall_score >= 80 ? 'bg-green-500' :
                                    qualityScore.overall_score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                                }`}
                                style={{ width: `${qualityScore.overall_score}%` }}
                            ></div>
                        </div>
                    </div>

                    {/* Detailed Scores */}
                    <div className="grid grid-cols-2 gap-4 mb-6">
                        {[
                            { key: 'structure_formatting', label: 'Structure & Format' },
                            { key: 'content_completeness', label: 'Content Completeness' },
                            { key: 'ats_compatibility', label: 'ATS Compatibility' },
                            { key: 'keyword_optimization', label: 'Keyword Optimization' },
                            { key: 'professional_language', label: 'Professional Language' }
                        ].map(({ key, label }) => {
                            const score = qualityScore[key as keyof typeof qualityScore] as number || 0;
                            return (
                                <div key={key} className={`p-3 rounded-lg ${getScoreBgColor(score)}`}>
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm font-medium text-gray-700">{label}</span>
                                        <span className={`text-lg font-bold ${getScoreColor(score)}`}>
                                            {score}
                                        </span>
                                    </div>
                                    <div className="w-full bg-white/50 rounded-full h-2 mt-2">
                                        <div
                                            className={`h-full rounded-full ${
                                                score >= 80 ? 'bg-green-500' :
                                                score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                                            }`}
                                            style={{ width: `${score}%` }}
                                        ></div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* Improvement Suggestions */}
                    {qualityScore.improvement_suggestions?.length > 0 && (
                        <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                            <div className="flex items-center gap-2 mb-3">
                                <AlertCircle className="w-5 h-5 text-blue-600" />
                                <h4 className="font-semibold text-blue-900">Top Improvements</h4>
                            </div>
                            <ul className="space-y-2">
                                {qualityScore.improvement_suggestions.map((suggestion, idx) => (
                                    <li key={idx} className="flex items-start gap-2 text-sm text-blue-800">
                                        <span className="font-bold text-blue-600">{idx + 1}.</span>
                                        <span>{suggestion}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            )}

            {/* Contrastive Explanation */}
            {contrastiveExplanation && (
                <div className="bg-white rounded-lg shadow-lg p-6 border border-purple-200">
                    <div className="flex items-center gap-3 mb-4">
                        <TrendingUp className="w-6 h-6 text-purple-600" />
                        <h3 className="text-xl font-bold text-gray-900">Why This Ranking?</h3>
                    </div>
                    <p className="text-gray-700 leading-relaxed italic">
                        "{contrastiveExplanation}"
                    </p>
                </div>
            )}

            {/* Counterfactual Suggestions */}
            {counterfactualSuggestions && counterfactualSuggestions.length > 0 && (
                <div className="bg-white rounded-lg shadow-lg p-6 border border-purple-200">
                    <div className="flex items-center gap-3 mb-4">
                        <Lightbulb className="w-6 h-6 text-yellow-600" />
                        <h3 className="text-xl font-bold text-gray-900">What-If Scenarios</h3>
                        <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full font-semibold">
                            Career Boost
                        </span>
                    </div>
                    <div className="space-y-3">
                        {counterfactualSuggestions.map((suggestion, idx) => (
                            <div
                                key={idx}
                                className="p-4 bg-gradient-to-r from-yellow-50 to-orange-50 rounded-lg border border-yellow-200"
                            >
                                <div className="flex items-start gap-3">
                                    <div className="flex-shrink-0 w-8 h-8 bg-yellow-500 text-white rounded-full flex items-center justify-center font-bold">
                                        {idx + 1}
                                    </div>
                                    <p className="text-gray-800 flex-1">{suggestion}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Chain-of-Thought Reasoning */}
            {cotReasoning && (
                <div className="bg-white rounded-lg shadow-lg p-6 border border-purple-200">
                    <div className="flex items-center gap-3 mb-4">
                        <Brain className="w-6 h-6 text-purple-600" />
                        <h3 className="text-xl font-bold text-gray-900">AI Reasoning Process</h3>
                        <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded-full font-semibold">
                            Step-by-Step
                        </span>
                    </div>
                    <div className="prose prose-sm max-w-none">
                        <pre className="whitespace-pre-wrap bg-gray-50 p-4 rounded-lg border border-gray-200 text-gray-800 font-mono text-sm leading-relaxed">
{cotReasoning}
                        </pre>
                    </div>
                </div>
            )}
        </div>
    );
};
