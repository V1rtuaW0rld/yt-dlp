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
    if (event.data) {
        const match = event.data.match(/\[([^\]]+)\]\s*(.+)/); // Extraire task_id et data
        if (match) {
            const taskId = match[1];
            const data = match[2];
            console.log(`TaskId: "${taskId}", Data: "${data}"`);
            let row = document.querySelector(`tr[data-task-id="${taskId}"]`);
            if (!row) {
                row = document.createElement('tr');
                row.setAttribute('data-task-id', taskId);
                row.innerHTML = `<td id="video-title-${taskId}">En attente du titre...</td><td><div id="progress-container-${taskId}"><progress id="progress-${taskId}" value="0" max="100"></progress><span id="progress-text-${taskId}">0%</span></div></td>`;
                tableBody.appendChild(row);
            }
            if (data.startsWith('Titre récupéré :')) {
                const title = data.replace('Titre récupéré :', '').trim();
                const titleElement = document.getElementById(`video-title-${taskId}`);
                if (titleElement) titleElement.textContent = title;
                else console.error(`Élément non trouvé pour title-${taskId}`);
            } else if (data.startsWith('Progress:')) {
                const percentage = parseFloat(data.replace('Progress:', '').trim());
                const progress = document.getElementById(`progress-${taskId}`);
                const progressText = document.getElementById(`progress-text-${taskId}`);
                if (progress && progressText) {
                    progress.value = percentage;
                    progressText.textContent = `${percentage.toFixed(1)}%`;
                } else console.error(`Progression non trouvée pour ${taskId}`);
            } else {
                output.textContent += `${event.data}\n`;
                output.scrollTop = output.scrollHeight;
            }
        } else {
            output.textContent += `${event.data}\n`;
            output.scrollTop = output.scrollHeight;
        }
    }
};
eventSource.onerror = () => {
    output.textContent += 'Erreur de connexion au stream.\n';
    eventSource.close();
};
