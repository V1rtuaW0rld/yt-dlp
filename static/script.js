const form = document.getElementById('download-form');
const output = document.getElementById('output');
const tableBody = document.getElementById('video-table-body');

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
        output.textContent += 'Commande(s) lancée(s) !\n';
    } else {
        output.textContent += 'Erreur lors du démarrage.\n';
    }
});

const eventSource = new EventSource('/stream');
eventSource.onmessage = (event) => {
    console.log("Message reçu:", event.data);  // Débogage
    if (event.data) {
        const data = event.data.replace('data: ', '').trim();
        if (data.startsWith('{') && data.endsWith('}')) {
            // Gestion des données initiales
            const initialData = JSON.parse(data);
            if (initialData.type === 'InitialData') {
                tableBody.innerHTML = ''; // Efface le contenu initial
                // Ajoute les tâches dans l'ordre reçu (déjà trié par date DESC)
                initialData.tasks.forEach(task => {
                    const row = document.createElement('tr');
                    row.setAttribute('data-task-id', task.task_id);
                    row.innerHTML = `
                        <td>${task.date}</td>
                        <td id="video-title-${task.task_id}">${task.title}</td>
                        <td id="video-thumbnail-${task.task_id}">${task.thumbnail ? `<img src="${task.thumbnail}" alt="Miniature" style="max-width: 100px; max-height: 100px;">` : 'N/A'}</td>
                        <td id="video-duration-${task.task_id}">${task.duration_string}</td>
                        <td id="video-filesize-${task.task_id}">${task.filesize_approx}</td>
                        <td id="video-resolution-${task.task_id}">${task.resolution}</td>
                        <td id="video-filename-${task.task_id}">${task.filename}</td>
                        <td><div id="progress-container-${task.task_id}"><progress id="progress-${task.task_id}" value="${task.progress}" max="100"></progress><span id="progress-text-${task.task_id}">${task.progress.toFixed(1)}%</span></div></td>
                    `;
                    tableBody.appendChild(row); // Ajoute à la fin pour respecter l'ordre décroissant
                });
            }
        } else {
            // Gestion des mises à jour (nouvelles tâches ou progression)
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
                            row.innerHTML = `
                                <td>${videoInfo.date}</td>
                                <td id="video-title-${taskId}">${videoInfo.title}</td>
                                <td id="video-thumbnail-${taskId}">${videoInfo.thumbnail ? `<img src="${videoInfo.thumbnail}" alt="Miniature" style="max-width: 100px; max-height: 100px;">` : 'N/A'}</td>
                                <td id="video-duration-${taskId}">${videoInfo.duration_string}</td>
                                <td id="video-filesize-${taskId}">${videoInfo.filesize_approx}</td>
                                <td id="video-resolution-${taskId}">${videoInfo.resolution}</td>
                                <td id="video-filename-${taskId}">${videoInfo.filename}</td>
                                <td><div id="progress-container-${taskId}"><progress id="progress-${taskId}" value="0" max="100"></progress><span id="progress-text-${taskId}">0%</span></div></td>
                            `;
                            tableBody.insertBefore(row, tableBody.firstChild); // Nouvelle tâche en tête
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
                    }
                } else {
                    output.textContent += `${data}\n`;
                    output.scrollTop = output.scrollHeight;
                }
            }
        }
    }
};
eventSource.onerror = () => {
    output.textContent += 'Erreur de connexion au stream.\n';
    eventSource.close();
};