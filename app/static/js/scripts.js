function toggleCharacters(accountId) {
    var element = document.getElementById('chars-' + accountId);
    element.style.display = element.style.display === 'none' ? 'block' : 'none';
}

function runCharacterAction(accountId, characterId, action) {
    fetch(`/run/${accountId}/${characterId}/${action}`)
        .then(response => response.json())
        .then(data => alert(data.message))
        .catch(error => console.error('Error:', error));
}

function stopCharacterAction(accountId, characterId) {
    fetch(`/stop/${accountId}/${characterId}`)
        .then(response => response.json())
        .then(data => alert(data.message))
        .catch(error => console.error('Error:', error));
}

let lastUpdate = [];

function updateRunningBots() {
    fetch('/get_running_bots')
        .then(response => response.json())
        .then(data => {
            // Check if the data is different from the last update
            if (JSON.stringify(data) !== JSON.stringify(lastUpdate)) {
                lastUpdate = data;
                let botsTable = document.getElementById('runningBotsTable').querySelector('tbody');
                botsTable.innerHTML = data.map(bot => `
                    <tr>
                        <td>${bot.character}</td>
                        <td>${bot.activity}</td>
                        <td>${bot.runTime}</td>
                        <td>${bot.status}</td>
                        <td><button onclick="fetchLog('${bot.name}')">Show Log</button></td>
                    </tr>
                `).join('');
            }
        })
        .catch(error => console.error('Error:', error));
}

let logRefreshInterval = null;

function showLogModal(logData) {
    var ansiUp = new AnsiUp();
    var html = ansiUp.ansi_to_html(logData);
    document.getElementById('logDetails').innerHTML = html;
    document.getElementById('logModal').style.display = 'block';
}

function closeLogModal() {
    document.getElementById('logModal').style.display = 'none';
    // Clear the interval when the modal is closed
    if (logRefreshInterval) {
        clearInterval(logRefreshInterval);
        logRefreshInterval = null;
    }
}

function fetchLog(name) {
    // Assuming '/get_log' is the endpoint to get the log content
    fetch(`/get_log/${name}`)
        .then(response => response.text())
        .then(data => {
            showLogModal(data);
            // Start refreshing the log every 5 seconds
            if (logRefreshInterval) {
                clearInterval(logRefreshInterval);
            }
            logRefreshInterval = setInterval(() => fetchLog(name), 1000);
        })
        .catch(error => console.error('Error:', error));
}

// Update the list every 5 seconds (or choose an appropriate interval)
let runningBotsRefreshInterval = setInterval(updateRunningBots, 5000);