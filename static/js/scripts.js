function getSelectedIds() {
    const checkboxes = document.querySelectorAll('.identity-checkbox:checked');
    return Array.from(checkboxes).map(cb => cb.dataset.id);
}

// Ouvre la modale et initialise l’état
function openRenameModal() {
    const selectedIds = getSelectedIds();
    if (selectedIds.length !== 1) {
        alert('Sélectionnez exactement une identité à renommer.');
        return;
    }
    document.getElementById('prenom').value = '';
    document.getElementById('nom').value = '';
    document.getElementById('prenom-seul').checked = false;
    document.getElementById('nom').disabled = false;
    document.getElementById('rename-modal').classList.remove('hidden');
}

// Ferme la modale
function closeRenameModal() {
    document.getElementById('rename-modal').classList.add('hidden');
}

// Gère la checkbox “prenom seul”
document.getElementById('prenom-seul').addEventListener('change', function () {
    document.getElementById('nom').disabled = this.checked;
    if (this.checked) {
        document.getElementById('nom').value = '';
    }
});

// Gestion du submit formulaire
document.getElementById('rename-form').addEventListener('submit', async function (e) {
    e.preventDefault();

    const selectedIds = getSelectedIds();
    if (selectedIds.length !== 1) {
        alert('Sélectionnez exactement une identité à renommer.');
        closeRenameModal();
        return;
    }

    const prenom = document.getElementById('prenom').value.trim();
    const nom = document.getElementById('nom').value.trim();
    const prenomSeul = document.getElementById('prenom-seul').checked;

    if (!prenom) {
        alert('Le prénom est obligatoire.');
        return;
    }

    const newId = prenomSeul ? prenom : prenom + (nom ? '_' + nom : '');

    const response = await fetch('/rename', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_id: selectedIds[0], new_id: newId }),
    });

    const result = await response.json();

    if (result.success) {
        location.reload();
    } else {
        alert(result.message);
    }
    closeRenameModal();
});

async function deleteIdentities() {
    const selectedIds = getSelectedIds();
    if (selectedIds.length === 0) {
        alert('Sélectionnez au moins une identité à supprimer.');
        return;
    }
    if (confirm('Confirmer la suppression des identités sélectionnées ?')) {
        const response = await fetch('/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: selectedIds })
        });
        const result = await response.json();
        if (result.success) {
            location.reload();
        }
    }
}

async function mergeIdentities() {
    const selectedIds = getSelectedIds();
    if (selectedIds.length < 2) {
        alert('Sélectionnez au moins deux identités à fusionner.');
        return;
    }
    const newId = document.getElementById('merge-input').value.trim();
    if (!newId) {
        alert('Entrez un nom valide pour la fusion.');
        return;
    }
    const response = await fetch('/merge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: selectedIds, new_id: newId })
    });
    const result = await response.json();
    if (result.success) {
        location.reload();
    } else {
        alert(result.message);
    }
}

// 🔹 Affichage des identités avec date/heure de dernier passage
async function loadIdentities() {
    const container = document.getElementById('identity-container');
    container.innerHTML = '';

    const response = await fetch('/identities');
    const identities = await response.json();

    identities.forEach(identity => {
        const card = document.createElement('div');
        card.classList.add('identity-card');

        // Checkbox
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.classList.add('identity-checkbox');
        checkbox.dataset.id = identity.id;
        card.appendChild(checkbox);

        // Nom ou ID
        const name = document.createElement('h3');
        name.textContent = identity.name || `ID: ${identity.id}`;
        card.appendChild(name);

        // Image
        if (identity.image) {
            const img = document.createElement('img');
            img.src = `/images/${identity.image}`;
            img.alt = identity.name || `ID: ${identity.id}`;
            card.appendChild(img);
        }

        // Date et heure dernier passage
        if (identity.last_seen) {
            const lastSeen = document.createElement('p');
            const dateObj = new Date(identity.last_seen);
            lastSeen.textContent = `Vu le ${dateObj.toLocaleDateString()} à ${dateObj.toLocaleTimeString()}`;
            card.appendChild(lastSeen);
        }

        container.appendChild(card);
    });
}

// Charger les identités au démarrage
document.addEventListener('DOMContentLoaded', loadIdentities);
