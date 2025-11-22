import React from 'react';
import { Link } from 'react-router-dom';
import { Briefcase, ArrowRight, Zap, Globe, Cpu, BarChart, Users, CheckCircle } from 'lucide-react';
import { motion } from 'framer-motion';

const Landing = () => {
    return (
        <div className="min-h-screen bg-white font-sans text-slate-900 selection:bg-indigo-100 selection:text-indigo-900">
            {/* Background Gradients */}
            <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
                <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-indigo-50 rounded-full blur-[120px]" />
                <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-purple-50 rounded-full blur-[120px]" />
            </div>

            {/* Navigation */}
            <nav className="fixed top-0 w-full border-b border-slate-100 bg-white/80 backdrop-blur-xl z-50">
                <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-600/20">
                            <Briefcase size={22} />
                        </div>
                        <span className="text-xl font-bold tracking-tight text-slate-900">TalentMatch<span className="text-indigo-600">.ai</span></span>
                    </div>
                    <div className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600">
                        <a href="#features" className="hover:text-indigo-600 transition-colors">Features</a>
                        <a href="#solutions" className="hover:text-indigo-600 transition-colors">Solutions</a>
                        <a href="#pricing" className="hover:text-indigo-600 transition-colors">Pricing</a>
                    </div>
                    <div className="flex items-center gap-4">
                        <Link to="/candidate" className="text-sm font-medium text-slate-600 hover:text-indigo-600 transition-colors">Sign In</Link>
                        <Link to="/hirer" className="group relative px-6 py-2.5 rounded-lg bg-slate-900 text-white text-sm font-bold hover:bg-slate-800 transition-all overflow-hidden shadow-lg shadow-slate-900/20">
                            <span className="relative z-10 group-hover:mr-2 transition-all">Get Started</span>
                            <ArrowRight size={16} className="absolute right-4 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-all text-white" />
                        </Link>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="relative pt-32 pb-20 md:pt-48 md:pb-32 overflow-hidden z-10">
                <div className="max-w-7xl mx-auto px-6 text-center">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6 }}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-sm font-medium mb-8"
                    >
                        <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-600"></span>
                        </span>
                        New: Multi-LLM Support for Enterprise
                    </motion.div>

                    <motion.h1
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6, delay: 0.1 }}
                        className="text-5xl md:text-7xl font-bold tracking-tight mb-8 leading-[1.1] text-slate-900"
                    >
                        Hiring Intelligence, <br />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-600 animate-gradient bg-300%">Reimagined.</span>
                    </motion.h1>

                    <motion.p
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6, delay: 0.2 }}
                        className="text-lg md:text-xl text-slate-600 mb-12 max-w-2xl mx-auto leading-relaxed"
                    >
                        Stop filtering CVs manually. Our AI engine parses, understands, and ranks candidates with human-level precision at machine speed.
                    </motion.p>

                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6, delay: 0.3 }}
                        className="flex flex-col sm:flex-row items-center justify-center gap-4"
                    >
                        <Link to="/hirer" className="w-full sm:w-auto px-8 py-4 rounded-xl bg-indigo-600 text-white font-bold hover:bg-indigo-700 transition-all shadow-xl shadow-indigo-600/20 flex items-center justify-center gap-2">
                            <Briefcase size={20} /> I'm Hiring
                        </Link>
                        <Link to="/candidate" className="w-full sm:w-auto px-8 py-4 rounded-xl bg-white border border-slate-200 text-slate-700 font-bold hover:bg-slate-50 transition-all shadow-sm flex items-center justify-center gap-2">
                            <Users size={20} /> I'm a Candidate
                        </Link>
                    </motion.div>

                    {/* Dashboard Preview Mockup */}
                    <motion.div
                        initial={{ opacity: 0, y: 40, rotateX: 10 }}
                        animate={{ opacity: 1, y: 0, rotateX: 0 }}
                        transition={{ duration: 0.8, delay: 0.5 }}
                        className="mt-20 relative mx-auto max-w-5xl perspective-1000"
                    >
                        <div className="relative rounded-2xl border border-slate-200 bg-white shadow-2xl shadow-slate-200/50 overflow-hidden transform-gpu">
                            <div className="p-4 border-b border-slate-100 flex items-center gap-4 bg-slate-50/50">
                                <div className="flex gap-2">
                                    <div className="w-3 h-3 rounded-full bg-red-400/80" />
                                    <div className="w-3 h-3 rounded-full bg-amber-400/80" />
                                    <div className="w-3 h-3 rounded-full bg-emerald-400/80" />
                                </div>
                                <div className="h-6 w-64 bg-slate-200/50 rounded-md" />
                            </div>
                            <div className="p-8 grid grid-cols-3 gap-6 bg-slate-50/30">
                                <div className="col-span-1 space-y-4">
                                    <div className="h-32 rounded-xl bg-white border border-slate-100 shadow-sm animate-pulse" />
                                    <div className="h-32 rounded-xl bg-white border border-slate-100 shadow-sm" />
                                </div>
                                <div className="col-span-2 space-y-4">
                                    <div className="h-16 rounded-xl bg-white border border-slate-100 shadow-sm flex items-center px-4 gap-4">
                                        <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center font-bold">JD</div>
                                        <div className="h-4 w-32 bg-slate-100 rounded" />
                                        <div className="ml-auto h-8 w-20 bg-indigo-600 rounded-lg opacity-10" />
                                    </div>
                                    <div className="h-16 rounded-xl bg-white border border-slate-100 shadow-sm flex items-center px-4 gap-4">
                                        <div className="w-8 h-8 rounded-full bg-slate-100" />
                                        <div className="h-4 w-32 bg-slate-100 rounded" />
                                    </div>
                                    <div className="h-16 rounded-xl bg-white border border-slate-100 shadow-sm flex items-center px-4 gap-4">
                                        <div className="w-8 h-8 rounded-full bg-slate-100" />
                                        <div className="h-4 w-32 bg-slate-100 rounded" />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </div>
            </section>

            {/* Features Bento Grid */}
            <section id="features" className="py-32 relative z-10 bg-slate-50">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="text-center mb-20">
                        <h2 className="text-3xl md:text-5xl font-bold mb-6 text-slate-900">Built for the <span className="text-indigo-600">Future of Work</span></h2>
                        <p className="text-slate-600 max-w-2xl mx-auto text-lg">Everything you need to modernize your recruitment stack, from parsing to placement.</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {/* Feature 1 - Large */}
                        <motion.div
                            whileHover={{ y: -5 }}
                            className="md:col-span-2 bg-white border border-slate-200 rounded-3xl p-8 md:p-12 relative overflow-hidden group shadow-sm hover:shadow-md transition-all"
                        >
                            <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-50 rounded-full blur-[80px] group-hover:bg-indigo-100 transition-all duration-500" />
                            <div className="relative z-10">
                                <div className="w-14 h-14 bg-indigo-50 rounded-2xl flex items-center justify-center text-indigo-600 mb-6 border border-indigo-100">
                                    <Cpu size={28} />
                                </div>
                                <h3 className="text-2xl font-bold mb-4 text-slate-900">Hybrid Parsing Engine</h3>
                                <p className="text-slate-600 text-lg leading-relaxed max-w-md">
                                    Our proprietary engine combines OCR for scanned documents with LLMs for semantic understanding, delivering 99.9% accuracy across all formats.
                                </p>
                            </div>
                        </motion.div>

                        {/* Feature 2 */}
                        <motion.div
                            whileHover={{ y: -5 }}
                            className="bg-white border border-slate-200 rounded-3xl p-8 relative overflow-hidden group shadow-sm hover:shadow-md transition-all"
                        >
                            <div className="w-12 h-12 bg-purple-50 rounded-xl flex items-center justify-center text-purple-600 mb-6 border border-purple-100">
                                <Zap size={24} />
                            </div>
                            <h3 className="text-xl font-bold mb-3 text-slate-900">Instant Matching</h3>
                            <p className="text-slate-600">Real-time vector similarity search ranks thousands of candidates in milliseconds.</p>
                        </motion.div>

                        {/* Feature 3 */}
                        <motion.div
                            whileHover={{ y: -5 }}
                            className="bg-white border border-slate-200 rounded-3xl p-8 relative overflow-hidden group shadow-sm hover:shadow-md transition-all"
                        >
                            <div className="w-12 h-12 bg-emerald-50 rounded-xl flex items-center justify-center text-emerald-600 mb-6 border border-emerald-100">
                                <Globe size={24} />
                            </div>
                            <h3 className="text-xl font-bold mb-3 text-slate-900">Global Reach</h3>
                            <p className="text-slate-600">Native support for English, Spanish, French, and German CVs with auto-translation.</p>
                        </motion.div>

                        {/* Feature 4 - Large */}
                        <motion.div
                            whileHover={{ y: -5 }}
                            className="md:col-span-2 bg-white border border-slate-200 rounded-3xl p-8 md:p-12 relative overflow-hidden group shadow-sm hover:shadow-md transition-all"
                        >
                            <div className="absolute top-0 left-0 w-64 h-64 bg-purple-50 rounded-full blur-[80px] group-hover:bg-purple-100 transition-all duration-500" />
                            <div className="relative z-10">
                                <div className="w-14 h-14 bg-pink-50 rounded-2xl flex items-center justify-center text-pink-600 mb-6 border border-pink-100">
                                    <BarChart size={28} />
                                </div>
                                <h3 className="text-2xl font-bold mb-4 text-slate-900">Deep Analytics</h3>
                                <p className="text-slate-600 text-lg leading-relaxed max-w-md">
                                    Gain insights into your hiring pipeline with automated reporting on time-to-hire, candidate quality, and source effectiveness.
                                </p>
                            </div>
                        </motion.div>
                    </div>
                </div>
            </section>

            {/* Social Proof */}
            <section className="py-20 border-y border-slate-200 bg-white">
                <div className="max-w-7xl mx-auto px-6 text-center">
                    <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-10">Trusted by innovative teams worldwide</p>
                    <div className="flex flex-wrap justify-center gap-12 md:gap-20 opacity-60 grayscale hover:grayscale-0 transition-all duration-500">
                        {/* Placeholders for logos - using dark text for white theme */}
                        <div className="text-2xl font-bold text-slate-800 flex items-center gap-2"><div className="w-6 h-6 bg-slate-800 rounded-full" /> Acme Corp</div>
                        <div className="text-2xl font-bold text-slate-800 flex items-center gap-2"><div className="w-6 h-6 bg-slate-800 rounded-md" /> TechFlow</div>
                        <div className="text-2xl font-bold text-slate-800 flex items-center gap-2"><div className="w-6 h-6 bg-slate-800 rotate-45" /> Nebulon</div>
                        <div className="text-2xl font-bold text-slate-800 flex items-center gap-2"><div className="w-6 h-6 bg-slate-800 rounded-full border-2 border-slate-800" /> Vertex</div>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="bg-slate-50 pt-24 pb-12 border-t border-slate-200">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="grid md:grid-cols-4 gap-12 mb-16">
                        <div className="col-span-1 md:col-span-2">
                            <div className="flex items-center gap-2 mb-6">
                                <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white">
                                    <Briefcase size={18} />
                                </div>
                                <span className="text-xl font-bold text-slate-900">TalentMatch.ai</span>
                            </div>
                            <p className="text-slate-500 max-w-xs leading-relaxed">
                                The intelligent operating system for modern recruitment teams. Built for speed, accuracy, and scale.
                            </p>
                        </div>
                        <div>
                            <h4 className="text-slate-900 font-bold mb-6">Product</h4>
                            <ul className="space-y-4 text-slate-500 text-sm">
                                <li><a href="#" className="hover:text-indigo-600 transition-colors">Features</a></li>
                                <li><a href="#" className="hover:text-indigo-600 transition-colors">Integrations</a></li>
                                <li><a href="#" className="hover:text-indigo-600 transition-colors">Enterprise</a></li>
                                <li><a href="#" className="hover:text-indigo-600 transition-colors">Changelog</a></li>
                            </ul>
                        </div>
                        <div>
                            <h4 className="text-slate-900 font-bold mb-6">Company</h4>
                            <ul className="space-y-4 text-slate-500 text-sm">
                                <li><a href="#" className="hover:text-indigo-600 transition-colors">About Us</a></li>
                                <li><a href="#" className="hover:text-indigo-600 transition-colors">Careers</a></li>
                                <li><a href="#" className="hover:text-indigo-600 transition-colors">Blog</a></li>
                                <li><a href="#" className="hover:text-indigo-600 transition-colors">Contact</a></li>
                            </ul>
                        </div>
                    </div>
                    <div className="pt-8 border-t border-slate-200 flex flex-col md:flex-row items-center justify-between gap-4">
                        <p className="text-slate-500 text-sm">&copy; 2025 TalentMatch AI. All rights reserved.</p>
                        <div className="flex gap-6 text-slate-500 text-sm">
                            <a href="#" className="hover:text-indigo-600 transition-colors">Privacy Policy</a>
                            <a href="#" className="hover:text-indigo-600 transition-colors">Terms of Service</a>
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    );
};

export default Landing;
