import React from 'react';
import { Upload, AlertCircle } from 'lucide-react';

interface UploadSectionProps {
    file: File | null;
    error: string | null;
    status: string;
    onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
    onUpload: () => void;
    isPremium: boolean;
}

export const UploadSection: React.FC<UploadSectionProps> = ({
    file,
    error,
    status,
    onFileChange,
    onUpload,
    isPremium
}) => {
    return (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 mb-12 max-w-2xl mx-auto">
            <div className="border-2 border-dashed border-slate-200 rounded-xl p-8 text-center hover:border-indigo-400 transition-colors bg-slate-50/50">
                <input
                    type="file"
                    id="cv-upload"
                    className="hidden"
                    accept=".pdf"
                    onChange={onFileChange}
                />
                <label htmlFor="cv-upload" className="cursor-pointer flex flex-col items-center">
                    <div className="w-16 h-16 bg-indigo-50 rounded-full flex items-center justify-center text-indigo-600 mb-4">
                        <Upload size={32} />
                    </div>
                    <span className="text-lg font-semibold text-slate-900 mb-1">
                        {file ? file.name : "Upload your CV"}
                    </span>
                    <span className="text-sm text-slate-500 mb-6">
                        {file ? "Click to change file" : "PDF files only, max 5MB"}
                    </span>
                </label>
                {file && (
                    <button
                        onClick={onUpload}
                        disabled={['uploading', 'parsing', 'matching', 'ai_analyzing'].includes(status)}
                        className={`px-8 py-3 rounded-lg font-bold text-white transition-all shadow-lg transform hover:scale-105 ${['uploading', 'parsing', 'matching', 'ai_analyzing'].includes(status)
                                ? 'bg-slate-400 cursor-not-allowed'
                                : isPremium
                                    ? 'bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 hover:shadow-xl animate-pulse'
                                    : 'bg-indigo-600 hover:bg-indigo-700'
                            }`}
                    >
                        {isPremium ? '✨ Unlock AI Portal' : 'Upload CV'}
                    </button>
                )}
            </div>

            {error && (
                <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2 text-sm border border-red-100">
                    <AlertCircle size={16} /> {error}
                </div>
            )}

            {!isPremium && (
                <div className="mt-4 text-center text-xs text-slate-500">
                    Non-premium users will be processed in batch mode. Results will be available later.
                </div>
            )}
        </div>
    );
};
