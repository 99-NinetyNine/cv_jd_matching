import React, { useState, useEffect } from 'react';
import { Brain, Sparkles, Target, Lightbulb, GitBranch, CheckCircle } from 'lucide-react';

interface NodeEvent {
    event: 'node_start' | 'node_complete' | 'complete';
    node?: string;
    message?: string;
    data?: any;
}

interface AIReasoningPanelProps {
    cvId: string;
    onComplete?: (results: any) => void;
}

const nodeIcons: Record<string, any> = {
    assess_quality: Target,
    contrastive_explain: GitBranch,
    counterfactual_suggest: Lightbulb,
    cot_reasoning: Brain
};

const nodeLabels: Record<string, string> = {
    assess_quality: 'CV Quality Assessment',
    contrastive_explain: 'Match Comparison',
    counterfactual_suggest: 'Improvement Suggestions',
    cot_reasoning: 'AI Reasoning Chain'
};

export const AIReasoningPanel: React.FC<AIReasoningPanelProps> = ({ cvId, onComplete }) => {
    const [currentNode, setCurrentNode] = useState<string | null>(null);
    const [completedNodes, setCompletedNodes] = useState<Set<string>>(new Set());
    const [nodeResults, setNodeResults] = useState<Record<string, any>>({});
    const [streamingText, setStreamingText] = useState<string>('');
    const [isComplete, setIsComplete] = useState(false);

    useEffect(() => {
        const apiBase = import.meta.env.VITE_API_URL?.replace(/^http/, 'ws') || 'ws://localhost:8000';
        const ws = new WebSocket(`${apiBase}/advanced/ws/explain/${cvId}`);

        ws.onopen = () => {
            console.log('🧠 AI Reasoning WebSocket connected');
        };

        ws.onmessage = (event) => {
            const data: NodeEvent = JSON.parse(event.data);

            if (data.event === 'node_start') {
                setCurrentNode(data.node || null);
                setStreamingText('');
                // Simulate token streaming effect
                simulateTokenStream(data.message || 'Processing...');
            } else if (data.event === 'node_complete') {
                setCompletedNodes(prev => new Set([...prev, data.node || '']));
                setNodeResults(prev => ({
                    ...prev,
                    [data.node || '']: data.data
                }));
                setStreamingText('');
            } else if (data.event === 'complete') {
                setIsComplete(true);
                setCurrentNode(null);
                if (onComplete) {
                    onComplete(data.data);
                }
            }
        };

        ws.onerror = (error) => {
            console.error('AI Reasoning WS Error:', error);
        };

        return () => {
            ws.close();
        };
    }, [cvId, onComplete]);

    const simulateTokenStream = (text: string) => {
        let index = 0;
        const interval = setInterval(() => {
            if (index < text.length) {
                setStreamingText(prev => prev + text[index]);
                index++;
            } else {
                clearInterval(interval);
            }
        }, 30);
    };

    return (
        <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-lg p-6 shadow-lg border border-purple-200">
            {/* Header */}
            <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-purple-600 rounded-lg">
                    <Sparkles className="w-6 h-6 text-white" />
                </div>
                <div>
                    <h3 className="text-lg font-bold text-gray-900">AI Premium Analysis</h3>
                    <p className="text-sm text-gray-600">Advanced explainability powered by LangGraph</p>
                </div>
            </div>

            {/* Node Progress */}
            <div className="space-y-4 mb-6">
                {Object.keys(nodeLabels).map((nodeKey) => {
                    const Icon = nodeIcons[nodeKey];
                    const isActive = currentNode === nodeKey;
                    const isCompleted = completedNodes.has(nodeKey);

                    return (
                        <div
                            key={nodeKey}
                            className={`
                                relative p-4 rounded-lg border-2 transition-all duration-300
                                ${isActive ? 'bg-purple-100 border-purple-500 shadow-lg scale-105' : ''}
                                ${isCompleted ? 'bg-green-50 border-green-400' : ''}
                                ${!isActive && !isCompleted ? 'bg-white border-gray-200' : ''}
                            `}
                        >
                            <div className="flex items-start gap-3">
                                {/* Icon */}
                                <div className={`
                                    p-2 rounded-lg
                                    ${isActive ? 'bg-purple-600 animate-pulse' : ''}
                                    ${isCompleted ? 'bg-green-600' : ''}
                                    ${!isActive && !isCompleted ? 'bg-gray-300' : ''}
                                `}>
                                    {isCompleted ? (
                                        <CheckCircle className="w-5 h-5 text-white" />
                                    ) : (
                                        <Icon className={`w-5 h-5 ${isActive || isCompleted ? 'text-white' : 'text-gray-600'}`} />
                                    )}
                                </div>

                                <div className="flex-1">
                                    <h4 className="font-semibold text-gray-900 mb-1">
                                        {nodeLabels[nodeKey]}
                                    </h4>

                                    {/* Streaming Text */}
                                    {isActive && streamingText && (
                                        <p className="text-sm text-purple-700 font-mono">
                                            {streamingText}
                                            <span className="animate-pulse">▋</span>
                                        </p>
                                    )}

                                    {/* Completed Results */}
                                    {isCompleted && nodeResults[nodeKey] && (
                                        <div className="mt-2 text-sm text-gray-700">
                                            {renderNodeResult(nodeKey, nodeResults[nodeKey])}
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Progress Bar for Active Node */}
                            {isActive && (
                                <div className="absolute bottom-0 left-0 right-0 h-1 bg-purple-200 rounded-b-lg overflow-hidden">
                                    <div className="h-full bg-purple-600 animate-progress"></div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Completion Message */}
            {isComplete && (
                <div className="bg-green-100 border-2 border-green-400 rounded-lg p-4 flex items-center gap-3">
                    <CheckCircle className="w-6 h-6 text-green-600" />
                    <div>
                        <p className="font-semibold text-green-900">Analysis Complete!</p>
                        <p className="text-sm text-green-700">Scroll down to view detailed insights</p>
                    </div>
                </div>
            )}
        </div>
    );
};

// Helper function to render node-specific results
function renderNodeResult(nodeKey: string, data: any): React.ReactNode {
    switch (nodeKey) {
        case 'assess_quality':
            return data.quality_score ? (
                <div className="space-y-1">
                    <div className="flex items-center justify-between">
                        <span className="font-medium">Overall Score:</span>
                        <span className="text-lg font-bold text-green-600">
                            {data.quality_score.overall_score || 0}/100
                        </span>
                    </div>
                    <div className="text-xs text-gray-600">
                        ✓ Structure: {data.quality_score.structure_formatting || 0}
                        {' • '}
                        ATS: {data.quality_score.ats_compatibility || 0}
                    </div>
                </div>
            ) : null;

        case 'contrastive_explain':
            return data.contrastive_explanation ? (
                <p className="italic text-gray-700 line-clamp-3">
                    "{data.contrastive_explanation}"
                </p>
            ) : null;

        case 'counterfactual_suggest':
            return data.counterfactual_suggestions?.length > 0 ? (
                <div className="text-xs text-gray-600">
                    ✓ {data.counterfactual_suggestions.length} improvement suggestions generated
                </div>
            ) : null;

        case 'cot_reasoning':
            return data.cot_reasoning ? (
                <p className="text-xs text-gray-600 line-clamp-2">
                    ✓ Step-by-step reasoning completed
                </p>
            ) : null;

        default:
            return <span className="text-xs text-gray-500">✓ Completed</span>;
    }
}

// Add CSS animation for progress bar
const style = document.createElement('style');
style.textContent = `
    @keyframes progress {
        0% { width: 0%; }
        100% { width: 100%; }
    }
    .animate-progress {
        animation: progress 2s ease-in-out infinite;
    }
`;
document.head.appendChild(style);
