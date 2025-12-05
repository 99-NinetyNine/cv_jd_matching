import React, { useState, useEffect } from 'react';
import { Sparkles, ArrowRight } from 'lucide-react';
import { LeftPortal } from './LeftPortal';
import { RightPortal } from './RightPortal';

interface AIPortalSectionProps {
    cvId: string;
    isPremium: boolean;
    onComplete: (matches: any[], aiInsights?: any) => void;
}

export const AIPortalSection: React.FC<AIPortalSectionProps> = ({
    cvId,
    isPremium,
    onComplete
}) => {
    const [showQualityPortal, setShowQualityPortal] = useState(false);
    const [userWantsQuality, setUserWantsQuality] = useState<boolean | null>(null);
    const [ws, setWs] = useState<WebSocket | null>(null);
    const [leftPortalData, setLeftPortalData] = useState<any>({});
    const [rightPortalData, setRightPortalData] = useState<any>({});
    const [qualityCheckComplete, setQualityCheckComplete] = useState(false);
    const [analysisComplete, setAnalysisComplete] = useState(false);

    useEffect(() => {
        if (!cvId) return;

        // Connect to WebSocket
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const wsUrl = apiUrl.replace(/^http/, 'ws');
        const websocket = new WebSocket(`${wsUrl}/super-advanced/ws/analyze/${cvId}`);

        websocket.onopen = () => {
            console.log('🔗 AI Portal WebSocket Connected');
        };

        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('📨 WS Message:', data);

            handleWebSocketMessage(data);
        };

        websocket.onerror = (error) => {
            console.error('❌ WebSocket Error:', error);
        };

        websocket.onclose = () => {
            console.log('🔌 WebSocket Closed');
        };

        setWs(websocket);

        return () => {
            if (websocket.readyState === WebSocket.OPEN) {
                websocket.close();
            }
        };
    }, [cvId]);

    const handleWebSocketMessage = (data: any) => {
        switch (data.event) {
            case 'user_choice':
                // Ask user if they want quality check
                break;

            case 'node_start':
                if (data.node === 'parse') {
                    setLeftPortalData((prev: any) => ({ ...prev, status: 'parsing' }));
                } else if (data.node === 'quality') {
                    setRightPortalData((prev: any) => ({ ...prev, status: 'analyzing' }));
                } else if (data.node === 'embed') {
                    setLeftPortalData((prev: any) => ({ ...prev, status: 'embedding' }));
                } else if (data.node === 'search') {
                    setLeftPortalData((prev: any) => ({ ...prev, status: 'searching' }));
                } else if (data.node === 'contrastive' || data.node === 'counterfactual' || data.node === 'cot') {
                    setLeftPortalData((prev: any) => ({ ...prev, status: 'ai_analyzing' }));
                }
                break;

            case 'node_complete':
                if (data.node === 'parse') {
                    setLeftPortalData((prev: any) => ({
                        ...prev,
                        cvText: data.data?.cv_text,
                        parsed: true
                    }));
                } else if (data.node === 'quality') {
                    setRightPortalData((prev: any) => ({
                        ...prev,
                        qualityScores: data.data?.quality_scores,
                        complete: true
                    }));
                    setQualityCheckComplete(true);
                } else if (data.node === 'embed') {
                    setLeftPortalData((prev: any) => ({
                        ...prev,
                        embedded: true
                    }));
                } else if (data.node === 'search') {
                    setLeftPortalData((prev: any) => ({
                        ...prev,
                        matches: data.data?.top_matches,
                        matchingComplete: true
                    }));
                } else if (data.node === 'contrastive') {
                    setLeftPortalData((prev: any) => ({
                        ...prev,
                        contrastiveExplanation: data.data?.contrastive_explanation
                    }));
                } else if (data.node === 'counterfactual') {
                    setLeftPortalData((prev: any) => ({
                        ...prev,
                        counterfactualSuggestions: data.data?.counterfactual_suggestions
                    }));
                } else if (data.node === 'cot') {
                    setLeftPortalData((prev: any) => ({
                        ...prev,
                        cotReasoning: data.data?.cot_reasoning
                    }));
                }
                break;

            case 'quality_scores':
                setRightPortalData((prev: any) => ({
                    ...prev,
                    qualityScores: data.data
                }));
                break;

            case 'token':
                // Streaming quality analysis
                setRightPortalData((prev: any) => ({
                    ...prev,
                    streamingText: (prev.streamingText || '') + data.token
                }));
                break;

            case 'complete':
                setLeftPortalData((prev: any) => ({ ...prev, status: 'complete' }));
                setAnalysisComplete(true);
                break;

            case 'error':
                console.error('Error:', data.message);
                setLeftPortalData((prev: any) => ({ ...prev, error: data.message }));
                break;
        }
    };

    const handleQualityChoice = (wantsQuality: boolean) => {
        setUserWantsQuality(wantsQuality);
        setShowQualityPortal(wantsQuality);

        // Send choice to backend
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ choice: wantsQuality ? 'yes' : 'no' }));
        }
    };

    const handleProceedWithPredictions = () => {
        // User clicked "Give me predictions" in quality portal
        // Continue with the flow
        setLeftPortalData((prev: any) => ({ ...prev, status: 'embedding' }));
    };

    const handleViewResults = () => {
        onComplete(leftPortalData.matches || [], {
            quality_score: rightPortalData.qualityScores,
            contrastive_explanation: leftPortalData.contrastiveExplanation,
            counterfactual_suggestions: leftPortalData.counterfactualSuggestions,
            cot_reasoning: leftPortalData.cotReasoning
        });
    };

    return (
        <div className="bg-white rounded-2xl shadow-xl border border-slate-200 w-full min-h-[600px] flex flex-col overflow-hidden mb-12">
            {/* Header */}
            <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
                        <Sparkles size={24} />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold">AI Analysis Portal</h2>
                        <p className="text-sm text-white/80">Real-time CV processing & matching</p>
                    </div>
                </div>
                {analysisComplete && (
                    <button
                        onClick={handleViewResults}
                        className="flex items-center gap-2 px-6 py-2 bg-white text-indigo-600 font-bold rounded-lg hover:bg-indigo-50 transition-all shadow-md animate-pulse"
                    >
                        View Results <ArrowRight size={18} />
                    </button>
                )}
            </div>

            {/* Quality Check Prompt (if not decided yet) */}
            {userWantsQuality === null && (
                <div className="flex-1 flex items-center justify-center p-8 bg-slate-50">
                    <div className="text-center max-w-md">
                        <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
                            <Sparkles size={40} className="text-white" />
                        </div>
                        <h3 className="text-2xl font-bold text-gray-900 mb-4">
                            Want a Quality Check?
                        </h3>
                        <p className="text-gray-600 mb-8">
                            Get detailed feedback on your CV quality before we find matches.
                            This will open a dual-portal experience!
                        </p>
                        <div className="flex gap-4 justify-center">
                            <button
                                onClick={() => handleQualityChoice(true)}
                                className="px-8 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold rounded-lg hover:shadow-lg transition-all"
                            >
                                Yes, Review My CV
                            </button>
                            <button
                                onClick={() => handleQualityChoice(false)}
                                className="px-8 py-3 bg-white border border-gray-300 text-gray-700 font-semibold rounded-lg hover:bg-gray-50 transition-all"
                            >
                                Skip to Matching
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Portal Content */}
            {userWantsQuality !== null && (
                <div className="flex-1 flex overflow-hidden min-h-[500px]">
                    {/* Left Portal - Always visible */}
                    <div className={`${showQualityPortal ? 'w-1/2' : 'w-full'} border-r border-gray-200 overflow-y-auto transition-all duration-500`}>
                        <LeftPortal data={leftPortalData} />
                    </div>

                    {/* Right Portal - Quality Check */}
                    {showQualityPortal && (
                        <div className="w-1/2 overflow-y-auto bg-gradient-to-br from-purple-50 to-pink-50">
                            <RightPortal
                                data={rightPortalData}
                                onProceed={handleProceedWithPredictions}
                                isComplete={qualityCheckComplete}
                            />
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};
