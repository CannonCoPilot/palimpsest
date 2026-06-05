document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const gutenbergIdInput = document.getElementById('gutenberg-id');
    const fetchGutenbergBtn = document.getElementById('fetch-gutenberg-btn');
    const fileUploadInput = document.getElementById('file-upload');
    const documentListUl = document.getElementById('document-list');
    const selectedListUl = document.getElementById('selected-list');
    const clearSelectionBtn = document.getElementById('clear-selection-btn');
    const runAnalysisBtn = document.getElementById('run-analysis-btn');
    const analysisStatusDiv = document.getElementById('analysis-status');
    const visualizationAreaDiv = document.getElementById('visualization-area'); // Main area
    const statsOutputPre = document.getElementById('stats-output');
    const exportResultsBtn = document.getElementById('export-results-btn');
    const analysisCheckboxes = document.querySelectorAll('input[name="analysis-module"]');

    // Progress elements
    const analysisProgressPanel = document.getElementById('analysis-progress');
    const progressLogUl = document.getElementById('progress-log');

    // Visualization specific elements
    const textComparisonView = document.getElementById('text-comparison-view');
    const textPane1Pre = document.querySelector('#text-pane-1 pre');
    const textPane2Pre = document.querySelector('#text-pane-2 pre');
    const textPane1Title = document.querySelector('#text-pane-1 h5');
    const textPane2Title = document.querySelector('#text-pane-2 h5');
    const heatmapView = document.getElementById('heatmap-view');
    const structureGraphView = document.getElementById('structure-graph-view');
    const heatmapPlaceholder = document.getElementById('heatmap-placeholder');
    const structureGraphPlaceholder = document.getElementById('structure-graph-placeholder');


    // --- Application State ---
    let loadedDocuments = {}; // Store loaded docs: { id: { name: string, content: string } }
    let selectedDocumentIds = []; // Array of selected document IDs
    let lastAnalysisResults = null; // Store results for export
    const MAX_SELECTED_DOCS = 4;

    // --- Helper Functions ---
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    function logProgress(message, type = 'info') {
        const li = document.createElement('li');
        li.textContent = message;
        if (type === 'error') {
            li.classList.add('error');
        } else if (type === 'success') {
            li.classList.add('success');
        }
        progressLogUl.appendChild(li);
        // Scroll to the bottom of the log
        progressLogUl.scrollTop = progressLogUl.scrollHeight;
    }

    // --- UI Update Functions ---
    function updateDocumentList() {
        documentListUl.innerHTML = ''; // Clear existing list
        Object.entries(loadedDocuments).forEach(([id, doc]) => {
            const li = document.createElement('li');
            li.textContent = doc.name;
            const selectBtn = document.createElement('button');
            selectBtn.textContent = 'Select';
            selectBtn.classList.add('select-doc');
            selectBtn.dataset.docId = id;
            selectBtn.disabled = selectedDocumentIds.includes(id) || selectedDocumentIds.length >= MAX_SELECTED_DOCS;
            selectBtn.addEventListener('click', handleSelectDocument);
            li.appendChild(selectBtn);
            documentListUl.appendChild(li);
        });
        updateRunAnalysisButton();
    }

    function updateSelectedList() {
        selectedListUl.innerHTML = '';
        selectedDocumentIds.forEach(id => {
            if (loadedDocuments[id]) {
                const li = document.createElement('li');
                li.textContent = loadedDocuments[id].name;
                const removeBtn = document.createElement('button');
                removeBtn.textContent = 'Remove';
                removeBtn.classList.add('remove-doc');
                removeBtn.dataset.docId = id;
                removeBtn.addEventListener('click', handleRemoveDocument);
                li.appendChild(removeBtn);
                selectedListUl.appendChild(li);
            }
        });
        clearSelectionBtn.disabled = selectedDocumentIds.length === 0;
        // Re-enable selection buttons in the main list if below max
        document.querySelectorAll('.select-doc').forEach(btn => {
             btn.disabled = selectedDocumentIds.includes(btn.dataset.docId) || selectedDocumentIds.length >= MAX_SELECTED_DOCS;
        });
        updateRunAnalysisButton();
    }

     function updateRunAnalysisButton() {
        // Enable run button if 1 to MAX_SELECTED_DOCS documents are selected
        runAnalysisBtn.disabled = !(selectedDocumentIds.length > 0 && selectedDocumentIds.length <= MAX_SELECTED_DOCS);
    }

    function addDocument(id, name, content) {
        if (!loadedDocuments[id]) {
            loadedDocuments[id] = { name, content };
            updateDocumentList();
        } else {
            console.warn(`Document with ID/Name '${id}' already loaded. Content not updated.`);
        }
    }

    function setStatus(message, isError = false) {
        analysisStatusDiv.textContent = `Status: ${message}`;
        analysisStatusDiv.style.color = isError ? 'red' : '#666';
    }

    function displayResults(results) {
        lastAnalysisResults = results;
        
        // Reset visualization areas
        visualizationAreaDiv.innerHTML = '';
        textComparisonView.style.display = 'none';
        heatmapView.style.display = 'none';
        structureGraphView.style.display = 'none';

        if (!results || !results.analysisResults) {
            console.error('Invalid results format:', results);
            return;
        }

        // Display string matching results
        if (results.analysisResults.string_matching) {
            const stringResults = results.analysisResults.string_matching;
            
            // Show visualizations
            if (stringResults.visualizations?.length > 0) {
                stringResults.visualizations.forEach(visPath => {
                    if (visPath.includes('heatmap')) {
                        heatmapView.style.display = 'block';
                        const img = document.createElement('img');
                        img.src = visPath;
                        img.alt = 'Analysis Visualization';
                        img.className = 'analysis-visualization';
                        heatmapPlaceholder.innerHTML = '';
                        heatmapPlaceholder.appendChild(img);
                    }
                });
            }

            // Show scores and statistics
            if (stringResults.preliminary_scores) {
                statsOutputPre.textContent = JSON.stringify(stringResults.preliminary_scores, null, 2);
            }
        }

        // Display text comparison if appropriate
        if (selectedDocumentIds.length >= 1) {
            textComparisonView.style.display = 'block';
            
            // First document
            if (loadedDocuments[selectedDocumentIds[0]]) {
                textPane1Pre.textContent = loadedDocuments[selectedDocumentIds[0]].content;
                textPane1Title.textContent = loadedDocuments[selectedDocumentIds[0]].name;
            }
            
            // Second document (if available)
            if (selectedDocumentIds.length >= 2 && loadedDocuments[selectedDocumentIds[1]]) {
                textPane2Pre.textContent = loadedDocuments[selectedDocumentIds[1]].content;
                textPane2Title.textContent = loadedDocuments[selectedDocumentIds[1]].name;
            } else {
                textPane2Pre.textContent = '';
                textPane2Title.textContent = 'Document 2 (Not Selected)';
            }
        }

        // Enable export if we have results
        exportResultsBtn.disabled = false;
    }


    // --- Event Handlers ---
    function handleSelectDocument(event) {
        const docId = event.target.dataset.docId;
        if (selectedDocumentIds.length < MAX_SELECTED_DOCS && !selectedDocumentIds.includes(docId)) {
            selectedDocumentIds.push(docId);
            updateSelectedList();
        }
    }

    function handleRemoveDocument(event) {
        const docIdToRemove = event.target.dataset.docId;
        selectedDocumentIds = selectedDocumentIds.filter(id => id !== docIdToRemove);
        updateSelectedList();
    }

    function handleClearSelection() {
        selectedDocumentIds = [];
        updateSelectedList();
    }

    async function handleFetchGutenberg() {
        const bookId = gutenbergIdInput.value.trim();
        if (!bookId || isNaN(parseInt(bookId))) {
            alert('Please enter a valid numeric Project Gutenberg ID.');
            return;
        }

        setStatus(`Fetching Gutenberg ID: ${bookId}...`);
        fetchGutenbergBtn.disabled = true;

        try {
            console.log(`Fetching Gutenberg book ID: ${bookId}`);
            const response = await fetch(`/api/gutenberg?book_id=${bookId}`);
            
            if (!response.ok) {
                throw new Error(`Failed to fetch book: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            
            if (data.content) {
                addDocument(data.doc_id, data.name, data.content);
                setStatus(`Successfully fetched ${data.name}`);
                gutenbergIdInput.value = '';
            } else {
                throw new Error('No content received from server');
            }
        } catch (error) {
            console.error('Error fetching Gutenberg text:', error);
            setStatus(`Failed to fetch Gutenberg ID: ${bookId} - ${error.message}`, true);
        } finally {
            fetchGutenbergBtn.disabled = false;
        }
    }

    function handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;
        if (file.type !== 'text/plain') {
            alert('Please upload a plain text file (.txt).');
            fileUploadInput.value = '';
            return;
        }

        setStatus(`Reading file: ${file.name}...`);
        const reader = new FileReader();

        reader.onload = (e) => {
            const content = e.target.result;
            const docId = `file_${file.name.replace(/[^a-zA-Z0-9]/g, '_')}_${Date.now()}`;
            const docName = file.name;
            addDocument(docId, docName, content);
            setStatus(`Successfully loaded file: ${file.name}.`);
            fileUploadInput.value = '';
        };

        reader.onerror = (e) => {
            setStatus(`Error reading file: ${file.name}.`, true);
            console.error("File reading error:", e);
            fileUploadInput.value = '';
        };

        reader.readAsText(file);
    }

    async function handleRunAnalysis() {
        if (selectedDocumentIds.length === 0) {
            alert('Please select at least one document to analyze.');
            return;
        }
        if (selectedDocumentIds.length > MAX_SELECTED_DOCS) {
            alert(`Please select no more than ${MAX_SELECTED_DOCS} documents.`);
            return;
        }

        const selectedModules = Array.from(analysisCheckboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);

        if (selectedModules.length === 0) {
            alert('Please select at least one analysis module.');
            return;
        }

        try {
            // Clear UI and show progress
            setStatus('Analysis started...');
            runAnalysisBtn.disabled = true;
            exportResultsBtn.disabled = true;
            visualizationAreaDiv.innerHTML = '<p>Analysis running...</p>';
            statsOutputPre.textContent = 'Analysis running...';
            textComparisonView.style.display = 'none';
            heatmapView.style.display = 'none';
            structureGraphView.style.display = 'none';
            progressLogUl.innerHTML = '';
            analysisProgressPanel.style.display = 'block';

            // Log initial status
            logProgress(`Starting analysis for ${selectedDocumentIds.length} document(s)...`);
            logProgress(`Selected modules: ${selectedModules.join(', ')}`);

            // Send analysis request
            console.log('Sending analysis request:', { document_ids: selectedDocumentIds, modules: selectedModules });
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    document_ids: selectedDocumentIds,
                    modules: selectedModules
                })
            });

            if (!response.ok) {
                throw new Error(`Analysis request failed: ${response.status} ${response.statusText}`);
            }

            const results = await response.json();
            console.log('Analysis results:', results);
            lastAnalysisResults = results; // Store for export

            // Display results and visualizations
            if (results.analysisResults.string_matching) {
                const stringResults = results.analysisResults.string_matching;
                logProgress('String matching analysis complete');

                // Display visualizations if available
                if (stringResults.visualizations && stringResults.visualizations.length > 0) {
                    heatmapView.style.display = 'block';
                    const heatmapDiv = document.getElementById('heatmap-placeholder');
                    heatmapDiv.innerHTML = '';

                    stringResults.visualizations.forEach(visPath => {
                        const img = document.createElement('img');
                        img.src = visPath;
                        img.alt = 'Analysis Visualization';
                        img.className = 'analysis-visualization';
                        heatmapDiv.appendChild(img);
                    });
                }

                // Display scores
                if (stringResults.preliminary_scores) {
                    statsOutputPre.textContent = 'Analysis Results:\n' +
                        JSON.stringify(stringResults, null, 2);
                }
            }

            logProgress('Analysis complete!', 'success');
            setStatus('Analysis complete.');
            exportResultsBtn.disabled = false;

        } catch (error) {
            console.error("Analysis error:", error);
            logProgress(`Analysis failed: ${error.message || 'Unknown error'}`, 'error');
            setStatus('Analysis failed.', true);
            visualizationAreaDiv.innerHTML = '<p style="color: red;">Analysis failed. Check progress log for details.</p>';
        } finally {
            runAnalysisBtn.disabled = false;
        }
    }

     function handleExportResults() {
        if (!lastAnalysisResults) {
            alert("No analysis results available to export.");
            return;
        }
        setStatus('Exporting results...');
        try {
            const dataStr = JSON.stringify(lastAnalysisResults, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `palimpsest_analysis_${Date.now()}.json`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            setStatus('Results exported successfully.');
        } catch (error) {
             console.error("Export failed:", error);
             setStatus('Failed to export results.', true);
        }
    }


    // --- Event Listeners ---
    fetchGutenbergBtn.addEventListener('click', handleFetchGutenberg);
    fileUploadInput.addEventListener('change', handleFileUpload);
    clearSelectionBtn.addEventListener('click', handleClearSelection);
    runAnalysisBtn.addEventListener('click', handleRunAnalysis);
    exportResultsBtn.addEventListener('click', handleExportResults);
    document.getElementById('exit-palimpsest-btn').addEventListener('click', async () => {
        console.log('Exit button clicked');  // Debug log
        if (confirm('Are you sure you want to exit Palimpsest?')) {
            try {
                console.log('User confirmed exit, sending request to server...');
                const response = await fetch('/api/exit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({}) // Add empty body to ensure proper POST
                });
                
                console.log('Server response status:', response.status);  // Debug log
                const data = await response.json();
                console.log('Server response:', data);  // Debug log

                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}: ${response.statusText}`);
                }

                console.log('Server shutdown initiated successfully');
                
                // Show immediate visual feedback
                document.body.innerHTML = '<div style="text-align: center; padding: 20px;">' +
                    '<h2>Shutting Down Palimpsest...</h2>' +
                    '<p>Server is stopping. This tab will attempt to close in 2 seconds.</p></div>';

                // Give the server a moment to shut down, then try to close the tab
                setTimeout(() => {
                    console.log('Attempting to close browser tab...');
                    if (!window.close()) {  // If window.close() returns false or fails
                        console.log('Could not automatically close tab');
                        document.body.innerHTML = '<div style="text-align: center; padding: 20px;">' +
                            '<h2>Palimpsest Server Stopped</h2>' +
                            '<p>The server has been shut down. You can now close this tab.</p>' +
                            '<p style="color: #666; margin-top: 20px;">Note: This tab could not be closed automatically ' +
                            'due to browser security settings.</p></div>';
                    }
                }, 2000);

            } catch (e) {
                console.error('Error during shutdown:', e);
                alert('Error shutting down Palimpsest server: ' + e.message + '\nCheck the console for details.');
            }
        }
    });


    // --- Initial Setup ---
    setStatus('Ready.');
    updateDocumentList();
    updateSelectedList();
    analysisProgressPanel.style.display = 'none'; // Hide progress initially

});