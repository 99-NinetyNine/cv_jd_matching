import React, { memo } from 'react';
import { CheckCircle, Trash2, Plus, ChevronUp, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ReviewSectionProps {
    parsedData: any;
    expandedSections: Set<string>;
    toggleSection: (section: string) => void;
    updateBasics: (field: string, value: any) => void;
    updateArrayItem: (section: string, index: number, field: string, value: any) => void;
    addArrayItem: (section: string, template: any) => void;
    removeArrayItem: (section: string, index: number) => void;
    onConfirm: () => void;
    onCancel: () => void;
}

const CollapsibleSection = memo(({ title, isExpanded, onToggle, children }: any) => (
    <div className="border border-slate-200 rounded-lg overflow-hidden mb-4">
        <button
            onClick={onToggle}
            className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 flex items-center justify-between transition-colors"
        >
            <span className="font-semibold text-slate-700">{title}</span>
            {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </button>
        <AnimatePresence>
            {isExpanded && (
                <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: 'auto' }}
                    exit={{ height: 0 }}
                    className="overflow-hidden"
                >
                    <div className="p-4 space-y-4">
                        {children}
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    </div>
));

export const ReviewSection: React.FC<ReviewSectionProps> = ({
    parsedData,
    expandedSections,
    toggleSection,
    updateBasics,
    updateArrayItem,
    addArrayItem,
    removeArrayItem,
    onConfirm,
    onCancel
}) => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 mb-12 max-w-4xl mx-auto"
        >
            <div className="flex items-center gap-2 mb-6 text-emerald-600 font-medium">
                <CheckCircle size={20} /> CV Parsed Successfully. Please Review and Edit.
            </div>

            {/* Basics Section */}
            <CollapsibleSection
                title="Basic Information"
                isExpanded={expandedSections.has('basics')}
                onToggle={() => toggleSection('basics')}
            >
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Full Name</label>
                        <input
                            type="text"
                            value={parsedData.basics?.name || ''}
                            onChange={(e) => updateBasics('name', e.target.value)}
                            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                        <input
                            type="email"
                            value={parsedData.basics?.email || ''}
                            onChange={(e) => updateBasics('email', e.target.value)}
                            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Phone</label>
                        <input
                            type="tel"
                            value={parsedData.basics?.phone || ''}
                            onChange={(e) => updateBasics('phone', e.target.value)}
                            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Job Title/Label</label>
                        <input
                            type="text"
                            value={parsedData.basics?.label || ''}
                            onChange={(e) => updateBasics('label', e.target.value)}
                            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                        />
                    </div>
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Professional Summary</label>
                    <textarea
                        value={parsedData.basics?.summary || ''}
                        onChange={(e) => updateBasics('summary', e.target.value)}
                        rows={4}
                        className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    />
                </div>
            </CollapsibleSection>

            {/* Work Experience */}
            <CollapsibleSection
                title={`Work Experience (${parsedData.work?.length || 0})`}
                isExpanded={expandedSections.has('work')}
                onToggle={() => toggleSection('work')}
            >
                {(parsedData.work || []).map((work: any, index: number) => (
                    <div key={index} className="border border-slate-200 rounded-lg p-4 relative">
                        <button
                            onClick={() => removeArrayItem('work', index)}
                            className="absolute top-2 right-2 text-red-500 hover:text-red-700"
                        >
                            <Trash2 size={16} />
                        </button>
                        <div className="grid grid-cols-2 gap-3 mb-3">
                            <input
                                placeholder="Position"
                                value={work.position || ''}
                                onChange={(e) => updateArrayItem('work', index, 'position', e.target.value)}
                                className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                            />
                            <input
                                placeholder="Company"
                                value={work.name || ''}
                                onChange={(e) => updateArrayItem('work', index, 'name', e.target.value)}
                                className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                            />
                            <input
                                placeholder="Start Date"
                                value={work.startDate || ''}
                                onChange={(e) => updateArrayItem('work', index, 'startDate', e.target.value)}
                                className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                            />
                            <input
                                placeholder="End Date"
                                value={work.endDate || ''}
                                onChange={(e) => updateArrayItem('work', index, 'endDate', e.target.value)}
                                className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                            />
                        </div>
                        <textarea
                            placeholder="Summary"
                            value={work.summary || ''}
                            onChange={(e) => updateArrayItem('work', index, 'summary', e.target.value)}
                            rows={2}
                            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                        />
                    </div>
                ))}
                <button
                    onClick={() => addArrayItem('work', { position: '', name: '', startDate: '', endDate: '', summary: '', highlights: [] })}
                    className="flex items-center gap-2 text-indigo-600 hover:text-indigo-700 font-medium text-sm"
                >
                    <Plus size={16} /> Add Work Experience
                </button>
            </CollapsibleSection>

            {/* Education */}
            <CollapsibleSection
                title={`Education (${parsedData.education?.length || 0})`}
                isExpanded={expandedSections.has('education')}
                onToggle={() => toggleSection('education')}
            >
                {(parsedData.education || []).map((edu: any, index: number) => (
                    <div key={index} className="border border-slate-200 rounded-lg p-4 relative">
                        <button
                            onClick={() => removeArrayItem('education', index)}
                            className="absolute top-2 right-2 text-red-500 hover:text-red-700"
                        >
                            <Trash2 size={16} />
                        </button>
                        <div className="grid grid-cols-2 gap-3">
                            <input
                                placeholder="Institution"
                                value={edu.institution || ''}
                                onChange={(e) => updateArrayItem('education', index, 'institution', e.target.value)}
                                className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                            />
                            <input
                                placeholder="Degree"
                                value={edu.studyType || ''}
                                onChange={(e) => updateArrayItem('education', index, 'studyType', e.target.value)}
                                className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                            />
                            <input
                                placeholder="Field of Study"
                                value={edu.area || ''}
                                onChange={(e) => updateArrayItem('education', index, 'area', e.target.value)}
                                className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                            />
                            <input
                                placeholder="End Date"
                                value={edu.endDate || ''}
                                onChange={(e) => updateArrayItem('education', index, 'endDate', e.target.value)}
                                className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                            />
                        </div>
                    </div>
                ))}
                <button
                    onClick={() => addArrayItem('education', { institution: '', studyType: '', area: '', endDate: '' })}
                    className="flex items-center gap-2 text-indigo-600 hover:text-indigo-700 font-medium text-sm"
                >
                    <Plus size={16} /> Add Education
                </button>
            </CollapsibleSection>

            {/* Skills */}
            <CollapsibleSection
                title={`Skills (${parsedData.skills?.length || 0})`}
                isExpanded={expandedSections.has('skills')}
                onToggle={() => toggleSection('skills')}
            >
                <div className="flex flex-wrap gap-2">
                    {(parsedData.skills || []).map((skill: any, index: number) => (
                        <div key={index} className="flex items-center gap-2 bg-indigo-50 text-indigo-700 px-3 py-1 rounded-full text-sm">
                            <input
                                value={typeof skill === 'string' ? skill : skill.name || ''}
                                onChange={(e) => updateArrayItem('skills', index, 'name', e.target.value)}
                                className="bg-transparent border-none outline-none w-24"
                            />
                            <button
                                onClick={() => removeArrayItem('skills', index)}
                                className="text-indigo-500 hover:text-indigo-700"
                            >
                                <Trash2 size={14} />
                            </button>
                        </div>
                    ))}
                    <button
                        onClick={() => addArrayItem('skills', { name: '', keywords: [] })}
                        className="flex items-center gap-1 text-indigo-600 hover:text-indigo-700 font-medium text-sm px-3 py-1 border border-indigo-300 rounded-full"
                    >
                        <Plus size={14} /> Add Skill
                    </button>
                </div>
            </CollapsibleSection>

            {/* Projects */}
            <CollapsibleSection
                title={`Projects (${parsedData.projects?.length || 0})`}
                isExpanded={expandedSections.has('projects')}
                onToggle={() => toggleSection('projects')}
            >
                {(parsedData.projects || []).map((project: any, index: number) => (
                    <div key={index} className="border border-slate-200 rounded-lg p-4 relative">
                        <button
                            onClick={() => removeArrayItem('projects', index)}
                            className="absolute top-2 right-2 text-red-500 hover:text-red-700"
                        >
                            <Trash2 size={16} />
                        </button>
                        <input
                            placeholder="Project Name"
                            value={project.name || ''}
                            onChange={(e) => updateArrayItem('projects', index, 'name', e.target.value)}
                            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm mb-2"
                        />
                        <textarea
                            placeholder="Description"
                            value={project.description || ''}
                            onChange={(e) => updateArrayItem('projects', index, 'description', e.target.value)}
                            rows={2}
                            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                        />
                    </div>
                ))}
                <button
                    onClick={() => addArrayItem('projects', { name: '', description: '', highlights: [] })}
                    className="flex items-center gap-2 text-indigo-600 hover:text-indigo-700 font-medium text-sm"
                >
                    <Plus size={16} /> Add Project
                </button>
            </CollapsibleSection>

            {/* Certificates */}
            <CollapsibleSection
                title={`Certificates (${parsedData.certificates?.length || 0})`}
                isExpanded={expandedSections.has('certificates')}
                onToggle={() => toggleSection('certificates')}
            >
                {(parsedData.certificates || []).map((cert: any, index: number) => (
                    <div key={index} className="flex items-center gap-2 border border-slate-200 rounded-lg p-3">
                        <input
                            placeholder="Certificate Name"
                            value={cert.name || ''}
                            onChange={(e) => updateArrayItem('certificates', index, 'name', e.target.value)}
                            className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-sm"
                        />
                        <input
                            placeholder="Issuer"
                            value={cert.issuer || ''}
                            onChange={(e) => updateArrayItem('certificates', index, 'issuer', e.target.value)}
                            className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-sm"
                        />
                        <button
                            onClick={() => removeArrayItem('certificates', index)}
                            className="text-red-500 hover:text-red-700"
                        >
                            <Trash2 size={16} />
                        </button>
                    </div>
                ))}
                <button
                    onClick={() => addArrayItem('certificates', { name: '', issuer: '', date: '' })}
                    className="flex items-center gap-2 text-indigo-600 hover:text-indigo-700 font-medium text-sm"
                >
                    <Plus size={16} /> Add Certificate
                </button>
            </CollapsibleSection>

            <div className="pt-6 flex justify-end gap-3 border-t border-slate-200">
                <button
                    onClick={onCancel}
                    className="px-6 py-2 border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-50"
                >
                    Cancel
                </button>
                <button
                    onClick={onConfirm}
                    className="px-6 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700"
                >
                    Confirm & Match
                </button>
            </div>
        </motion.div>
    );
};
