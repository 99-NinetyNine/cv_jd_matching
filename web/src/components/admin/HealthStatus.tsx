import React from 'react';
import { CheckCircle, AlertTriangle, XCircle, Database, Server, Activity } from 'lucide-react';

interface HealthData {
    status: string;
    timestamp: string;
    components: {
        database: string;
        celery_workers: string;
        api: string;
    };
    pending_work: {
        parsing: number;
        embedding: number;
    };
    recent_failures: number;
}

interface HealthStatusProps {
    data: HealthData | null;
    loading: boolean;
}

export const HealthStatus: React.FC<HealthStatusProps> = ({ data, loading }) => {
    if (loading) return <div className="animate-pulse h-24 bg-slate-100 rounded-xl"></div>;
    if (!data) return null;

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'healthy': return <CheckCircle className="text-emerald-500" size={20} />;
            case 'degraded': return <AlertTriangle className="text-amber-500" size={20} />;
            default: return <XCircle className="text-red-500" size={20} />;
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'healthy': return 'bg-emerald-50 border-emerald-100 text-emerald-700';
            case 'degraded': return 'bg-amber-50 border-amber-100 text-amber-700';
            default: return 'bg-red-50 border-red-100 text-red-700';
        }
    };

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            <div className={`p-4 rounded-xl border flex items-center justify-between ${getStatusColor(data.components.database)}`}>
                <div className="flex items-center gap-3">
                    <Database size={20} />
                    <span className="font-medium">Database</span>
                </div>
                {getStatusIcon(data.components.database)}
            </div>

            <div className={`p-4 rounded-xl border flex items-center justify-between ${getStatusColor(data.components.celery_workers)}`}>
                <div className="flex items-center gap-3">
                    <Server size={20} />
                    <span className="font-medium">Workers</span>
                </div>
                {getStatusIcon(data.components.celery_workers)}
            </div>

            <div className={`p-4 rounded-xl border flex items-center justify-between ${getStatusColor(data.components.api)}`}>
                <div className="flex items-center gap-3">
                    <Activity size={20} />
                    <span className="font-medium">API</span>
                </div>
                {getStatusIcon(data.components.api)}
            </div>
        </div>
    );
};
