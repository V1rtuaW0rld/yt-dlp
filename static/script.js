const form = document.getElementById('download-form');
const output = document.getElementById('output');
const tableBody = document.getElementById('video-table-body');
const paginationContainer = document.getElementById('pagination-container');

let eventSource = new EventSource('/stream?page=1');
let currentPage = 1;
let totalPages = 1;
let perPage = 5;

function loadPage(page) {
 if (page < 1 || page > totalPages) {
 console.warn(`Page ${page} hors limites (1 à ${totalPages})`);
 return;
 }
 currentPage = page;
 if (eventSource.readyState !== 2) eventSource.close(); // Ferme seulement si actif
 eventSource = new EventSource(`/stream?page=${page}`);
 eventSource.onmessage = handleMessage;
 eventSource.onerror = (e) => {
 console.error('Erreur stream:', e);
 output.textContent += 'Erreur de connexion au stream.\n';
 setTimeout(() => loadPage(currentPage), 1000); // Reconnexion auto
 };
 console.log(`Chargement de la page ${page}`);
}

function handleMessage(event) {
 console.log("Message brut reçu:", event.data);
 if (event.data) {
 const data = event.data.replace('data: ', '').trim();
 console.log("Données traitées:", data);
 if (data.startsWith('{') && data.endsWith('}')) {
 try {
 const initialData = JSON.parse(data);
 console.log("Données initiales:", initialData);
 if (initialData.type === 'InitialData') {
 tableBody.innerHTML = '';
 initialData.tasks.forEach(task => {
 const row = document.createElement('tr');
 row.setAttribute('data-task-id', task.task_id);
 // Détecte si status est un timestamp epoch
 const isEpoch = /^\d{9,}$/.test(task.status);
 row.innerHTML = `
 <td>${task.date || 'N/A'}</td>
 <td id="video-title-${task.task_id}">${task.title || 'N/A'}</td>
 <td id="video-thumbnail-${task.task_id}">${task.thumbnail ? `<img src="${task.thumbnail}" alt="Miniature" style="max-width: 100px; max-height: 100px;">` : 'N/A'}</td>
 <td id="video-duration-${task.task_id}">${task.duration_string || 'N/A'}</td>
 <td id="video-filesize-${task.task_id}">${task.filesize_approx || 'N/A'}</td>
 <td id="video-resolution-${task.task_id}">${task.resolution || 'N/A'}</td>
 <td id="video-filename-${task.task_id}">${task.filename || 'N/A'}</td>
 <td><div id="progress-container-${task.task_id}"><progress id="progress-${task.task_id}" value="${task.progress || 0}" max="100"></progress><span id="progress-text-${task.task_id}">${(task.progress || 0).toFixed(1)}%</span></div></td>
 <td>
 ${isEpoch ? `<img src="/static/images/default.gif" alt="En cours" style="max-width: 30px; max-height: 30px;">` : ''}
 ${task.status === '0' ? `<img src="/static/images/resume-button.png" alt="Reprendre" style="max-width: 30px; max-height: 30px; cursor: pointer;" class="resume-button" data-task-id="${task.task_id}">` : ''}
 ${task.status === '1' ? `<img src="/static/images/ok.png" alt="Terminé" style="max-width: 30px; max-height: 30px;">` : ''}
 </td>
 `;
 tableBody.appendChild(row);
 });
 // Ajouter les gestionnaires de clic pour resume-button
 document.querySelectorAll('.resume-button').forEach(button => {
 button.addEventListener('click', async () => {
 const taskId = button.getAttribute('data-task-id');
 const response = await fetch('/resume', {
 method: 'POST',
 headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
 body: `task_id=${encodeURIComponent(taskId)}`
 });
 if (response.ok) {
 output.textContent += await response.text() + '\n';
 loadPage(currentPage); // Rafraîchir la page actuelle
 } else {
 output.textContent += 'Erreur lors de la reprise.\n';
 }
 });
 });
 currentPage = initialData.pagination.current_page;
 totalPages = initialData.pagination.total_pages;
 perPage = initialData.pagination.per_page;
 renderPagination();
 }
 } catch (e) {
 console.error('Erreur parsing JSON:', e, data);
 output.textContent += 'Erreur lors du traitement des données.\n';
 }
 } else {
 const match = data.match(/\[([^\]]+)\]\s*(.+)/);
 if (match) {
 const taskId = match[1];
 const dataContent = match[2];
 if (dataContent.startsWith('VideoInfo:')) {
 try {
 const videoInfo = JSON.parse(dataContent.replace('VideoInfo:', '').trim());
 let row = document.querySelector(`tr[data-task-id="${taskId}"]`);
 if (!row) {
 row = document.createElement('tr');
 row.setAttribute('data-task-id', taskId);
 const isEpoch = /^\d{9,}$/.test(videoInfo.status);
 row.innerHTML = `
 <td>${videoInfo.date || 'N/A'}</td>
 <td id="video-title-${taskId}">${videoInfo.title || 'N/A'}</td>
 <td id="video-thumbnail-${taskId}">${videoInfo.thumbnail ? `<img src="${videoInfo.thumbnail}" alt="Miniature" style="max-width: 100px; max-height: 100px;">` : 'N/A'}</td>
 <td id="video-duration-${taskId}">${videoInfo.duration_string || 'N/A'}</td>
 <td id="video-filesize-${taskId}">${videoInfo.filesize_approx || 'N/A'}</td>
 <td id="video-resolution-${taskId}">${videoInfo.resolution || 'N/A'}</td>
 <td id="video-filename-${taskId}">${videoInfo.filename || 'N/A'}</td>
 <td><div id="progress-container-${taskId}"><progress id="progress-${taskId}" value="0" max="100"></progress><span id="progress-text-${taskId}">0%</span></div></td>
 <td>
 ${isEpoch ? `<img src="/static/images/default.gif" alt="En cours" style="max-width: 30px; max-height: 30px;">` : ''}
 ${videoInfo.status === '0' ? `<img src="/static/images/resume-button.png" alt="Reprendre" style="max-width: 30px; max-height: 30px; cursor: pointer;" class="resume-button" data-task-id="${taskId}">` : ''}
 ${videoInfo.status === '1' ? `<img src="/static/images/ok.png" alt="Terminé" style="max-width: 30px; max-height: 30px;">` : ''}
 </td>
 `;
 tableBody.insertBefore(row, tableBody.firstChild);
 }
 } catch (e) {
 console.error(`Erreur parsing VideoInfo: ${e}`);
 }
 } else if (dataContent.startsWith('Progress:')) {
 const percentage = parseFloat(dataContent.replace('Progress:', '').trim());
 const progress = document.getElementById(`progress-${taskId}`);
 const progressText = document.getElementById(`progress-text-${taskId}`);
 if (progress && progressText) {
 progress.value = percentage;
 progressText.textContent = `${percentage.toFixed(1)}%`;
 } else {
 console.warn(`Éléments progress non trouvés pour ${taskId}`);
 }
 } else {
 output.textContent += `${data}\n`;
 output.scrollTop = output.scrollHeight;
 }
 }
 }
 }
}

function renderPagination() {
 if (totalPages <= 1) {
 paginationContainer.innerHTML = '';
 return;
 }
 paginationContainer.innerHTML = `
 <nav aria-label="Pagination des tâches">
 <ul class="pagination">
 <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
 <a class="page-link" href="#" onclick="loadPage(1)">Première</a>
 </li>
 <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
 <a class="page-link" href="#" onclick="loadPage(${currentPage - 1})">Précédente</a>
 </li>
 <li class="page-item disabled"><span class="page-link">Page ${currentPage} sur ${totalPages}</span></li>
 <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
 <a class="page-link" href="#" onclick="loadPage(${currentPage + 1})">Suivante</a>
 </li>
 <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
 <a class="page-link" href="#" onclick="loadPage(${totalPages})">Dernière</a>
 </li>
 <li class="page-item">
 <input type="number" class="form-control form-control-sm d-inline-block w-auto mx-2" id="page-input" min="1" max="${totalPages}" value="${currentPage}" style="width: 80px;" onchange="loadPage(this.value)">
 </li>
 </ul>
 </nav>
 `;
}

form.addEventListener('submit', async (e) => {
 e.preventDefault();
 output.textContent = 'Démarrage...\n';
 const url = document.getElementById('url').value;
 const res = await fetch('/download', {
 method: 'POST',
 headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
 body: `url=${encodeURIComponent(url)}`
 });
 if (res.ok) {
 const text = await res.text();
 output.textContent += text + '\n';
 loadPage(1); // Recharge la page 1 après soumission
 } else {
 output.textContent += 'Erreur lors du démarrage.\n';
 }
});

// Initialisation
loadPage(1);