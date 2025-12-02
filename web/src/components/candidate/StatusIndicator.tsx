import React, { memo } from 'react';

interface StatusIndicatorProps {
    status: 'idle' | 'uploading' | 'parsing' | 'reviewing' | 'matching' | 'complete';
}

export const StatusIndicator = memo(({ status }: StatusIndicatorProps) => {
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
