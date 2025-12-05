import React from 'react';
import { CheckCircle, Loader, Database, Search, Brain, Sparkles } from 'lucide-react';

interface LeftPortalProps {
    data: {
        status?: string;
        cvText?: string;
        parsed?: boolean;
        embedded?: boolean;
        matches?: any[];
        matchingComplete?: boolean;
        contrastiveExplanation?: string;
        counterfactualSuggestions?: string[];
        cotReasoning?: string;
        error?: string;
    };
}

export const LeftPortal: React.FC<LeftPortalProps> = ({ data }) => {
    const stages = [
        {
            key: 'parsing',
            label: 'Parsing CV',
            icon: Database,
            active: data.status === 'parsing',
            complete: data.parsed,
        },
        {
            key: 'embedding',
            label: 'Creating Embeddings',
            icon: Brain,
            active: data.status === 'embedding',
            complete: data.embedded,
        },
        {
            key: 'searching',
            label: 'Finding Matches',
            icon: Search,
            active: data.status === 'searching',
            complete: data.matchingComplete,
        },
        {
            key: 'ai_analyzing',
            label: 'AI Analysis',
            icon: Sparkles,
            active: data.status === 'ai_analyzing',
            complete: data.contrastiveExplanation && data.counterfactualSuggestions && data.cotReasoning,
        },
    ];

    return (
        <div className="p-6 h-full">
            <div className="mb-6">
                <h3 className="text-xl font-bold text-gray-900 mb-2">Matching Pipeline</h3>
                <p className="text-sm text-gray-600">Processing your CV and finding the best job matches</p>
            </div>

            {/* Progress Stages */}
            <div className="space-y-4 mb-8">
                {stages.map((stage) => {
                    const Icon = stage.icon;
                    const isActive = stage.active;
                    const isComplete = stage.complete;

                    return (
                        <div
                            key={stage.key}
                            className={`flex items-start gap-4 p-4 rounded-lg border-2 transition-all ${isActive
                                ? 'border-indigo-500 bg-indigo-50'
                                : isComplete
                                    ? 'border-green-500 bg-green-50'
                                    : 'border-gray-200 bg-gray-50'
                                }`}
                        >
                            <div
                                className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${isActive
                                    ? 'bg-indigo-500 text-white'
                                    : isComplete
                                        ? 'bg-green-500 text-white'
                                        : 'bg-gray-300 text-gray-600'
                                    }`}
                            >
                                {isActive ? (
                                    <Loader size={20} className="animate-spin" />
                                ) : isComplete ? (
                                    <CheckCircle size={20} />
                                ) : (
                                    <Icon size={20} />
                                )}
                            </div>
                            <div className="flex-1">
                                <h4 className="font-semibold text-gray-900">{stage.label}</h4>
                                <p className="text-sm text-gray-600 mt-1">
                                    {isActive && 'Processing...'}
                                    {isComplete && 'Complete'}
                                    {!isActive && !isComplete && 'Waiting...'}
                                </p>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Error Display */}
            {data.error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                    <p className="text-red-700 font-medium">Error: {data.error}</p>
                </div>
            )}

            {/* Matches Preview */}
            {data.matches && data.matches.length > 0 && (
                <div className="bg-white border border-gray-200 rounded-lg p-6">
                    <h4 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <CheckCircle size={20} className="text-green-500" />
                        Found {data.matches.length} Matches
                    </h4>
                    <div className="space-y-3">
                        {data.matches.map((match, index) => (
                            <div
                                key={index}
                                className="p-4 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg border border-indigo-200"
                            >
                                <div className="flex items-start justify-between mb-2">
                                    <div>
                                        <h5 className="font-semibold text-gray-900">{match.title || match.data?.title}</h5>
                                        <p className="text-sm text-gray-600">{match.company || match.data?.company}</p>
                                    </div>
                                    <div className="text-right">
                                        <div className="text-lg font-bold text-indigo-600">
                                            {Math.round((match.match_score || 0) * 100)}%
                                        </div>
                                        <div className="text-xs text-gray-500">Match</div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* AI Insights Preview */}
            {data.contrastiveExplanation && (
                <div className="mt-6 bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200 rounded-lg p-6">
                    <h4 className="font-bold text-gray-900 mb-3 flex items-center gap-2">
                        <Sparkles size={20} className="text-purple-600" />
                        AI Insights
                    </h4>
                    <div className="space-y-4 text-sm">
                        <div>
                            <h5 className="font-semibold text-gray-800 mb-1">Why This Match?</h5>
                            <p className="text-gray-700">{data.contrastiveExplanation}</p>
                        </div>
                        {data.counterfactualSuggestions && data.counterfactualSuggestions.length > 0 && (
                            <div>
                                <h5 className="font-semibold text-gray-800 mb-2">Improvement Suggestions</h5>
                                <ul className="space-y-1">
                                    {data.counterfactualSuggestions.map((suggestion, idx) => (
                                        <li key={idx} className="text-gray-700 flex items-start gap-2">
                                            <span className="text-purple-600">•</span>
                                            <span>{suggestion}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Complete State */}
            {data.status === 'complete' && (
                <div className="mt-6 text-center">
                    <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
                        <CheckCircle size={32} className="text-white" />
                    </div>
                    <h4 className="text-xl font-bold text-gray-900 mb-2">Analysis Complete!</h4>
                    <p className="text-gray-600">Your results are ready to view</p>
                </div>
            )}
        </div>
    );
};
