const API_BASE = "https://TU-BACKEND-AQUI.fly.dev"; // <--- CAMBIAR

let currentEvent = null;

// Cargar evento
function loadEvent() {
    const code = document.getElementById("eventCode").value.trim();
    if (!code) {
        alert("Ingresa un código de evento.");
        return;
    }

    currentEvent = code;
    refreshAll();
}

// refrescar todo cada 5 segundos
setInterval(() => {
    if (currentEvent) refreshAll();
}, 5000);

async function refreshAll() {
    loadTiempos();
    loadResultados();
    loadInscritos();
    loadMedallero();
}

// ===============================
// 1. Tiempos en vivo
// ===============================
async function loadTiempos() {
    const res = await fetch(`${API_BASE}/api/eventos/${currentEvent}/tiempos`);
    const data = await res.json();
    const tbody = document.getElementById("tblTiempos");
    tbody.innerHTML = "";

    data.forEach(row => {
        tbody.innerHTML += `
        <tr>
            <td>${row.evento_completo}</td>
            <td>${row.serie_numero}</td>
            <td>${row.carril}</td>
            <td>${row.nombre_completo}</td>
            <td>${row.club}</td>
            <td>${row.tiempo_neto}</td>
        </tr>`;
    });
}

// ===============================
// 2. Resultados finales
// ===============================
async function loadResultados() {
    const res = await fetch(`${API_BASE}/api/eventos/${currentEvent}/resultados`);
    const data = await res.json();
    const tbody = document.getElementById("tblResultados");
    tbody.innerHTML = "";

    data.forEach(row => {
        tbody.innerHTML += `
        <tr>
            <td>${row.posicion}</td>
            <td>${row.nombre_completo}</td>
            <td>${row.club}</td>
            <td>${row.tiempo_neto}</td>
        </tr>`;
    });
}

// ===============================
// 3. Inscritos
// ===============================
async function loadInscritos() {
    const res = await fetch(`${API_BASE}/api/eventos/${currentEvent}/inscritos`);
    const data = await res.json();
    const tbody = document.getElementById("tblInscritos");
    tbody.innerHTML = "";

    data.forEach(row => {
        tbody.innerHTML += `
        <tr>
            <td>${row.nombre}</td>
            <td>${row.apellido}</td>
            <td>${row.genero}</td>
            <td>${row.club}</td>
            <td>${row.prueba}</td>
            <td>${row.categoria}</td>
            <td>${row.edad}</td>
        </tr>`;
    });
}

// ===============================
// 4. Medallero
// ===============================
async function loadMedallero() {
    const res = await fetch(`${API_BASE}/api/eventos/${currentEvent}/medallero`);
    const data = await res.json();
    const tbody = document.getElementById("tblMedallero");
    tbody.innerHTML = "";

    data.forEach(row => {
        tbody.innerHTML += `
        <tr>
            <td>${row.club}</td>
            <td>${row.oros}</td>
            <td>${row.platas}</td>
            <td>${row.bronces}</td>
        </tr>`;
    });
}
