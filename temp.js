
        const API_URL = "http://localhost:8000/api/v1";

        // Fetch Standards on load
        window.onload = async () => {
            try {
                const res = await fetch(`${API_URL}/standards`);
                const standards = await res.json();
                const sel = document.getElementById('standardSelect');
                sel.innerHTML = '<option value="">-- Select Standard --</option>';
                standards.forEach(s => {
                    sel.innerHTML += `<option value="${s.id}">${s.name || s.id}</option>`;
                });
            } catch (e) {
                document.getElementById('standardSelect').innerHTML = '<option value="">Error loading standards (Backend running?)</option>';
            }
        };

        // Fetch Frameworks when standard changes
        async function fetchFrameworks() {
            const stdId = document.getElementById('standardSelect').value;
            const fSel = document.getElementById('frameworkSelect');
            const btn = document.getElementById('startBtn');
            
            if (!stdId) {
                fSel.innerHTML = '<option value="">Waiting for standard...</option>';
                fSel.disabled = true;
                btn.disabled = true;
                return;
            }

            fSel.disabled = false;
            fSel.innerHTML = '<option value="">Loading frameworks...</option>';
            
            try {
                const res = await fetch(`${API_URL}/standards/${stdId}/frameworks`);
                const frameworks = await res.json();
                fSel.innerHTML = '<option value="">-- Select Framework --</option>';
                frameworks.forEach(f => {
                    fSel.innerHTML += `<option value="${f.id}">${f.name || f.id}</option>`;
                });
            } catch (e) {
                fSel.innerHTML = '<option value="">Error loading</option>';
            }
        }

        // Enable button when framework selected
        document.getElementById('frameworkSelect').addEventListener('change', (e) => {
            const val = e.target.value;
            document.getElementById('startBtn').disabled = !val;
            
            // Show config if ITSAR-ROUTER
            const configDiv = document.getElementById('itsarRouterConfig');
            if (val === 'ITSAR-ROUTER') {
                configDiv.style.display = 'block';
            } else {
                configDiv.style.display = 'none';
            }
        });

        async function startAnalysis() {
            const stdId = document.getElementById('standardSelect').value;
            const frmId = document.getElementById('frameworkSelect').value;
            const fileInput = document.getElementById('docUpload');
            
            if (!fileInput.files.length) {
                alert("Please upload a document first.");
                return;
            }

            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append("file", file);
            formData.append("standard_id", stdId);
            formData.append("framework_id", frmId);
            
            if (frmId === 'ITSAR-ROUTER') {
                const routerType = document.querySelector('input[name="router_type"]:checked').value;
                const capabilities = Array.from(document.querySelectorAll('input[name="capabilities"]:checked')).map(cb => cb.value).join(',');
                formData.append("router_type", routerType);
                formData.append("capability_flags", capabilities);
            }

            document.getElementById('startBtn').style.display = 'none';
            document.getElementById('loader').style.display = 'block';
            document.getElementById('reportSection').style.display = 'none';
            const statusText = document.getElementById('statusText');
            statusText.innerText = "Uploading and Initializing Analysis...";

            try {
                // 1. Initiate Assessment
                const res = await fetch(`${API_URL}/assess`, {
                    method: 'POST',
                    body: formData
                });
                
                if (!res.ok) throw new Error("Failed to start assessment");
                const jobData = await res.json();
                const jobId = jobData.id;

                // 2. Poll for Status
                const pollInterval = setInterval(async () => {
                    const pollRes = await fetch(`${API_URL}/reports/${jobId}`);
                    if (!pollRes.ok) return;
                    
                    const reportData = await pollRes.json();
                    const total = reportData.total || 0;
                    const processed = reportData.processed || 0;
                    
                    if (total > 0) {
                        statusText.innerText = `Analyzing requirements... (${processed} / ${total})`;
                    } else {
                        statusText.innerText = `Processing document...`;
                    }

                    if (reportData.status === 'completed' || reportData.status === 'failed') {
                        clearInterval(pollInterval);

                        document.getElementById('loader').style.display = 'none';
                        document.getElementById('startBtn').style.display = 'inline-block';
                        document.getElementById('startBtn').innerText = "Run Another Analysis";
                        document.getElementById('reportSection').style.display = 'block';

                        const tbody = document.getElementById('reportTableBody');
                        tbody.innerHTML = '';

                        if (reportData.status === 'failed') {
                            tbody.innerHTML = `<tr><td colspan="4" style="color:#f87171;padding:1rem;">⛔ Analysis pipeline failed: ${reportData.document_id || 'Unknown error'}. Please check the document and retry.</td></tr>`;
                            return;
                        }

                        if (!reportData.results || reportData.results.length === 0) {
                            tbody.innerHTML = '<tr><td colspan="4">No requirements were evaluated. The framework JSON may be empty.</td></tr>';
                            return;
                        }

                        // Summary counts
                        let counts = {compliant:0, non_compliant:0, partial:0, manual_review:0};
                        reportData.results.forEach(r => { if (counts[r.status] !== undefined) counts[r.status]++; });
                        document.getElementById('reportSection').insertAdjacentHTML('afterbegin',
                            `<div style="display: flex; gap: 1rem; margin-bottom: 1.2rem; flex-wrap: wrap;">
                                <span style="background:#16a34a22;color:#4ade80;padding:0.4rem 1rem;border-radius:8px;">✅ Compliant: ${counts.compliant}</span>
                                <span style="background:#dc262622;color:#f87171;padding:0.4rem 1rem;border-radius:8px;">❌ Non-Compliant: ${counts.non_compliant}</span>
                                <span style="background:#d9770622;color:#fb923c;padding:0.4rem 1rem;border-radius:8px;">⚠️ Partial: ${counts.partial}</span>
                                <span style="background:#7c3aed22;color:#a78bfa;padding:0.4rem 1rem;border-radius:8px;">🔍 Manual Review: ${counts.manual_review}</span>
                            </div>`);

                        // Process grouped hierarchy
                        const groupMap = {};
                        const ungrouped = [];
                        
                        reportData.results.forEach(r => {
                            if (r.id.startsWith('GROUP-')) {
                                const groupId = r.id.replace('GROUP-', '');
                                if (!groupMap[groupId]) groupMap[groupId] = { group: null, children: [] };
                                groupMap[groupId].group = r;
                            } else {
                                // Child requirement. Find its group ID
                                const parts = r.id.split('.');
                                let groupId = null;
                                if (parts.length >= 3) {
                                    groupId = parts.slice(0, 3).join('.');
                                }
                                
                                if (groupId && groupMap[groupId]) {
                                    groupMap[groupId].children.push(r);
                                } else if (groupId) {
                                    if (!groupMap[groupId]) groupMap[groupId] = { group: null, children: [] };
                                    groupMap[groupId].children.push(r);
                                } else {
                                    ungrouped.push(r);
                                }
                            }
                        });

                        // Sort groups
                        const sortedGroups = Object.keys(groupMap).sort((a, b) => {
                            const aParts = a.split('.').map(Number);
                            const bParts = b.split('.').map(Number);
                            for (let i = 0; i < Math.max(aParts.length, bParts.length); i++) {
                                const av = aParts[i] || 0;
                                const bv = bParts[i] || 0;
                                if (av !== bv) return av - bv;
                            }
                            return 0;
                        });

                        sortedGroups.forEach(groupId => {
                            const gData = groupMap[groupId];
                            
                            // Group Header Row
                            if (gData.group) {
                                const g = gData.group;
                                const statusMap = {
                                    'compliant':     {cls:'status-passed',  icon:'✅', label:'Compliant'},
                                    'non_compliant': {cls:'status-failed',  icon:'❌', label:'Non-Compliant'},
                                    'partial':       {cls:'status-partial', icon:'⚠️', label:'Partial'},
                                    'manual_review': {cls:'status-review',  icon:'🔍', label:'Manual Review'}
                                };
                                const s = statusMap[g.status] || {cls:'status-partial', icon:'❓', label: g.status};
                                
                                const covPct = (g.confidence.score * 100).toFixed(0) + '%';
                                
                                tbody.innerHTML += `
                                    <tr style="background: rgba(79, 70, 229, 0.1); border-top: 2px solid var(--primary); border-bottom: 2px solid var(--primary);">
                                        <td style="font-weight: 700; color: #fff;">${groupId} (Group)</td>
                                        <td>
                                            <span class="status-badge ${s.cls}">${s.icon} ${s.label}</span>
                                            <div style="font-size:0.75rem; margin-top:4px; color:var(--text-muted);">Coverage: ${covPct}</div>
                                        </td>
                                        <td colspan="2" style="font-size: 0.85rem; color: #ddd;">
                                            <div style="white-space:pre-wrap;">${g.reasoning.replace(/\[EVIDENCE\].*/, '').trim()}</div>
                                        </td>
                                    </tr>
                                `;
                            } else {
                                tbody.innerHTML += `
                                    <tr style="background: rgba(79, 70, 229, 0.1); border-top: 2px solid var(--primary);">
                                        <td colspan="4" style="font-weight: 700; color: #fff; padding: 0.75rem 1rem;">Group ${groupId}</td>
                                    </tr>
                                `;
                            }

                            // Render children
                            gData.children.forEach(r => {
                                renderRow(r, tbody);
                            });
                        });
                        
                        if (ungrouped.length > 0) {
                            tbody.innerHTML += `
                                <tr style="background: rgba(79, 70, 229, 0.1); border-top: 2px solid var(--primary);">
                                    <td colspan="4" style="font-weight: 700; color: #fff; padding: 0.75rem 1rem;">Ungrouped</td>
                                </tr>
                            `;
                            ungrouped.forEach(r => renderRow(r, tbody));
                        }
                    }
                }, 2500);
            } catch (err) {
                console.error(err);
                document.getElementById('loader').style.display = 'none';
                document.getElementById('startBtn').style.display = 'inline-block';
                statusText.innerText = "Error starting analysis: " + err.message;
            }
        }
        
        function renderRow(r, tbody) {
            const statusMap = {
                'compliant':     {cls:'status-passed',  icon:'✅', label:'Compliant'},
                'non_compliant': {cls:'status-failed',  icon:'❌', label:'Non-Compliant'},
                'partial':       {cls:'status-partial', icon:'⚠️', label:'Partial'},
                'manual_review': {cls:'status-review',  icon:'🔍', label:'Manual Review'}
            };
            const s = statusMap[r.status] || {cls:'status-partial', icon:'❓', label: r.status};

            const rawJust = r.text || '';
            const providesMatch = rawJust.match(/PRODUCT PROVIDES:\s*([\s\S]*?)(?=GAP IDENTIFIED:|\[ANALYSIS\]|\[EVIDENCE\]|$)/);
            const gapMatch = rawJust.match(/GAP IDENTIFIED:\s*([\s\S]*?)(?=\[ANALYSIS\]|\[EVIDENCE\]|$)/);
            const analysisMatch = rawJust.match(/\[ANALYSIS\]([^\[]*?)(?=\[EVIDENCE\]|$)/);
            const evidenceMatch = rawJust.match(/\[EVIDENCE\]([\s\S]*)$/);

            const provides = providesMatch ? providesMatch[1].trim() : '';
            const gap = gapMatch ? gapMatch[1].trim() : '';
            const analysis = analysisMatch ? analysisMatch[1].trim() : '';
            const evidence = evidenceMatch ? evidenceMatch[1].trim() : '';

            const gapClass = (gap === 'None identified.' || gap.toLowerCase().includes('none identified')) ? 'gap-none' : 'gap-missing';

            let detailHtml = `<div class="gap-card">`;
            if (provides) detailHtml += `<div class="gap-section-label">Product Provides</div><div class="gap-provides">${provides}</div>`;
            if (gap) detailHtml += `<div class="gap-section-label">Gap Identified</div><div class="${gapClass}">${gap}</div>`;
            if (!provides && !gap) detailHtml += `<div style="color:var(--text-muted);white-space:pre-wrap;">${rawJust.replace(/\[ANALYSIS\][\s\S]*$/, '').trim()}</div>`;
            if (analysis) detailHtml += `<div class="gap-analysis-scores">${analysis}</div>`;
            if (evidence) {
                const evShort = evidence.length > 300 ? evidence.substring(0, 300) + '...' : evidence;
                detailHtml += `<div class="gap-evidence">📄 ${evShort}</div>`;
            }
            detailHtml += `</div>`;

            tbody.innerHTML += `
                <tr>
                    <td style="font-weight:600; font-size:0.9rem;">
                        <span style="display:inline-block; margin-left: 1rem;">↳ ${r.id}</span>
                    </td>
                    <td>
                        <span class="status-badge ${s.cls}">
                            ${s.icon} ${s.label}
                        </span>
                        <div style="font-size:0.75rem; margin-top:4px; color:var(--text-muted); margin-left: 1rem;">
                            Conf: ${(r.confidence.score * 100).toFixed(1)}%
                        </div>
                    </td>
                    <td colspan="2">${detailHtml}</td>
                </tr>
            `;
        }
    