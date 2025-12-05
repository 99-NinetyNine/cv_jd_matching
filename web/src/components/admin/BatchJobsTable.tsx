import React from 'react';
import { Briefcase, RefreshCw, Play, AlertCircle } from 'lucide-react';

interface BatchJob {
    id: number;
    batch_id?: string;  // Old schema
    batch_api_id?: string;  // New schema
    type?: string;  // Old schema
    batch_type?: string;  // New schema
    status: string;
    total_items?: number;  // Old schema
    processed_items?: number;  // Old schema
    request_counts?: {  // New schema
        total: number;
        completed: number;
        failed: number;
    };
    created_at: string;
    completed_at?: string | null;
    error?: string;
    results?: any;
}

interface BatchJobsTableProps {
    batches: BatchJob[];
    onTrigger: (type: string) => void;
    onCheckStatus: () => void;
}

const StatusBadge = ({ status }: { status: string }) => {
    const styles: any = {
        completed: 'bg-emerald-100 text-emerald-700',
        failed: 'bg-red-100 text-red-700',
        processing: 'bg-blue-100 text-blue-700',
        in_progress: 'bg-blue-100 text-blue-700',
        validating: 'bg-amber-100 text-amber-700',
        pending: 'bg-slate-100 text-slate-700',
    };

    return (
        <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[status] || 'bg-slate-100 text-slate-600'}`}>
            {status}
        </span>
    );
};

export const BatchJobsTable: React.FC<BatchJobsTableProps> = ({ batches, onTrigger, onCheckStatus }) => {
    const [expandedBatch, setExpandedBatch] = React.useState<number | null>(null);

    // Calculate summary statistics
    const summary = batches.reduce((acc, batch) => {
        const status = batch.status.toLowerCase();
        acc.total++;
        if (status === 'completed') acc.completed++;
        else if (status === 'failed') acc.failed++;
        else if (status === 'in_progress' || status === 'processing') acc.processing++;
        else if (status === 'validating' || status === 'pending') acc.pending++;
        return acc;
    }, { total: 0, pending: 0, processing: 0, completed: 0, failed: 0 });

    return (
        <div className="space-y-6">
            {/* Batch Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 text-center">
                    <div className="text-3xl font-bold text-slate-800">{summary.total}</div>
                    <div className="text-xs text-slate-500 mt-1 font-medium">Total Batches</div>
                </div>
                <div className="bg-yellow-50 p-4 rounded-xl shadow-sm border border-yellow-200 text-center">
                    <div className="text-3xl font-bold text-yellow-700">{summary.pending}</div>
                    <div className="text-xs text-yellow-600 mt-1 font-medium">Pending</div>
                </div>
                <div className="bg-blue-50 p-4 rounded-xl shadow-sm border border-blue-200 text-center">
                    <div className="text-3xl font-bold text-blue-700">{summary.processing}</div>
                    <div className="text-xs text-blue-600 mt-1 font-medium">Processing</div>
                </div>
                <div className="bg-green-50 p-4 rounded-xl shadow-sm border border-green-200 text-center">
                    <div className="text-3xl font-bold text-green-700">{summary.completed}</div>
                    <div className="text-xs text-green-600 mt-1 font-medium">Completed</div>
                </div>
                <div className="bg-red-50 p-4 rounded-xl shadow-sm border border-red-200 text-center">
                    <div className="text-3xl font-bold text-red-700">{summary.failed}</div>
                    <div className="text-xs text-red-600 mt-1 font-medium">Failed</div>
                </div>
            </div>

            {/* Batch Jobs Table */}
            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-lg font-bold flex items-center gap-2 text-slate-700">
                        <Briefcase size={18} className="text-slate-400" /> Batch Jobs
                    </h3>
                    <div className="flex gap-2">
                        <button
                            onClick={() => onTrigger('embedding')}
                            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm font-medium transition-colors flex items-center gap-2"
                        >
                            <Play size={14} /> Trigger Embedding
                        </button>
                        <button
                            onClick={() => onTrigger('parsing')}
                            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm font-medium transition-colors flex items-center gap-2"
                        >
                            <Play size={14} /> Trigger Parsing
                        </button>
                        <button
                            onClick={onCheckStatus}
                            className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 text-sm font-medium transition-colors flex items-center gap-2"
                        >
                            <RefreshCw size={14} /> Refresh
                        </button>
                    </div>
                </div>

            <div className="overflow-x-auto">
                <table className="w-full text-sm text-left text-slate-500">
                    <thead className="text-xs text-slate-700 uppercase bg-slate-50 border-b border-slate-200">
                        <tr>
                            <th className="px-6 py-3 font-semibold">Batch ID</th>
                            <th className="px-6 py-3 font-semibold">Type</th>
                            <th className="px-6 py-3 font-semibold">Status</th>
                            <th className="px-6 py-3 font-semibold">Progress</th>
                            <th className="px-6 py-3 font-semibold">Created</th>
                            <th className="px-6 py-3 font-semibold">Duration</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                        {batches.length > 0 ? (
                            batches.map((batch) => {
                                // Handle both old and new schema
                                const batchId = batch.batch_api_id || batch.batch_id || 'unknown';
                                const batchType = batch.batch_type || batch.type || 'unknown';

                                // Calculate progress based on schema
                                let totalItems = 0;
                                let processedItems = 0;

                                if (batch.request_counts) {
                                    // New schema
                                    totalItems = batch.request_counts.total;
                                    processedItems = batch.request_counts.completed + batch.request_counts.failed;
                                } else {
                                    // Old schema
                                    totalItems = batch.total_items || 0;
                                    processedItems = batch.processed_items || 0;
                                }

                                const progressPercent = totalItems > 0
                                    ? Math.round((processedItems / totalItems) * 100)
                                    : 0;

                                const duration = batch.completed_at
                                    ? Math.round((new Date(batch.completed_at).getTime() - new Date(batch.created_at).getTime()) / 1000)
                                    : null;

                                return (
                                    <React.Fragment key={batch.id}>
                                        <tr
                                            className="hover:bg-slate-50 transition-colors cursor-pointer"
                                            onClick={() => setExpandedBatch(expandedBatch === batch.id ? null : batch.id)}
                                        >
                                            <td className="px-6 py-4 font-mono text-xs text-slate-600">
                                                {batchId.length > 16 ? `${batchId.substring(0, 16)}...` : batchId}
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className="px-2 py-1 bg-slate-100 rounded text-xs font-medium text-slate-600">
                                                    {batchType}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <StatusBadge status={batch.status} />
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-2">
                                                    <div className="w-24 h-2 bg-slate-200 rounded-full overflow-hidden">
                                                        <div
                                                            className="h-full bg-indigo-600 transition-all"
                                                            style={{ width: `${progressPercent}%` }}
                                                        />
                                                    </div>
                                                    <span className="text-xs text-slate-600">
                                                        {processedItems}/{totalItems}
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-xs">
                                                {new Date(batch.created_at).toLocaleString()}
                                            </td>
                                            <td className="px-6 py-4 text-xs">
                                                {duration ? `${duration}s` : '-'}
                                            </td>
                                        </tr>
                                        {expandedBatch === batch.id && (
                                            <tr>
                                                <td colSpan={6} className="px-6 py-4 bg-slate-50">
                                                    <div className="space-y-2 text-sm">
                                                        <div className="flex gap-4">
                                                            <div>
                                                                <span className="font-semibold text-slate-700">Full Batch ID:</span>
                                                                <span className="ml-2 font-mono text-xs text-slate-600">{batchId}</span>
                                                            </div>
                                                        </div>
                                                        {batch.request_counts && (
                                                            <div className="grid grid-cols-3 gap-4 mt-3">
                                                                <div className="p-3 bg-white rounded border border-slate-200">
                                                                    <div className="text-xs text-slate-500">Total Requests</div>
                                                                    <div className="text-lg font-bold text-slate-800">{batch.request_counts.total}</div>
                                                                </div>
                                                                <div className="p-3 bg-white rounded border border-slate-200">
                                                                    <div className="text-xs text-slate-500">Completed</div>
                                                                    <div className="text-lg font-bold text-green-600">{batch.request_counts.completed}</div>
                                                                </div>
                                                                <div className="p-3 bg-white rounded border border-slate-200">
                                                                    <div className="text-xs text-slate-500">Failed</div>
                                                                    <div className="text-lg font-bold text-red-600">{batch.request_counts.failed}</div>
                                                                </div>
                                                            </div>
                                                        )}
                                                        {batch.error && (
                                                            <div className="flex items-start gap-2 text-red-600 bg-red-50 p-3 rounded">
                                                                <AlertCircle size={16} className="mt-0.5 flex-shrink-0" />
                                                                <div>
                                                                    <div className="font-semibold">Error:</div>
                                                                    <div className="text-xs">{batch.error}</div>
                                                                </div>
                                                            </div>
                                                        )}
                                                        {batch.results && Object.keys(batch.results).length > 0 && (
                                                            <div className="mt-2">
                                                                <div className="font-semibold text-slate-700 mb-1">Results:</div>
                                                                <pre className="text-xs bg-white p-3 rounded border border-slate-200 overflow-auto max-h-48">
                                                                    {JSON.stringify(batch.results, null, 2)}
                                                                </pre>
                                                            </div>
                                                        )}
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </React.Fragment>
                                );
                            })
                        ) : (
                            <tr>
                                <td className="px-6 py-8 text-center text-slate-400" colSpan={6}>
                                    No batch jobs found. Trigger a batch to get started.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
        </div>
    );
};
