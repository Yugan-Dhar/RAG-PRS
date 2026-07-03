import React, { useState, useEffect, useRef } from 'react';
import { 
  UploadCloud, FileText, CheckCircle, AlertTriangle, XCircle, Search, 
  Settings, Home, Grid, Folder, PieChart as PieChartIcon, Clock, Users, Shield, 
  Bell, ChevronRight, X, HelpCircle, ExternalLink
} from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip } from 'recharts';

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export default function App() {
  const [standards, setStandards] = useState([]);
  const [frameworks, setFrameworks] = useState([]);
  const [selectedStandard, setSelectedStandard] = useState('');
  const [selectedFramework, setSelectedFramework] = useState('');
  
  const [routerType, setRouterType] = useState('conventional');
  const [capabilities, setCapabilities] = useState([]);
  const [file, setFile] = useState(null);
  
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState('');
  
  const [report, setReport] = useState(null);
  const [expandedRows, setExpandedRows] = useState({});
  const [activeTab, setActiveTab] = useState('Dashboard');

  const fileInputRef = useRef(null);

  useEffect(() => {
    fetch(`${API_URL}/standards`)
      .then(res => res.json())
      .then(data => setStandards(data))
      .catch(err => console.error("Error fetching standards", err));
  }, []);

  useEffect(() => {
    if (!selectedStandard) {
      setFrameworks([]);
      return;
    }
    fetch(`${API_URL}/standards/${selectedStandard}/frameworks`)
      .then(res => res.json())
      .then(data => setFrameworks(data))
      .catch(err => console.error("Error fetching frameworks", err));
  }, [selectedStandard]);

  const handleCapabilityToggle = (val) => {
    setCapabilities(prev => prev.includes(val) ? prev.filter(c => c !== val) : [...prev, val]);
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleStartAnalysis = async () => {
    if (!file) {
      if (report) {
        setActiveTab('Reports');
        return;
      }
      alert("Please upload a document first.");
      return;
    }
    if (!selectedFramework) {
      alert("Please select a standard and framework.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("standard_id", selectedStandard);
    formData.append("framework_id", selectedFramework);
    
    if (selectedFramework === 'ITSAR-ROUTER') {
      formData.append("router_type", routerType);
      formData.append("capability_flags", capabilities.join(','));
    }

    setLoading(true);
    setStatusText("Uploading and Initializing Analysis...");

    try {
      const res = await fetch(`${API_URL}/assess`, {
        method: 'POST',
        body: formData
      });
      
      if (!res.ok) throw new Error("Failed to start assessment");
      const jobData = await res.json();
      const jobId = jobData.id;

      // Poll
      const pollInterval = setInterval(async () => {
        const pollRes = await fetch(`${API_URL}/reports/${jobId}`);
        if (!pollRes.ok) return;
        
        const reportData = await pollRes.json();
        const total = reportData.total || 0;
        const processed = reportData.processed || 0;
        
        if (total > 0) {
          setStatusText(`Analyzing requirements... (${processed} / ${total})`);
        } else {
          setStatusText(`Processing document...`);
        }

        if (reportData.status === 'completed' || reportData.status === 'failed') {
          clearInterval(pollInterval);
          setLoading(false);
          
          if (reportData.status === 'completed') {
            processReportData(reportData);
          } else {
            alert("Analysis failed: " + reportData.document_id);
          }
        }
      }, 2500);
    } catch (err) {
      console.error(err);
      setLoading(false);
      alert("Error starting analysis: " + err.message);
    }
  };

  const processReportData = (data) => {
    let counts = {compliant: 0, non_compliant: 0, partial: 0, manual_review: 0, evidence_not_found: 0};
    const groupMap = {};
    const ungrouped = [];

    data.results?.forEach(r => {
      counts[r.status] = (counts[r.status] || 0) + 1;
      
      if (r.id.startsWith('GROUP-')) {
        const groupId = r.id.replace('GROUP-', '');
        if (!groupMap[groupId]) groupMap[groupId] = { group: null, children: [] };
        groupMap[groupId].group = r;
      } else {
        const parts = r.id.split('.');
        let groupId = null;
        if (parts.length >= 2) {
          groupId = parts.slice(0, 2).join('.');
        }
        if (groupId) {
          if (!groupMap[groupId]) groupMap[groupId] = { group: null, children: [] };
          groupMap[groupId].children.push(r);
        } else {
          ungrouped.push(r);
        }
      }
    });

    const sortedGroups = Object.keys(groupMap).sort((a, b) => {
      const aParts = a.split('.').map(Number);
      const bParts = b.split('.').map(Number);
      for (let i = 0; i < Math.max(aParts.length, bParts.length); i++) {
        const av = aParts[i] || 0;
        const bv = bParts[i] || 0;
        if (av !== bv) return av - bv;
      }
      return 0;
    }).map(k => ({ 
      id: k, 
      title: data.group_titles ? data.group_titles[k] : '',
      ...groupMap[k] 
    }));

    setReport({ counts, groups: sortedGroups, ungrouped, raw: data, group_titles: data.group_titles || {} });
  };

  const parseJustification = (text) => {
    const rawJust = text || '';
    try {
      const parsed = JSON.parse(rawJust);
      return {
        isJson: true,
        extracted_evidence: parsed.extracted_evidence || [],
        matched_concepts: parsed.matched_concepts || [],
        missing_concepts: parsed.missing_concepts || [],
        verdict: parsed.verdict || '',
        recommendation: parsed.recommendation || '',
        justification: parsed.justification || '',
        raw: rawJust
      };
    } catch (e) {
      // Fallback
      const providesMatch = rawJust.match(/PRODUCT PROVIDES:\s*([\s\S]*?)(?=GAP IDENTIFIED:|RECOMMENDATION:|\[EVIDENCE\]|$)/);
      const gapMatch = rawJust.match(/GAP(?: IDENTIFIED)?:\s*([\s\S]*?)(?=RECOMMENDATION:|\[EVIDENCE\]|$)/);
      const recMatch = rawJust.match(/RECOMMENDATION:\s*([\s\S]*?)(?=\[EVIDENCE\]|$)/);
      const evidenceMatch = rawJust.match(/\[EVIDENCE\]([\s\S]*)$/);

      return {
        isJson: false,
        provides: providesMatch ? providesMatch[1].trim() : '',
        gap: gapMatch ? gapMatch[1].trim() : '',
        rec: recMatch ? recMatch[1].trim() : '',
        evidence: evidenceMatch ? evidenceMatch[1].trim() : '',
        raw: rawJust
      };
    }
  };

  const getStatusConfig = (status) => {
    switch (status) {
      case 'compliant': return { icon: <CheckCircle className="w-4 h-4 text-emerald-500" />, color: 'text-emerald-500', bg: 'bg-emerald-500/10', label: 'Compliant' };
      case 'non_compliant': return { icon: <XCircle className="w-4 h-4 text-red-500" />, color: 'text-red-500', bg: 'bg-red-500/10', label: 'Non-Compliant' };
      case 'partial': return { icon: <AlertTriangle className="w-4 h-4 text-amber-500" />, color: 'text-amber-500', bg: 'bg-amber-500/10', label: 'Partial' };
      case 'manual_review': return { icon: <Search className="w-4 h-4 text-purple-500" />, color: 'text-purple-500', bg: 'bg-purple-500/10', label: 'Manual Review' };
      case 'evidence_not_found': return { icon: <HelpCircle className="w-4 h-4 text-slate-400" />, color: 'text-slate-400', bg: 'bg-slate-400/10', label: 'Evidence Not Found' };
      default: return { icon: null, color: 'text-gray-400', bg: 'bg-gray-800', label: status };
    }
  };

  // UI Components
  const SidebarItem = ({ icon: Icon, label, active }) => (
    <div className={`flex items-center px-4 py-2.5 my-1 rounded-lg cursor-pointer transition-colors ${active ? 'bg-blue-600/10 text-blue-500' : 'text-gray-400 hover:text-gray-200 hover:bg-[#1e293b]'}`}>
      <Icon className="w-4 h-4 mr-3" />
      <span className="text-sm font-medium">{label}</span>
    </div>
  );

  const TopNavItem = ({ icon: Icon, label, active, onClick }) => (
    <div 
      onClick={onClick}
      className={`flex items-center px-4 py-4 cursor-pointer border-b-2 transition-colors ${active ? 'border-blue-500 text-blue-500' : 'border-transparent text-gray-400 hover:text-gray-200'}`}
    >
      <Icon className="w-4 h-4 mr-2" />
      <span className="text-sm font-medium">{label}</span>
    </div>
  );

  const ProgressBar = ({ value, label, subtitle, colorClass, barColorClass }) => (
    <div className="panel p-4 flex flex-col justify-between h-32">
      <div className="text-xs text-gray-400 font-medium">{label}</div>
      <div>
        <div className={`text-2xl font-bold ${colorClass}`}>{value}%</div>
        <div className="flex items-center text-xs text-gray-400 mt-1">
          <div className={`w-2 h-2 rounded-full mr-1.5 ${barColorClass.replace('bg-', 'bg-')}`}></div>
          {subtitle}
        </div>
      </div>
      <div className="w-full bg-gray-800 rounded-full h-1.5 mt-3">
        <div className={`h-1.5 rounded-full ${barColorClass}`} style={{ width: `${value}%` }}></div>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-[#090e17]">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 border-r border-[#1f2937] bg-[#0b1120] flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-[#1f2937]">
          <Shield className="w-6 h-6 text-blue-500 mr-2" />
          <div className="font-bold text-sm leading-tight text-white">PRS Compliance<br/>Intelligence Platform</div>
        </div>
        
        <div className="flex-1 overflow-y-auto py-4 px-3 custom-scrollbar">
          <div className="text-xs font-semibold text-gray-500 mb-2 px-3 tracking-wider">ANALYSIS</div>
          <SidebarItem icon={Grid} label="Overview" active={true} />
          <SidebarItem icon={UploadCloud} label="Upload & Analyze" />
          <SidebarItem icon={Search} label="Requirement Explorer" />
          <SidebarItem icon={FileText} label="Standards Mapping" />
          <SidebarItem icon={PieChartIcon} label="Gap Analysis" />
          
          <div className="text-xs font-semibold text-gray-500 mb-2 mt-6 px-3 tracking-wider">MANAGE</div>
          <SidebarItem icon={FileText} label="Documents" />
          <SidebarItem icon={Folder} label="Reports" />
          <SidebarItem icon={FileText} label="Analysis" />
          <SidebarItem icon={Clock} label="History" />
          
          <div className="text-xs font-semibold text-gray-500 mb-2 mt-6 px-3 tracking-wider">SETTINGS</div>
          <SidebarItem icon={Settings} label="Integrations" />
          <SidebarItem icon={Users} label="Team" />
          <SidebarItem icon={Settings} label="Settings" />
        </div>
        
        <div className="p-4 border-t border-[#1f2937]">
          <div className="panel p-4">
            <div className="text-xs font-bold text-white mb-1">Need Help?</div>
            <a href="#" className="text-xs text-blue-500 flex items-center hover:underline">
              View Documentation <ChevronRight className="w-3 h-3 ml-1" />
            </a>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden relative">
        {/* Top Navbar */}
        <header className="h-16 flex-shrink-0 border-b border-[#1f2937] bg-[#090e17] flex items-center justify-between px-6 z-10">
          <div className="flex items-center h-full space-x-2">
            <TopNavItem icon={Home} label="Dashboard" active={activeTab === 'Dashboard'} onClick={() => setActiveTab('Dashboard')} />
            <TopNavItem icon={Grid} label="Standards" active={activeTab === 'Standards'} onClick={() => setActiveTab('Standards')} />
            <TopNavItem icon={FileText} label="Analysis" active={activeTab === 'Reports'} onClick={() => setActiveTab('Reports')} />
            <TopNavItem icon={Folder} label="Reports" active={activeTab === 'Projects'} onClick={() => setActiveTab('Projects')} />
            <TopNavItem icon={Settings} label="Settings" active={activeTab === 'Settings'} onClick={() => setActiveTab('Settings')} />
          </div>
          <div className="flex items-center space-x-4">
            <div className="relative cursor-pointer text-gray-400 hover:text-white transition-colors">
              <Bell className="w-5 h-5" />
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-blue-500 rounded-full border-2 border-[#090e17]"></div>
            </div>
            <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-xs font-bold cursor-pointer hover:ring-2 hover:ring-blue-500 transition-all">
              AD
            </div>
          </div>
        </header>

        {/* Scrollable Main Area */}
        <main className="flex-1 overflow-y-auto p-6 custom-scrollbar">
          <div className="max-w-6xl mx-auto space-y-6">
            
            {activeTab === 'Dashboard' && (
              <>
                {/* Hero Banner */}
            <div className="panel hero-banner p-8 flex items-center justify-between">
              <div className="relative z-10">
                <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Cybersecurity Requirement Analysis</h1>
                <p className="text-blue-200/70 text-base max-w-lg">
                  Analyze Product Requirement Specifications against ITSAR, IEC 62443, CRA and global cybersecurity standards.
                </p>
              </div>
              <div className="relative z-10 hidden md:block opacity-90">
                <Shield className="w-24 h-24 text-blue-500 drop-shadow-[0_0_15px_rgba(37,99,235,0.5)]" strokeWidth={1} />
              </div>
            </div>

            {/* Two Column Upload & Config */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              
              {/* Left Column: Upload */}
              <div className="panel p-6 flex flex-col h-[320px]">
                <h2 className="text-base font-semibold text-white mb-4">Upload PRS Document</h2>
                <div 
                  className={`flex-1 border-2 border-dashed ${file ? 'border-blue-500 bg-blue-500/5' : 'border-[#334155] bg-[#0f172a] hover:border-[#475569]'} rounded-xl flex flex-col items-center justify-center transition-all`}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleFileDrop}
                >
                  {file ? (
                    <div className="text-center">
                      <FileText className="w-12 h-12 text-blue-500 mx-auto mb-3" />
                      <p className="text-sm text-white font-medium mb-1">{file.name}</p>
                      <p className="text-xs text-gray-500">{(file.size / (1024*1024)).toFixed(2)} MB</p>
                      <button onClick={() => setFile(null)} className="mt-4 text-xs text-red-400 hover:text-red-300">Remove File</button>
                    </div>
                  ) : (
                    <>
                      <UploadCloud className="w-12 h-12 text-gray-500 mb-4" />
                      <p className="text-sm text-gray-300 mb-2">Drag & drop your PRS document here</p>
                      <p className="text-xs text-gray-500 mb-4">or</p>
                      <button 
                        onClick={() => fileInputRef.current?.click()}
                        className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2 px-6 rounded-lg transition-colors"
                      >
                        Select File
                      </button>
                      <input 
                        type="file" 
                        ref={fileInputRef} 
                        onChange={(e) => setFile(e.target.files[0])} 
                        className="hidden" 
                        accept=".pdf,.txt,.docx" 
                      />
                    </>
                  )}
                </div>
                <div className="flex justify-between items-center mt-3 text-xs text-gray-500">
                  <span>Supported formats: PDF, DOCX, TXT</span>
                  <span>Max file size: 100 MB</span>
                </div>
              </div>

              {/* Right Column: Config / Details */}
              <div className="panel p-6 flex flex-col h-[320px] overflow-y-auto custom-scrollbar">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-base font-semibold text-white">Document Details & Config</h2>
                  {file && <X className="w-4 h-4 text-gray-500 cursor-pointer" onClick={() => setFile(null)}/>}
                </div>

                <div className="space-y-4">
                  {/* Selectors */}
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1.5">Target Standard</label>
                    <select 
                      className="w-full bg-[#0f172a] border border-[#334155] rounded-lg p-2.5 text-sm text-white focus:border-blue-500 outline-none"
                      value={selectedStandard} onChange={e => setSelectedStandard(e.target.value)}
                    >
                      <option value="">-- Select Standard --</option>
                      {standards.map(s => <option key={s.id} value={s.id}>{s.name || s.id}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1.5">Target Framework</label>
                    <select 
                      className="w-full bg-[#0f172a] border border-[#334155] rounded-lg p-2.5 text-sm text-white focus:border-blue-500 outline-none disabled:opacity-50"
                      value={selectedFramework} onChange={e => setSelectedFramework(e.target.value)}
                      disabled={!selectedStandard}
                    >
                      <option value="">-- Select Framework --</option>
                      {frameworks.map(f => <option key={f.id} value={f.id}>{f.name || f.id}</option>)}
                    </select>
                  </div>

                  {selectedFramework === 'ITSAR-ROUTER' && (
                    <div className="pt-2 border-t border-[#1f2937]">
                      <label className="block text-xs font-medium text-blue-400 mb-2">ITSAR Configuration</label>
                      <div className="grid grid-cols-2 gap-2">
                        {['conventional', 'sdn'].map(type => (
                          <label key={type} className="flex items-center space-x-2 text-xs text-gray-300">
                            <input type="radio" name="routerType" value={type} checked={routerType === type} onChange={() => setRouterType(type)} className="text-blue-500 bg-[#0f172a] border-[#334155]" />
                            <span className="capitalize">{type}</span>
                          </label>
                        ))}
                      </div>
                      <div className="grid grid-cols-2 gap-2 mt-2">
                        {[{id: 'web_interface', l: 'Web UI'}, {id: 'api_support', l: 'API'}, {id: 'wifi', l: 'Wi-Fi'}].map(cap => (
                          <label key={cap.id} className="flex items-center space-x-2 text-xs text-gray-300">
                            <input type="checkbox" checked={capabilities.includes(cap.id)} onChange={() => handleCapabilityToggle(cap.id)} className="rounded text-blue-500 bg-[#0f172a] border-[#334155]" />
                            <span>{cap.l}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {file && (
                    <div className="pt-3 border-t border-[#1f2937] text-xs text-gray-400 space-y-2">
                      <div className="flex justify-between"><span>File Size</span> <span className="text-white">{(file.size / (1024*1024)).toFixed(2)} MB</span></div>
                      <div className="flex justify-between"><span>Upload Time</span> <span className="text-white">{new Date().toLocaleString()}</span></div>
                      <div className="flex justify-between"><span>Status</span> <span className="text-emerald-400">Ready for Analysis</span></div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Generate Button */}
            <button 
              onClick={handleStartAnalysis}
              disabled={loading || (!file && !report)}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-[#1e293b] disabled:text-gray-500 disabled:cursor-not-allowed text-white font-medium py-4 px-6 rounded-xl transition-all flex justify-center items-center group"
            >
              {loading ? (
                <><div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-3"></div> {statusText}</>
              ) : (!file && report) ? (
                <>
                  <Search className="w-5 h-5 mr-2 text-blue-200 group-hover:text-white transition-colors" />
                  View Previous Analysis
                  <ChevronRight className="w-5 h-5 ml-auto opacity-50 group-hover:opacity-100 transition-opacity" />
                </>
              ) : (
                <>
                  <Search className="w-5 h-5 mr-2 text-blue-200 group-hover:text-white transition-colors" />
                  Generate Compliance Assessment
                  <ChevronRight className="w-5 h-5 ml-auto opacity-50 group-hover:opacity-100 transition-opacity" />
                </>
              )}
            </button>

            {/* Analysis Summary Area */}
            <div className="mt-8">
              <h3 className="text-sm font-semibold text-white mb-4">Analysis Summary {report ? '' : '(Preview)'}</h3>
              
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                
                {/* Main Pie Chart Card */}
                <div className="panel p-5 flex flex-col items-center justify-center col-span-2 md:col-span-1 h-32 relative">
                  <div className="text-xs text-gray-400 font-medium absolute top-4 left-4">Overall Compliance</div>
                  
                  {report ? (
                    <div className="w-full h-full pt-6 relative">
                       <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={[
                              { name: 'Compliant', value: report.counts.compliant, color: '#3b82f6' }, // Blue
                              { name: 'Partial', value: report.counts.partial, color: '#6366f1' },     // Indigo
                              { name: 'Non-Compliant', value: report.counts.non_compliant, color: '#1e293b' },
                              { name: 'Evidence Not Found', value: report.counts.evidence_not_found, color: '#94a3b8' },
                            ].filter(d => d.value > 0)}
                            cx="50%" cy="50%" innerRadius={28} outerRadius={38}
                            dataKey="value" stroke="none"
                          >
                            {/* Colors are handled by cell mapping below */}
                            { [
                              { name: 'Compliant', value: report.counts.compliant, color: '#3b82f6' }, 
                              { name: 'Partial', value: report.counts.partial, color: '#6366f1' },     
                              { name: 'Non-Compliant', value: report.counts.non_compliant, color: '#1e293b' },
                              { name: 'Evidence Not Found', value: report.counts.evidence_not_found, color: '#94a3b8' },
                            ].filter(d => d.value > 0).map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                        </PieChart>
                      </ResponsiveContainer>
                      <div className="absolute inset-0 pt-6 flex items-center justify-center flex-col pointer-events-none">
                        <span className="text-lg font-bold text-white">
                          {Math.round(((report.counts.compliant + report.counts.partial) / Math.max(1, (report.counts.compliant + report.counts.partial + report.counts.non_compliant + report.counts.evidence_not_found))) * 100)}%
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center w-full h-full pt-6">
                      <div className="w-16 h-16 rounded-full border-4 border-[#1e293b] border-t-blue-500 flex items-center justify-center">
                        <span className="text-lg font-bold text-white">68%</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Stat Bars */}
                {report ? (
                  <>
                    <ProgressBar 
                      label={`${selectedFramework} Coverage`}
                      value={Math.round(((report.counts.compliant + report.counts.partial) / Math.max(1, (report.counts.compliant + report.counts.partial + report.counts.non_compliant + report.counts.evidence_not_found))) * 100)}
                      subtitle="Current Target"
                      colorClass="text-blue-400"
                      barColorClass="bg-blue-500"
                    />
                    <ProgressBar label="IEC 62443 Coverage" value={61} subtitle="Moderate (Estimated)" colorClass="text-purple-400" barColorClass="bg-purple-500" />
                    <ProgressBar label="CRA Readiness" value={56} subtitle="Medium (Estimated)" colorClass="text-amber-400" barColorClass="bg-amber-500" />
                    <ProgressBar label="OWASP Alignment" value={78} subtitle="Good (Estimated)" colorClass="text-emerald-400" barColorClass="bg-emerald-500" />
                  </>
                ) : (
                  <>
                    <ProgressBar label="ITSAR Coverage" value={72} subtitle="Good" colorClass="text-blue-400" barColorClass="bg-blue-500" />
                    <ProgressBar label="IEC 62443 Coverage" value={61} subtitle="Moderate" colorClass="text-purple-400" barColorClass="bg-purple-500" />
                    <ProgressBar label="CRA Readiness" value={56} subtitle="Medium" colorClass="text-amber-400" barColorClass="bg-amber-500" />
                    <ProgressBar label="OWASP Alignment" value={78} subtitle="Good" colorClass="text-emerald-400" barColorClass="bg-emerald-500" />
                  </>
                )}
              </div>

              {/* Section Breakdown for Dashboard */}
              {report && (
                <div className="mt-6 panel p-5">
                  <h4 className="text-sm font-semibold text-white mb-4">Section Breakdown</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {report.groups.map(g => {
                      const totalReqs = g.children.length;
                      const coveredReqs = g.children.filter(c => c.status === 'compliant' || c.status === 'partial').length;
                      const coveragePct = totalReqs > 0 ? Math.round((coveredReqs / totalReqs) * 100) : 0;
                      let colorClass = 'text-red-500 bg-red-500/10';
                      if (coveragePct === 100) colorClass = 'text-emerald-500 bg-emerald-500/10';
                      else if (coveragePct >= 50) colorClass = 'text-amber-500 bg-amber-500/10';

                      return (
                        <div key={g.id} className="bg-[#0f172a] rounded-lg p-3 border border-[#1f2937] flex items-center justify-between">
                          <div>
                            <div className="text-sm font-medium text-white line-clamp-1">Section {g.id} {g.title}</div>
                            <div className="text-xs text-gray-500">{g.children.length} Requirements</div>
                          </div>
                          <div className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase ${colorClass}`}>
                            {coveredReqs}/{totalReqs} Covered
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {!report && (
                <div className="mt-4 flex items-center text-xs text-gray-400 bg-[#1e293b]/50 p-3 rounded-lg border border-[#334155]/50">
                  <div className="w-4 h-4 rounded-full border border-blue-500/50 flex items-center justify-center text-blue-500 mr-2">i</div>
                  Select a document and framework, then click 'Generate Compliance Assessment' to view real detailed results.
                </div>
              )}
            </div>
            </>
            )}

            {activeTab === 'Standards' && (
              <div className="space-y-6 animate-fade-in">
                <div className="panel p-6">
                  <h2 className="text-xl font-bold text-white mb-2">Cybersecurity Standards</h2>
                  <p className="text-gray-400 mb-6">Explore the reference standards and guidelines used for the gap analysis.</p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {/* ITSAR Router Card */}
                    <div className="bg-[#0f172a] rounded-xl border border-[#1f2937] p-5 hover:border-blue-500/50 transition-colors">
                      <div className="w-10 h-10 rounded bg-blue-500/10 flex items-center justify-center mb-4">
                        <Shield className="text-blue-500 w-5 h-5" />
                      </div>
                      <h3 className="text-white font-semibold text-lg mb-2">ITSAR Router</h3>
                      <p className="text-sm text-gray-400 mb-4 line-clamp-3">
                        Indian Telecommunication Security Assurance Requirements for IP Routers. Defines mandatory security baseline and cryptographic controls.
                      </p>
                      <a href="/ITSAR_IP_Router.pdf" target="_blank" rel="noreferrer" className="text-blue-400 hover:text-blue-300 text-sm font-medium flex items-center">
                        View PDF <ExternalLink className="w-3 h-3 ml-1" />
                      </a>
                    </div>
                    
                    {/* ITSAR LAN Card */}
                    <div className="bg-[#0f172a] rounded-xl border border-[#1f2937] p-5 hover:border-blue-500/50 transition-colors">
                      <div className="w-10 h-10 rounded bg-green-500/10 flex items-center justify-center mb-4">
                        <Grid className="text-green-500 w-5 h-5" />
                      </div>
                      <h3 className="text-white font-semibold text-lg mb-2">ITSAR LAN Switch</h3>
                      <p className="text-sm text-gray-400 mb-4 line-clamp-3">
                        Security assurance requirements tailored specifically for enterprise and telecom LAN switching equipment.
                      </p>
                      <a href="/ITSAR_LAN_Switch.pdf" target="_blank" rel="noreferrer" className="text-blue-400 hover:text-blue-300 text-sm font-medium flex items-center">
                        View PDF <ExternalLink className="w-3 h-3 ml-1" />
                      </a>
                    </div>

                    {/* IEC 62443 Card */}
                    <div className="bg-[#0f172a] rounded-xl border border-[#1f2937] p-5 hover:border-blue-500/50 transition-colors">
                      <div className="w-10 h-10 rounded bg-purple-500/10 flex items-center justify-center mb-4">
                        <FileText className="text-purple-500 w-5 h-5" />
                      </div>
                      <h3 className="text-white font-semibold text-lg mb-2">IEC 62443</h3>
                      <p className="text-sm text-gray-400 mb-4 line-clamp-3">
                        International series of standards that address cybersecurity for operational technology in automation and control systems.
                      </p>
                      <a href="#" className="text-blue-400 hover:text-blue-300 text-sm font-medium flex items-center">
                        View Details <ExternalLink className="w-3 h-3 ml-1" />
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'Projects' && (
              <div className="panel p-6 animate-fade-in flex flex-col items-center justify-center h-64">
                <Folder className="w-12 h-12 text-gray-500 mb-4" />
                <h3 className="text-lg font-medium text-white mb-2">Saved Reports</h3>
                <p className="text-gray-400 text-center max-w-sm">
                  Historical and saved gap analysis reports will appear here for download and review.
                </p>
              </div>
            )}

            {activeTab === 'Reports' && (
              <div className="mt-2 panel overflow-hidden animate-fade-in">
                <div className="p-4 border-b border-[#1f2937] flex justify-between items-center bg-[#131B2F]">
                  <h3 className="text-sm font-semibold text-white flex items-center">Requirement Gap Analysis Report</h3>
                </div>
                
                {!report ? (
                  <div className="p-8 text-center text-gray-400">
                    <FileText className="w-12 h-12 mx-auto mb-3 opacity-20" />
                    No report generated yet. Go to the Dashboard to analyze a document.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-sm">
                      <thead>
                        <tr className="bg-[#0f172a] text-gray-400 text-xs uppercase tracking-wider">
                          <th className="p-4 font-medium w-1/4">Requirement ID</th>
                          <th className="p-4 font-medium w-1/4">Status</th>
                          <th className="p-4 font-medium w-1/2">Analysis Summary</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#1f2937]">
                        {report.groups.map((g) => (
                          <React.Fragment key={g.id}>
                            {/* Group Header Row */}
                            <tr className="bg-[#1e293b]/50">
                              <td colSpan={3} className="p-3 border-b border-[#334155]/50">
                                <div className="font-bold text-blue-400 mb-2">Section {g.id} {g.title} ({g.children.length} Requirements)</div>
                                <div className="flex flex-wrap gap-2 text-xs">
                                  {g.children.map(req => {
                                    const isCovered = req.status === 'compliant' || req.status === 'partial';
                                    return (
                                      <div key={req.id} title={req.title} className={`flex items-center space-x-1 px-2 py-0.5 rounded-sm ${isCovered ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
                                        {isCovered ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                                        <span>{req.id}</span>
                                      </div>
                                    )
                                  })}
                                </div>
                              </td>
                            </tr>
                            
                            {/* Children Rows */}
                            {g.children.map((req) => {
                              const parsed = parseJustification(req.text);
                              const isExpanded = !!expandedRows[req.id];
                              const sc = getStatusConfig(req.status);
                              
                              let rowSummary = '';
                              if (parsed.isJson) {
                                rowSummary = parsed.justification || parsed.recommendation || `Verdict: ${parsed.verdict}`;
                              } else {
                                rowSummary = parsed.gap || parsed.provides || parsed.rec || parsed.evidence || parsed.raw || 'No details provided.';
                              }
                              
                              if (rowSummary.length > 80) rowSummary = rowSummary.substring(0, 80) + '...';

                              return (
                                <React.Fragment key={req.id}>
                                  <tr 
                                    className="hover:bg-[#1f2937]/50 cursor-pointer transition-colors"
                                    onClick={() => setExpandedRows(prev => ({...prev, [req.id]: !prev[req.id]}))}
                                  >
                                    <td className="p-4 pl-8">
                                      <div className="font-medium text-gray-300">{req.id}</div>
                                      <div className="text-xs text-gray-500 mt-1 max-w-[250px] leading-tight">{req.title}</div>
                                    </td>
                                    <td className="p-4">
                                      <div className="flex items-center space-x-2">
                                        {sc.icon}
                                        <span className={`text-xs font-medium ${sc.color}`}>{sc.label}</span>
                                      </div>
                                      <div className="text-xs text-gray-500 mt-1">Conf: {req.conf || 'N/A'}</div>
                                    </td>
                                    <td className="p-4 text-xs text-gray-400">
                                      {rowSummary}
                                    </td>
                                  </tr>
                                  
                                  {isExpanded && (
                                    <tr>
                                      <td colSpan={3} className="p-4 bg-[#111827]">
                                        <div className="pl-8 py-2">
                                          <div className="bg-[#1e293b]/40 rounded-lg p-5 border border-[#334155]/30">
                                            <div className="space-y-4 max-w-4xl">
                                              {parsed.isJson ? (
                                                <>
                                                  {/* JSON Rendering */}
                                                  {parsed.justification && (
                                                    <div>
                                                      <h4 className="text-[10px] font-bold uppercase tracking-wider text-blue-400 mb-1.5">Analysis Summary</h4>
                                                      <div className="border-l-2 border-blue-500/30 pl-3 text-gray-300 text-xs leading-relaxed">{parsed.justification}</div>
                                                    </div>
                                                  )}
                                                  {parsed.matched_concepts.length > 0 && (
                                                    <div>
                                                      <h4 className="text-[10px] font-bold uppercase tracking-wider text-emerald-500 mb-1.5">Matched Concepts</h4>
                                                      <div className="flex flex-wrap gap-2">
                                                        {parsed.matched_concepts.map((c, i) => <span key={i} className="px-2 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs">{c}</span>)}
                                                      </div>
                                                    </div>
                                                  )}
                                                  {parsed.missing_concepts.length > 0 && (
                                                    <div>
                                                      <h4 className="text-[10px] font-bold uppercase tracking-wider text-red-500 mb-1.5">Missing Concepts (Gaps)</h4>
                                                      <div className="flex flex-wrap gap-2">
                                                        {parsed.missing_concepts.map((c, i) => <span key={i} className="px-2 py-1 rounded bg-red-500/10 text-red-400 border border-red-500/20 text-xs">{c}</span>)}
                                                      </div>
                                                    </div>
                                                  )}
                                                  {parsed.extracted_evidence.length > 0 && (
                                                    <div>
                                                      <h4 className="text-[10px] font-bold uppercase tracking-wider text-blue-400 mb-1.5">Supporting Evidence</h4>
                                                      <ul className="list-disc pl-5 text-gray-300 text-xs space-y-1">
                                                        {parsed.extracted_evidence.map((e, i) => <li key={i} className="italic text-gray-400">"{e}"</li>)}
                                                      </ul>
                                                    </div>
                                                  )}
                                                  {parsed.recommendation && (
                                                    <div>
                                                      <h4 className="text-[10px] font-bold uppercase tracking-wider text-amber-500 mb-1.5">Recommendation</h4>
                                                      <div className="border-l-2 border-amber-500/30 pl-3 text-amber-100/90 text-xs leading-relaxed">{parsed.recommendation}</div>
                                                    </div>
                                                  )}
                                                </>
                                              ) : (
                                                <>
                                                  {/* Fallback / Raw Rendering */}
                                                  {parsed.gap && (
                                                    <div>
                                                      <h4 className="text-[10px] font-bold uppercase tracking-wider text-red-400 mb-1.5">Gap Identified</h4>
                                                      <div className="border-l-2 border-red-500/30 pl-3 text-gray-300 text-xs leading-relaxed">{parsed.gap}</div>
                                                    </div>
                                                  )}
                                                  {parsed.provides && (
                                                    <div>
                                                      <h4 className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 mb-1.5">Product Provides</h4>
                                                      <div className="border-l-2 border-emerald-500/30 pl-3 text-gray-300 text-xs leading-relaxed">{parsed.provides}</div>
                                                    </div>
                                                  )}
                                                  {parsed.rec && (
                                                    <div>
                                                      <h4 className="text-[10px] font-bold uppercase tracking-wider text-amber-400 mb-1.5">Recommendation</h4>
                                                      <div className="border-l-2 border-amber-500/30 pl-3 text-gray-300 text-xs leading-relaxed">{parsed.rec}</div>
                                                    </div>
                                                  )}
                                                  {parsed.evidence && (
                                                    <div>
                                                      <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">Evidence Details</h4>
                                                      <div className="border-l-2 border-slate-500/30 pl-3 text-gray-400 text-[11px] leading-relaxed whitespace-pre-wrap">{parsed.evidence}</div>
                                                    </div>
                                                  )}
                                                  {!parsed.gap && !parsed.provides && !parsed.rec && !parsed.evidence && parsed.raw && (
                                                    <div>
                                                      <h4 className="text-[10px] font-bold uppercase tracking-wider text-blue-400 mb-1.5">Analysis Summary</h4>
                                                      <div className="border-l-2 border-blue-500/30 pl-3 text-gray-300 text-xs leading-relaxed whitespace-pre-wrap">{parsed.raw}</div>
                                                    </div>
                                                  )}
                                                </>
                                              )}
                                            </div>
                                          </div>
                                        </div>
                                      </td>
                                    </tr>
                                  )}
                                </React.Fragment>
                              );
                            })}
                          </React.Fragment>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
            
          </div>
        </main>
      </div>
    </div>
  );
}
