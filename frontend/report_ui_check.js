
        const API_URL = "http://localhost:8000/api/v1";

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

        document.getElementById('frameworkSelect').addEventListener('change', (e) => {
            const val = e.target.value;
            document.getElementById('startBtn').disabled = !val;
            const configDiv = document.getElementById('itsarRouterConfig');
            configDiv.style.display = val === 'ITSAR-ROUTER' ? 'block' : 'none';
        });

        function escapeHtml(value) {
            return String(value ?? '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function asArray(value) {
            return Array.isArray(value) ? value.filter(Boolean) : [];
        }

        function sanitizeDomId(value) {
            return String(value).replace(/[^a-zA-Z0-9_-]/g, '_');
        }

        function toggleDetailRow(rowId) {
            const row = document.getElementById(rowId);
            if (!row) return;
            row.style.display = row.style.display === 'none' ? '' : 'none';
        }

        function compareRequirementIds(a, b) {
            const aParts = String(a).split('.');
            const bParts = String(b).split('.');
            const maxLen = Math.max(aParts.length, bParts.length);
            for (let i = 0; i < maxLen; i++) {
                const left = aParts[i] ?? '';
                const right = bParts[i] ?? '';
                const leftNum = Number(left);
                const rightNum = Number(right);
                const leftIsNum = !Number.isNaN(leftNum) && left !== '';
                const rightIsNum = !Number.isNaN(rightNum) && right !== '';
                if (leftIsNum && rightIsNum && leftNum !== rightNum) return leftNum - rightNum;
                if (left !== right) return left.localeCompare(right, undefined, { numeric: true, sensitivity: 'base' });
            }
            return 0;
        }

        function getStatusMeta(status) {
            const statusMap = {
                compliant: { cls: 'status-passed', icon: 'Compliant', label: 'Compliant' },
                non_compliant: { cls: 'status-failed', icon: 'Non-Compliant', label: 'Non-Compliant' },
                partial: { cls: 'status-partial', icon: 'Partial', label: 'Partial' },
                manual_review: { cls: 'status-review', icon: 'Manual Review', label: 'Manual Review' },
                evidence_not_found: { cls: 'status-evidence', icon: 'Evidence Not Found', label: 'Evidence Not Found' },
            };
            return statusMap[status] || { cls: 'status-partial', icon: status, label: status };
        }

        function renderChips(items, type) {
            const values = asArray(items);
            if (!values.length) return '';
            const chips = values.map(item => `<span class="concept-chip ${type}">${escapeHtml(item)}</span>`).join('');
            return `<div class="concept-chip-wrap">${chips}</div>`;
        }

        function renderEvidenceList(evidence) {
            const values = asArray(evidence);
            if (!values.length) return '';
            const lines = values.slice(0, 4).map(item => `<li>${escapeHtml(item)}</li>`).join('');
            return `<div class="analysis-subtitle">Evidence Highlights</div><ul class="analysis-list">${lines}</ul>`;
        }

        function renderScores(scores) {
            if (!scores || typeof scores !== 'object') return '';
            const keys = [
                ['semantic', 'Semantic'],
                ['capability', 'Capability'],
                ['evidence_quality', 'Evidence Quality'],
                ['grounding', 'Grounding'],
                ['confidence', 'Confidence'],
                ['coverage_ratio', 'Coverage Ratio'],
                ['average_child_confidence', 'Avg Child Confidence'],
            ];
            const parts = keys
                .filter(([key]) => scores[key] !== undefined && scores[key] !== null)
                .map(([key, label]) => `${label}: ${escapeHtml(scores[key])}`);
            if (!parts.length) return '';
            return `<div class="gap-analysis-scores">${parts.join(' | ')}</div>`;
        }

        function buildAnalysisCard(item, isGroup = false) {
            const summary = item.summary || item.text || 'No AI justification available yet.';
            const recommendation = item.recommendation;
            const matched = asArray(item.matched_concepts);
            const missing = asArray(item.missing_concepts);
            const evidence = asArray(item.evidence);
            const scores = item.scores || {};

            let html = '<div class="gap-card">';
            html += `<div class="analysis-summary">${escapeHtml(summary)}</div>`;

            if (matched.length) {
                html += '<div class="analysis-subtitle">Covered Concepts</div>';
                html += renderChips(matched, 'match');
            }
            if (missing.length) {
                html += '<div class="analysis-subtitle" style="margin-top:0.65rem;">Gaps / Missing Coverage</div>';
                html += renderChips(missing, 'miss');
            }
            if (recommendation) {
                html += `<div class="analysis-subtitle" style="color:#fbbf24; margin-top:0.75rem;">Recommendation</div><div style="border-left:3px solid #fbbf24;padding-left:0.6rem;color:#fde68a;margin-bottom:0.6rem;">${escapeHtml(recommendation)}</div>`;
            }
            html += renderEvidenceList(evidence);
            html += renderScores(scores);
            if (isGroup && !matched.length && !missing.length && !recommendation && !evidence.length) {
                html += '<div class="gap-evidence">Section roll-up result generated from child requirements.</div>';
            }
            html += '</div>';
            return html;
        }

        function renderSummary(reportData) {
            const summaryEl = document.getElementById('reportSummary');
            const counts = { compliant: 0, non_compliant: 0, partial: 0, manual_review: 0, evidence_not_found: 0 };
            (reportData.results || []).forEach(r => {
                if (counts[r.status] !== undefined) counts[r.status]++;
            });
            summaryEl.innerHTML = `
                <span style="background:#16a34a22;color:#4ade80;padding:0.4rem 1rem;border-radius:8px;">Compliant: ${counts.compliant}</span>
                <span style="background:#dc262622;color:#f87171;padding:0.4rem 1rem;border-radius:8px;">Non-Compliant: ${counts.non_compliant}</span>
                <span style="background:#d9770622;color:#fb923c;padding:0.4rem 1rem;border-radius:8px;">Partial: ${counts.partial}</span>
                <span style="background:#7c3aed22;color:#a78bfa;padding:0.4rem 1rem;border-radius:8px;">Manual Review: ${counts.manual_review}</span>
                <span style="background:#2563eb22;color:#93c5fd;padding:0.4rem 1rem;border-radius:8px;">Evidence Not Found: ${counts.evidence_not_found}</span>
            `;
        }

        function renderRow(r, tbody) {
            const s = getStatusMeta(r.status);
            const conf = r.conf || 'N/A';
            const detailHtml = buildAnalysisCard(r);
            tbody.innerHTML += `
                <tr>
                    <td style="font-weight:600; font-size:0.9rem;"><span class="child-id">${escapeHtml(r.id)}</span></td>
                    <td><span class="status-badge ${s.cls}">${escapeHtml(s.label)}</span></td>
                    <td><div class="muted-inline">${escapeHtml(conf)}</div></td>
                    <td>${detailHtml}</td>
                </tr>
            `;
        }

        function renderReport(reportData) {
            const tbody = document.getElementById('reportTableBody');
            tbody.innerHTML = '';
            renderSummary(reportData);

            if (!reportData.results || reportData.results.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4">No requirements were evaluated. The framework JSON may be empty.</td></tr>';
                return;
            }

            const groupMap = {};
            const ungrouped = [];

            reportData.results.forEach(r => {
                if (r.id.startsWith('GROUP-')) {
                    const groupId = r.id.replace('GROUP-', '');
                    if (!groupMap[groupId]) groupMap[groupId] = { group: null, children: [] };
                    groupMap[groupId].group = r;
                } else {
                    const parts = r.id.split('.');
                    let groupId = null;
                    if (parts.length >= 2) groupId = parts.slice(0, 2).join('.');
                    if (groupId) {
                        if (!groupMap[groupId]) groupMap[groupId] = { group: null, children: [] };
                        groupMap[groupId].children.push(r);
                    } else {
                        ungrouped.push(r);
                    }
                }
            });

            const sortedGroups = Object.keys(groupMap).sort(compareRequirementIds);
            sortedGroups.forEach(groupId => {
                const gData = groupMap[groupId];
                const groupResult = gData.group || {
                    id: `GROUP-${groupId}`,
                    status: 'partial',
                    summary: `Section ${groupId} includes ${gData.children.length} requirements.`,
                    conf: 'N/A',
                };
                const s = getStatusMeta(groupResult.status);
                const detailRowId = `section-detail-${sanitizeDomId(groupId)}`;
                const summaryPreview = escapeHtml((groupResult.summary || groupResult.text || `Section ${groupId}`).slice(0, 140));
                tbody.innerHTML += `
                    <tr class="section-row" onclick="toggleDetailRow('${detailRowId}')">
                        <td style="font-weight:700; color:#c4b5fd; font-size:1rem;">Section ${escapeHtml(groupId)} (${gData.children.length} Requirements)</td>
                        <td><span class="status-badge ${s.cls}">${escapeHtml(s.label)}</span></td>
                        <td><div class="muted-inline">${escapeHtml(groupResult.conf || 'N/A')}</div></td>
                        <td style="font-size:0.82rem; color:#ccc; white-space:pre-wrap;">${summaryPreview}</td>
                    </tr>
                    <tr id="${detailRowId}" style="display:none; background: rgba(0,0,0,0.2);">
                        <td colspan="4" style="padding:1.5rem;">${buildAnalysisCard(groupResult, true)}</td>
                    </tr>
                `;

                gData.children.sort((left, right) => compareRequirementIds(left.id, right.id));
                gData.children.forEach(child => renderRow(child, tbody));
            });

            if (ungrouped.length > 0) {
                tbody.innerHTML += `
                    <tr style="background: rgba(79, 70, 229, 0.1); border-top: 2px solid var(--primary);">
                        <td colspan="4" style="font-weight:700; color:#fff; padding:0.75rem 1rem;">Ungrouped Requirements</td>
                    </tr>
                `;
                ungrouped.sort((left, right) => compareRequirementIds(left.id, right.id));
                ungrouped.forEach(item => renderRow(item, tbody));
            }
        }

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
            document.getElementById('reportSummary').innerHTML = '';
            const statusText = document.getElementById('statusText');
            statusText.innerText = "Uploading and Initializing Analysis...";

            try {
                const res = await fetch(`${API_URL}/assess`, {
                    method: 'POST',
                    body: formData
                });

                if (!res.ok) throw new Error("Failed to start assessment");
                const jobData = await res.json();
                const jobId = jobData.id;

                const pollInterval = setInterval(async () => {
                    const pollRes = await fetch(`${API_URL}/reports/${jobId}`);
                    if (!pollRes.ok) return;

                    const reportData = await pollRes.json();
                    const total = reportData.total || 0;
                    const processed = reportData.processed || 0;

                    statusText.innerText = total > 0
                        ? `Analyzing requirements... (${processed} / ${total})`
                        : 'Processing document...';

                    if (reportData.status === 'completed' || reportData.status === 'failed') {
                        clearInterval(pollInterval);

                        document.getElementById('loader').style.display = 'none';
                        document.getElementById('startBtn').style.display = 'inline-block';
                        document.getElementById('startBtn').innerText = 'Run Another Analysis';
                        document.getElementById('reportSection').style.display = 'block';

                        const tbody = document.getElementById('reportTableBody');
                        tbody.innerHTML = '';

                        if (reportData.status === 'failed') {
                            document.getElementById('reportSummary').innerHTML = '';
                            tbody.innerHTML = `<tr><td colspan="4" style="color:#f87171;padding:1rem;">Analysis pipeline failed: ${escapeHtml(reportData.document_id || 'Unknown error')}. Please check the document and retry.</td></tr>`;
                            return;
                        }

                        renderReport(reportData);
                    }
                }, 2500);
            } catch (err) {
                console.error(err);
                document.getElementById('loader').style.display = 'none';
                document.getElementById('startBtn').style.display = 'inline-block';
                statusText.innerText = "Error starting analysis: " + err.message;
            }
        }
    
