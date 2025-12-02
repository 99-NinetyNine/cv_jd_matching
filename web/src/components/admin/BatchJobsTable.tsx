import React from 'react';
import { Briefcase, RefreshCw, Play } from 'lucide-react';

interface BatchJob {
    id: number;
    batch_api_id: string;
    batch_type: string;
    status: string;
    created_at: string;
    request_counts: {
        total: number;
        completed: number;
        failed: number;
    };
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
    return (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 mb-8">
            <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-bold flex items-center gap-2 text-slate-700">
                    <Briefcase size={18} className="text-slate-400" /> Batch Processing History
                </h3>
                <div className="flex gap-2">
                    <button
                        onClick={() => onTrigger('cv')}
                        className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm font-medium transition-colors flex items-center gap-2"
                    >
                        <Play size={14} /> Trigger CV Batch
                    </button>
                    <button
                        onClick={onCheckStatus}
                        className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 text-sm font-medium transition-colors flex items-center gap-2"
                    >
                        <RefreshCw size={14} /> Check Status
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
                            <th className="px-6 py-3 font-semibold">Created At</th>
                            <th className="px-6 py-3 font-semibold">Stats</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                        {batches.length > 0 ? (
                            batches.map((batch) => (
                                <tr key={batch.id} className="hover:bg-slate-50 transition-colors">
                                    <td className="px-6 py-4 font-mono text-xs text-slate-600">{batch.batch_api_id}</td>
                                    <td className="px-6 py-4">
                                        <span className="px-2 py-1 bg-slate-100 rounded text-xs font-medium text-slate-600">{batch.batch_type}</span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <StatusBadge status={batch.status} />
                                    </td>
                                    <td className="px-6 py-4">{new Date(batch.created_at).toLocaleString()}</td>
                                    <td className="px-6 py-4">
                                        {batch.request_counts ? (
                                            <div className="flex gap-2 text-xs">
                                                <span className="text-emerald-600">✓ {batch.request_counts.completed || 0}</span>
                                                <span className="text-red-600">✗ {batch.request_counts.failed || 0}</span>
                                            </div>
                                        ) : '-'}
                                    </td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td className="px-6 py-8 text-center text-slate-400" colSpan={5}>
                                    No batch jobs found.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};
